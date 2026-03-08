# python:3.12-slim recommended by Google Cloud for Cloud Run Python services
# https://docs.cloud.google.com/run/docs/tips/python
FROM python:3.12-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying source — maximizes layer cache hits
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "fastapi[standard]>=0.135.1" \
        "anthropic>=0.84.0" \
        "pydantic>=2.10.0" \
        "uvicorn[standard]>=0.34.0" \
        "google-cloud-storage>=2.18.0"

# Copy application source
COPY src/ ./src/

# Run as non-root user
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# Cloud Run injects $PORT at runtime (default 8080)
ENV PORT=8080
EXPOSE $PORT

# Single uvicorn worker — Cloud Run handles horizontal scaling via instances
CMD exec uvicorn src.lead_enrichment.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 1 \
    --log-level info
