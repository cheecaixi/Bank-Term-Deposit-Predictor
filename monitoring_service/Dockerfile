# Builds the Docker image for the FastAPI Monitoring Service.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app # Copies the Monitoring Service application into the container

EXPOSE 7002 # Documents port 7002 used by the Monitoring Service

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7002"]
# Starts the FastAPI Monitoring Service using Uvicorn on port 7002