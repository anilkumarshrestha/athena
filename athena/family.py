"""Families: who may see which children. No sign-up needed.

Each browser gets a family on its first API call: a random id in a signed, HttpOnly cookie.
Every learner belongs to one family, and the store only returns the current request's family's
learners (athena/store.py), so stories, readings, maths, teach rounds, the parent view and
delete all answer 404 for another family's child, without a check in every endpoint.

  family code   the id itself, shown to the grown-up (parent view) to open the same family on
                another device. It is a secret like a password: 64 random bits.
  Google        optional: "Sign in with Google to keep progress" links a Google account to
                the family (athena/api.py /api/auth/google); signing in elsewhere brings it back.
  legacy        learners stored before families existed belong to one family whose code is
                kept in state/legacy_family (printed at startup), so nothing is lost.

The current family lives in a context variable set by the middleware for each request.
Background work (prefetch, pictures) runs without it and sees everything: it only ever acts
on a learner it was handed.
"""

import contextvars
import hashlib
import hmac
import logging
import os
import re
import secrets
from pathlib import Path

log = logging.getLogger("athena")

COOKIE = "athena_family"
MAX_AGE = 365 * 24 * 3600
DEMO = "__demo__"  # template learners (Sita, Ram): copied into each new family, never listed
_ID = re.compile(r"^[0-9a-f]{16}$")

current: contextvars.ContextVar[str | None] = contextvars.ContextVar("family", default=None)


def _secret() -> bytes:
    """FAMILY_SECRET in production (Secret Manager); a local file in development."""
    if env := os.environ.get("FAMILY_SECRET"):
        return env.encode()
    from athena.config import settings

    path = Path(settings().state_dir) / "family_secret"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return path.read_text().strip().encode()


def new_id() -> str:
    return secrets.token_hex(8)


def sign(fid: str) -> str:
    mac = hmac.new(_secret(), fid.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{fid}.{mac}"


def verify(cookie: str | None) -> str | None:
    if not cookie or "." not in cookie:
        return None
    fid, mac = cookie.split(".", 1)
    if not _ID.match(fid):
        return None
    return fid if hmac.compare_digest(sign(fid), f"{fid}.{mac}") else None


def valid_code(code: str) -> str | None:
    """A family code as typed by a grown-up: "a1b2-c3d4-e5f6-a7b8" or without dashes."""
    fid = re.sub(r"[\s-]", "", code.lower())
    return fid if _ID.match(fid) else None


def pretty(fid: str) -> str:
    return "-".join(fid[i:i + 4] for i in range(0, 16, 4))


def legacy_family() -> str:
    from athena.config import settings

    path = Path(settings().state_dir) / "legacy_family"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_id())
    return path.read_text().strip()


class FamilyMiddleware:
    """Pure ASGI (covers WebSockets too): read or create the family cookie for /api calls."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket") or not scope["path"].startswith("/api/"):
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        cookie = _cookie(headers.get("cookie", ""), COOKIE)
        fid = verify(cookie)
        fresh = fid is None
        if fresh:
            fid = new_id()
        token = current.set(fid)
        secure = headers.get("x-forwarded-proto", scope.get("scheme", "http")) in ("https", "wss")

        async def send_with_cookie(message):
            if fresh and message["type"] == "http.response.start":
                hdrs = list(message.get("headers", []))
                hdrs.append((b"set-cookie", cookie_header(fid, secure).encode()))
                message = {**message, "headers": hdrs}
            await send(message)

        try:
            await self.app(scope, receive, send_with_cookie if scope["type"] == "http" else send)
        finally:
            current.reset(token)


def cookie_header(fid: str, secure: bool) -> str:
    return f"{COOKIE}={sign(fid)}; Path=/; Max-Age={MAX_AGE}; HttpOnly; SameSite=Lax" + ("; Secure" if secure else "")


def _cookie(header: str, name: str) -> str | None:
    for part in header.split(";"):
        k, _, v = part.strip().partition("=")
        if k == name:
            return v
    return None
