FROM python:3.11-slim

WORKDIR /app

# Cài đặt thư viện
COPY 05-scaling-reliability/develop/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install redis  # Cần cho phần Scaling

# Copy source code và utils
COPY 05-scaling-reliability/production/ .
COPY utils/ /app/utils/

# Biến môi trường
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
