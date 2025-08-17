FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the streaming script
COPY send_stream.py .

# Default command - can be overridden in docker-compose
CMD ["python", "send_stream.py", "--path", "/data/f1.csv", "--base-url", "http://gateway:8080", "--rate", "50"]