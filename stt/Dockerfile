FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 libatomic1 unzip wget && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "stt:app", "--host", "0.0.0.0", "--port", "8001"]
