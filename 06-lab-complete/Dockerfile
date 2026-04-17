# STAGE 1: Builder
FROM python:3.11-slim AS builder
WORKDIR /app
# Copy source code
COPY 06-lab-complete/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# STAGE 2: Runtime
FROM python:3.11-slim AS runtime
WORKDIR /app

# Bảo mật: Tạo user mới
RUN useradd -m myuser
USER myuser

# Copy packages từ stage 1
COPY --from=builder /root/.local /home/myuser/.local
ENV PATH=/home/myuser/.local/bin:$PATH

# Copy source code
COPY --chown=myuser:myuser 06-lab-complete/ .
COPY --chown=myuser:myuser utils/ ./utils/

# Biến môi trường
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Tự động kiểm tra sức khỏe từ bên trong Container
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:$PORT/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "app.main"]
