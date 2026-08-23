# Performs asynchronous health checks on all configured microservices,
# records their status and response times, and continuously monitors them.

import asyncio
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import httpx

from app.config import (
    MONITORED_SERVICES,
    POLL_INTERVAL_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SERVICE_HEALTH_PATHS,
)
from app.schemas import LogCreate
from app.storage import add_log

# Checks the health of one microservice and records the result
async def check_service(
    client: httpx.AsyncClient,
    service: str,
    base_url: str,
) -> dict[str, Any]:
     # Gets the service-specific health path or uses /health by default
    health_path = SERVICE_HEALTH_PATHS.get(service, "/health")

     # Creates the complete URL for the health check
    health_url = f"{base_url.rstrip('/')}{health_path}"

    # Records the start time to calculate response time
    started_at = perf_counter()

     # Records when the health check was performed
    checked_at = datetime.now(timezone.utc).isoformat()

    try:
        # Sends an asynchronous GET request to the service health endpoint
        response = await client.get(health_url)

         # Calculates how long the service took to respond
        response_time_ms = round((perf_counter() - started_at) * 1000, 2)

         # Considers HTTP 2xx responses as healthy
        healthy = 200 <= response.status_code < 300
        status = "healthy" if healthy else "unhealthy"

         # Records HTTP error if the service is not healthy
        error = None if healthy else f"HTTP {response.status_code}"
    except httpx.RequestError as error_detail:
        # Handles connection errors or unavailable services
        response_time_ms = round((perf_counter() - started_at) * 1000, 2)
        status = "unhealthy"
        response = None
        error = str(error_detail)
    # Gets the HTTP status code if a response was received
    status_code = response.status_code if response is not None else None
    add_log(LogCreate(
        service=service,
        level="INFO" if status == "healthy" else "ERROR",
        event="health_check",
        method="GET",
        endpoint=health_url,
        status_code=status_code,
        response_time_ms=response_time_ms,
        message=(
            f"{service} is healthy"
            if status == "healthy"
            else f"{service} health check failed: {error}"
        ),
    ))
    # Returns the health-check result for the service
    return {
        "service": service,
        "url": base_url,
        "status": status,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "checked_at": checked_at,
        "error": error,
    }

# Checks all configured microservices concurrently
async def check_all_services() -> list[dict[str, Any]]:
    # Sets the maximum time allowed for each request
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)
    # Creates an asynchronous HTTP client
    async with httpx.AsyncClient(timeout=timeout) as client:
         # Creates a health-check task for every monitored service
        checks = [
            check_service(client, service, url)
            for service, url in MONITORED_SERVICES.items()
        ]
         # Runs all service health checks at the same time
        return await asyncio.gather(*checks)

# Continuously checks all services at the configured interval
async def monitoring_loop() -> None:
    while True:
        await check_all_services()  # Performs health checks on all monitored services
        await asyncio.sleep(POLL_INTERVAL_SECONDS) # Waits before performing the next round of checks
