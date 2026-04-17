FROM python:3.11-slim
WORKDIR /app
COPY 05-scaling-reliability/develop/requirements.txt .
RUN pip install -r requirements.txt
RUN pip install redis
COPY 05-scaling-reliability/production/app.py .
COPY utils/mock_llm.py /app/utils/mock_llm.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
