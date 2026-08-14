import os

class Settings:
    PROJECT_NAME: str = "Bank Marketing API Gateway"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # Internal Microservice URLs (read from environment variables with fallbacks)
    INFERENCE_SERVICE_URL: str = os.getenv("INFERENCE_SERVICE_URL", "http://localhost:7000")
    DATABASE_SERVICE_URL: str = os.getenv("DATABASE_SERVICE_URL", "http://localhost:8000")
    MONITORING_SERVICE_URL: str = os.getenv("MONITORING_SERVICE_URL", "http://localhost:7002")

    # Gateway Server Settings
    PORT: int = int(os.getenv("PORT", 8080))
    TIMEOUT_SECONDS: float = float(os.getenv("TIMEOUT_SECONDS", 5.0))

settings = Settings()