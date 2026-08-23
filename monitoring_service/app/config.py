# Defines configuration settings for the Monitoring Service, including
# service URLs, health-check intervals, timeouts, logging, and monitored services.

import os

# Gets the AI Interface URL from environment variables or uses localhost by default
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:7000")

# Gets the API Gateway URL
GATEWAY_SERVICE_URL = os.getenv(
    "GATEWAY_SERVICE_URL",
    "http://localhost:8080"
)
# Gets the Database Service URL
DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL",
    "http://localhost:8000"
)
# Gets the Dashboard Service URL
DASHBOARD_SERVICE_URL = os.getenv(
    "DASHBOARD_SERVICE_URL",
    "http://localhost:8501"
)
# Defines the location of the SQLite database used for monitoring data
MONITORING_DATABASE_PATH = os.getenv(
    "MONITORING_DATABASE_PATH",
    "monitoring.db"
)
# Sets how often service health checks are performed (minimum 5 seconds)
POLL_INTERVAL_SECONDS = max(
    5,
    int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
)
# Sets the maximum time to wait for a service response (minimum 1 second)
REQUEST_TIMEOUT_SECONDS = max(
    1.0,
    float(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
)

# Sets the maximum number of monitoring logs to retain (minimum 100)
LOG_RETENTION_LIMIT = max(
    100,
    int(os.getenv("LOG_RETENTION_LIMIT", "5000"))
)

# Defines all services that will be monitored and their corresponding URLs
MONITORED_SERVICES = {
    "ai-interface": AI_SERVICE_URL,
    "api-gateway": GATEWAY_SERVICE_URL,
    "database-service": DATABASE_SERVICE_URL,
    "dashboard-service": DASHBOARD_SERVICE_URL,
}
# Defines custom health-check endpoints for services that require them
SERVICE_HEALTH_PATHS = {
    "dashboard-service": "/_stcore/health",
}
