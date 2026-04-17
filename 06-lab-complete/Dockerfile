# STAGE 1: Builder
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# STAGE 2: Runtime
FROM python:3.11-slim
WORKDIR /app

# Copy packages từ stage 1
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . .

# Biến môi trường mặc định
ENV PORT=8000
ENV AGENT_API_KEY=h2a-secret-key

EXPOSE 8000

# Chạy ứng dụng thông qua module python để tự động xử lý PORT
CMD ["python", "-m", "app.main"]
