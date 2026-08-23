import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, status

from app.config import MONITORED_SERVICES, POLL_INTERVAL_SECONDS
from app.monitor import check_all_services, monitoring_loop
from app.schemas import LogCreate
from app.storage import add_log, get_logs, get_metrics, initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    add_log(LogCreate(
        service="monitoring-service",
        event="startup",
        message="Monitoring service started",
    ))
    monitor_task = asyncio.create_task(monitoring_loop())
    try:
        yield
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Bank Marketing Monitoring Service",
    description=(
        "Student D service for system health monitoring, logs and errors"
    ),
    version="1.0.0",
    lifespan=lifespan,
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
    checks = await check_all_services()
    return {
        "overall_status": (
            "healthy"
            if all(item["status"] == "healthy" for item in checks)
            else "degraded"
        ),
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "services": checks,
    }


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
    limit: int = Query(default=100, ge=1, le=1000),
    service: Optional[str] = None,
    level: Optional[str] = Query(default=None, pattern="^[A-Z]+$"),
):
    return get_logs(limit=limit, service=service, level=level)


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
