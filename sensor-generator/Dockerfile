FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY send_stream.py .

CMD ["python", "send_stream.py", "--path", "/data/f1.csv", "--base-url", "http://gateway:8080", "--rate", "50"]