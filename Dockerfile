# Small Python base image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (Docker caches this layer if requirements.txt
# doesn't change, so rebuilds are faster)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Streamlit's default port
EXPOSE 8501

# GATEWAY_URL can be overridden at `docker run` time with -e, e.g.:
#   docker run -e GATEWAY_URL=http://gateway-service:8000 -p 8501:8501 dashboard-service
ENV GATEWAY_URL=http://localhost:8000

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
