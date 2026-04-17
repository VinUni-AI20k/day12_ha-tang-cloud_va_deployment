# ============================================================
# Multi-stage build — Stage 1: builder, Stage 2: slim runtime
# Final image < 500 MB, non-root user
# ============================================================

# Stage 1: Builder — install dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Runtime — clean image, no build tools
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

# Copy installed packages into system Python path (avoids --user path issues)
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY utils/ ./utils/

RUN chown -R agent:agent /app

USER agent

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
