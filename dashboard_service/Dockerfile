# Small Python base image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Streamlit
EXPOSE 8501

# Default Gateway URL for local development
ENV GATEWAY_URL=http://localhost:8080

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]