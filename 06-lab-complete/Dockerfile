# ============================================================
# Production Dockerfile — Multi-stage, < 500 MB, non-root
# ============================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Non-root user
RUN groupadd -r agent && useradd -r -g agent -m -d /home/agent agent

WORKDIR /app

# Copy packages từ builder
COPY --from=builder /root/.local /home/agent/.local

# Copy application
COPY app/ ./app/
COPY utils/ ./utils/

RUN chown -R agent:agent /app /home/agent

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV HOME=/home/agent
ENV PYTHONUSERBASE=/home/agent/.local
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
    "import os, urllib.request; urllib.request.urlopen(f\"http://localhost:{os.getenv('PORT','8000')}/health\")" \
    || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
