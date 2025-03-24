FROM python:3.10-slim

ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "etl_api:app", "--host", "0.0.0.0", "--port", "5000"]
