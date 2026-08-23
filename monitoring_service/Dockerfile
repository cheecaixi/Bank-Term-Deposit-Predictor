# Builds the Docker image for the FastAPI Monitoring Service.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copies the Monitoring Service application into the container
COPY app ./app

# Documents port 7002 used by the Monitoring Service
EXPOSE 7002

# Starts the FastAPI Monitoring Service using Uvicorn on port 7002
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7002"]
