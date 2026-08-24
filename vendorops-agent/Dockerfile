FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable

ENV PYTHONUNBUFFERED=1 \
    OTEL_SERVICE_NAME=vendorops-agent \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_LOGS_EXPORTER=otlp \
    OTEL_METRICS_EXPORTER=none \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
    OTEL_BSP_SCHEDULE_DELAY=1000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -sf http://localhost:8080/ping || exit 1

CMD ["uv", "run", "--no-dev", "python", "src/agent.py"]
