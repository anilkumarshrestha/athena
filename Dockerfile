# Athena: one container. Stage 1 builds the React app; stage 2 runs FastAPI, which serves
# the API, the WebSocket and the built frontend. ffmpeg: long recordings, picture resizing.

FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml constraints.txt ./
COPY athena ./athena
# Pinned to the versions the tests passed with; retries for slow networks.
RUN pip install --no-cache-dir --retries 10 --timeout 120 -c constraints.txt .
COPY data ./data
# Pre-drawn word pictures (illustrations only, no child data): a fresh deploy starts warm.
COPY media/pictures ./media/pictures
COPY --from=web /web/dist ./frontend/dist

ENV PORT=8080 PYTHONUNBUFFERED=1
# Not root: the app only writes to state/ and media/ under /app.
RUN useradd --create-home athena && mkdir -p state media && chown -R athena /app
USER athena
CMD exec uvicorn athena.api:app --host 0.0.0.0 --port ${PORT} --ws-ping-interval 20 --proxy-headers --forwarded-allow-ips='*'
