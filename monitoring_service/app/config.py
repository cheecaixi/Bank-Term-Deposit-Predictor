import os


AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:7000")
GATEWAY_SERVICE_URL = os.getenv(
    "GATEWAY_SERVICE_URL",
    "http://localhost:8080"
)
DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL",
    "http://localhost:8000"
)
DASHBOARD_SERVICE_URL = os.getenv(
    "DASHBOARD_SERVICE_URL",
    "http://localhost:8501"
)
MONITORING_DATABASE_PATH = os.getenv(
    "MONITORING_DATABASE_PATH",
    "monitoring.db"
)
POLL_INTERVAL_SECONDS = max(
    5,
    int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
)
REQUEST_TIMEOUT_SECONDS = max(
    1.0,
    float(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
)
LOG_RETENTION_LIMIT = max(
    100,
    int(os.getenv("LOG_RETENTION_LIMIT", "5000"))
)


MONITORED_SERVICES = {
    "ai-interface": AI_SERVICE_URL,
    "api-gateway": GATEWAY_SERVICE_URL,
    "database-service": DATABASE_SERVICE_URL,
    "dashboard-service": DASHBOARD_SERVICE_URL,
}

SERVICE_HEALTH_PATHS = {
    "dashboard-service": "/_stcore/health",
}
