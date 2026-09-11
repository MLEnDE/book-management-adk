# Production Multi-Stage Dockerfile for Google Cloud Agent Runtime / Cloud Run
# Conforms to Gemini Enterprise Agent Platform container runtime standards

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080 \
    ADK_APP_DATA_DIR=/var/data/book_management

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN groupadd -g 10001 agentgroup && \
    useradd -u 10001 -g agentgroup -s /bin/bash -m agentuser && \
    mkdir -p /var/data/book_management && \
    chown -R agentuser:agentgroup /var/data/book_management /app

COPY . /app/book_management_adk
RUN chown -R agentuser:agentgroup /app/book_management_adk

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

CMD ["uvicorn", "book_management_adk.server:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
