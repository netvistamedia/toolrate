FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM python:3.12-slim

RUN groupadd -r nemoflow && useradd -r -g nemoflow nemoflow

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN chown -R nemoflow:nemoflow /app
USER nemoflow

EXPOSE 8000
# --proxy-headers makes uvicorn honor X-Forwarded-For from the reverse proxy
# so `request.client.host` resolves to the real client IP, not Caddy's
# container IP. Without this flag, per-IP rate limits and the reporter
# fingerprint collapse to a single shared bucket in production.
# --forwarded-allow-ips="*" is only safe because docker-compose binds 8000
# to the loopback interface (see docker-compose.yml), so the only process
# that can set those headers is the Caddy container on the same host.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips=*"]
