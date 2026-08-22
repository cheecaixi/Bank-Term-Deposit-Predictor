FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY training ./training
COPY models ./models
COPY inference ./inference

EXPOSE 7000

CMD ["uvicorn", "inference.app:app", "--host", "0.0.0.0", "--port", "7000"]