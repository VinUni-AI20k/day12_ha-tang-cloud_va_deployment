FROM python:3.11-slim

WORKDIR /app

# Cài đặt thư viện
COPY 02-docker/develop/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code của agent
COPY 02-docker/develop/ .

# Copy thư mục utils từ thư mục gốc vào container
COPY utils/ ./utils/

# Mặc định chạy server
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
