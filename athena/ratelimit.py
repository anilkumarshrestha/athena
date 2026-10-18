"""Tiny sliding-window rate limiter. The public URL calls paid models; cap it."""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException
from starlette.requests import HTTPConnection


class RateLimit:
    def __init__(self, per_ip: int, global_: int, window_s: float = 60.0) -> None:
        self.per_ip, self.global_, self.window = per_ip, global_, window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._all: deque[float] = deque()
        self._lock = threading.Lock()

    @staticmethod
    def client_ip(request: HTTPConnection) -> str:
        # Cloud Run sets X-Forwarded-For; first hop is the client.
        fwd = request.headers.get("x-forwarded-for", "")
        return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")

    def __call__(self, request: HTTPConnection) -> None:  # HTTP requests and WebSockets
        now = time.monotonic()
        ip = self.client_ip(request)
        with self._lock:
            for q in (self._hits[ip], self._all):
                while q and now - q[0] > self.window:
                    q.popleft()
            if len(self._hits[ip]) >= self.per_ip or len(self._all) >= self.global_:
                raise HTTPException(429, "Too many stories at once. Please wait a minute.")
            self._hits[ip].append(now)
            self._all.append(now)
