# Use a small Python image for the FastAPI gateway container.
FROM python:3.10-slim

# Keep the application files inside a predictable container directory.
WORKDIR /app

# Install dependencies before copying source code so Docker can reuse this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application package into the image.
COPY app/ ./app

# Document the port used by Uvicorn inside the container.
EXPOSE 8080

# Start the gateway and listen on all container network interfaces.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]