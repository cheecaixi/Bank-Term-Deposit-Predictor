import os

# Central configuration for backend service addresses and gateway settings.
class Settings:
    PROJECT_NAME: str = "Bank Marketing API Gateway"
    VERSION: str = "1.0.0"

    # Read service URLs from the environment; localhost values support local runs.
    INFERENCE_SERVICE_URL: str = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:7000")
    DATABASE_SERVICE_URL: str = os.getenv("DATABASE_SERVICE_URL", "http://localhost:8000")
    MONITORING_SERVICE_URL: str = os.getenv("MONITORING_SERVICE_URL", "http://localhost:7002")

    # Gateway server settings used by the application and deployment configuration.
    PORT: int = int(os.getenv("PORT", 8080))
    TIMEOUT_SECONDS: float = float(os.getenv("TIMEOUT_SECONDS", 5.0))

# Create one shared settings object for the FastAPI application.
settings = Settings()