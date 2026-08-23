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


async def check_service(
    client: httpx.AsyncClient,
    service: str,
    base_url: str,
) -> dict[str, Any]:
    health_path = SERVICE_HEALTH_PATHS.get(service, "/health")
    health_url = f"{base_url.rstrip('/')}{health_path}"
    started_at = perf_counter()
    checked_at = datetime.now(timezone.utc).isoformat()

    try:
        response = await client.get(health_url)
        response_time_ms = round((perf_counter() - started_at) * 1000, 2)
        healthy = 200 <= response.status_code < 300
        status = "healthy" if healthy else "unhealthy"
        error = None if healthy else f"HTTP {response.status_code}"
    except httpx.RequestError as error_detail:
        response_time_ms = round((perf_counter() - started_at) * 1000, 2)
        status = "unhealthy"
        response = None
        error = str(error_detail)

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

    return {
        "service": service,
        "url": base_url,
        "status": status,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "checked_at": checked_at,
        "error": error,
    }


async def check_all_services() -> list[dict[str, Any]]:
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        checks = [
            check_service(client, service, url)
            for service, url in MONITORED_SERVICES.items()
        ]
        return await asyncio.gather(*checks)


async def monitoring_loop() -> None:
    while True:
        await check_all_services()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
