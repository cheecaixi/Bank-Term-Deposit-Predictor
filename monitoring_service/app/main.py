# Main FastAPI application for the Monitoring Service.
# Provides service health checks, centralized logs, and monitoring metrics.

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, status

from app.config import MONITORED_SERVICES, POLL_INTERVAL_SECONDS
from app.monitor import check_all_services, monitoring_loop
from app.schemas import LogCreate
from app.storage import add_log, get_logs, get_metrics, initialize_database

# Manages startup and shutdown tasks for the Monitoring Service
@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database() # Initializes the monitoring database when the service starts
    add_log(LogCreate(
        service="monitoring-service",
        event="startup",
        message="Monitoring service started",
    ))
    # Starts the background monitoring loop
    monitor_task = asyncio.create_task(monitoring_loop())
    try:
        yield
    finally:
         # Stops the background monitoring task when the service shuts down
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

# Creates and configures the FastAPI Monitoring Service application
app = FastAPI(
    title="Bank Marketing Monitoring Service",
    description=(
        "Student D service for system health monitoring, logs and errors"
    ),
    version="1.0.0",
    lifespan=lifespan,
    # Organizes API endpoints into sections in Swagger documentation
    openapi_tags=[
        {
            "name": "Monitoring Service",
            "description": "Information and health of Student D's monitoring service.",
        },
        {
            "name": "Microservice Status",
            "description": (
                "Live health checks for Student A's AI interface, Student B's "
                "API gateway, Student D's database service, and the Streamlit "
                "dashboard."
            ),
        },
        {
            "name": "System Logs",
            "description": "Collect and retrieve logs from the monitored system.",
        },
        {
            "name": "Monitoring Metrics",
            "description": "Aggregated log, error, warning and response-time metrics.",
        },
    ],
)

# Returns basic information about the Monitoring Service
@app.get(
    "/",
    tags=["Monitoring Service"],
    summary="Get monitoring service information",
    description=(
        "Identifies Student D's monitoring service and lists the four "
        "microservices it monitors."
    ),
)
def root():
    return {
        "service": "monitoring-service",
        "status": "running",
        "monitored_services": list(MONITORED_SERVICES),
    }

# Checks whether the Monitoring Service itself is running
@app.get(
    "/health",
    tags=["Monitoring Service"],
    summary="Check the monitoring service health",
    description=(
        "Checks whether the monitoring service itself is running. This does "
        "not check the AI, gateway, database, or dashboard services."
    ),
)
def health():
    return {"status": "healthy", "service": "monitoring-service"}

# Checks the health and response time of all monitored microservices
@app.get(
    "/status",
    tags=["Microservice Status"],
    summary="Check AI, Gateway, Database and Dashboard health",
    description=(
        "Actively calls /health on Student A's AI interface, Student B's API "
        "gateway, Student D's database service, and the Streamlit dashboard, "
        "then returns their status and response time."
    ),
)
async def service_status():
     # Performs health checks on all configured services
    checks = await check_all_services()
    return { # System is healthy only when every monitored service is healthy
        "overall_status": (
            "healthy"
            if all(item["status"] == "healthy" for item in checks)
            else "degraded"
        ),
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "services": checks,
    }

# Retrieves monitoring and application logs
@app.get(
    "/logs",
    tags=["System Logs"],
    summary="Get logs collected from monitored services",
    description=(
        "Returns recent monitoring and application logs. Student B's "
        "GET /api/logs endpoint forwards requests to this endpoint."
    ),
)
def logs(
      # Limits how many logs are returned (1–1000)
    limit: int = Query(default=100, ge=1, le=1000),
    service: Optional[str] = None, # Optionally filters logs by service
    level: Optional[str] = Query(default=None, pattern="^[A-Z]+$"), # Optionally filters logs by level such as INFO, WARNING or ERROR
):
    return get_logs(limit=limit, service=service, level=level)

# Receives and stores structured logs sent by other microservices
@app.post(
    "/logs",
    status_code=status.HTTP_201_CREATED,
    tags=["System Logs"],
    summary="Receive a log from a microservice",
    description=(
        "Stores a structured log sent by the AI interface, API gateway, "
        "database service, or another approved system component."
    ),
)
def create_log(log: LogCreate):
    return add_log(log)

# Calculates and returns aggregated monitoring metrics
@app.get(
    "/metrics",
    tags=["Monitoring Metrics"],
    summary="Get error, warning and response-time metrics",
    description=(
        "Summarises stored logs across the AI interface, API gateway, and "
        "database service for Student C's future monitoring dashboard."
    ),
)
def metrics():
    return get_metrics()
