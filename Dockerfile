# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm ci --strict-ssl=true --no-audit --no-fund
COPY frontend ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_URL=sqlite:////app/state/quality.db
WORKDIR /app
COPY requirements.lock ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -r requirements.lock && useradd --create-home --uid 10001 qualisiq && \
    mkdir -p /app/state /app/artifacts && chown -R qualisiq:qualisiq /app/state /app/artifacts
COPY --chown=qualisiq:qualisiq app ./app
COPY --chown=qualisiq:qualisiq ml ./ml
COPY --chown=qualisiq:qualisiq scripts ./scripts
COPY --chown=qualisiq:qualisiq migrations ./migrations
COPY --chown=qualisiq:qualisiq alembic.ini ./
COPY --from=web --chown=qualisiq:qualisiq /web/dist ./frontend/dist
USER qualisiq
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready',timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
