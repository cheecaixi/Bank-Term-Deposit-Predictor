from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogCreate(BaseModel):
    service: str = Field(min_length=1, max_length=100)
    level: LogLevel = "INFO"
    event: str = Field(default="application", max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    method: Optional[str] = Field(default=None, max_length=10)
    endpoint: Optional[str] = Field(default=None, max_length=500)
    status_code: Optional[int] = Field(default=None, ge=100, le=599)
    response_time_ms: Optional[float] = Field(default=None, ge=0)
    metadata: Optional[dict[str, Any]] = None


class ServiceStatus(BaseModel):
    service: str
    url: str
    status: Literal["healthy", "unhealthy"]
    status_code: Optional[int] = None
    response_time_ms: float
    checked_at: str
    error: Optional[str] = None
