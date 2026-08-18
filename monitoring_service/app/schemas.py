from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogCreate(BaseModel):
    # Defaults make this endpoint compatible with Student B's gateway
    # middleware, which sends only request execution details.
    service: str = Field(default="api-gateway", min_length=1, max_length=100)
    level: Optional[LogLevel] = None
    event: str = Field(default="api_request", max_length=100)
    message: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    method: Optional[str] = Field(default=None, max_length=10)
    endpoint: Optional[str] = Field(default=None, max_length=500)
    status_code: Optional[int] = Field(default=None, ge=100, le=599)
    response_time_ms: Optional[float] = Field(default=None, ge=0)
    execution_time_seconds: Optional[float] = Field(default=None, ge=0)
    metadata: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def normalize_gateway_log(self):
        if (
            self.response_time_ms is None
            and self.execution_time_seconds is not None
        ):
            self.response_time_ms = round(
                self.execution_time_seconds * 1000,
                2
            )

        if self.level is None:
            if self.status_code is not None and self.status_code >= 500:
                self.level = "ERROR"
            elif self.status_code is not None and self.status_code >= 400:
                self.level = "WARNING"
            else:
                self.level = "INFO"

        if self.message is None:
            request_name = " ".join(
                part for part in (self.method, self.endpoint) if part
            ) or "API request"
            status_text = (
                f" returned HTTP {self.status_code}"
                if self.status_code is not None
                else " completed"
            )
            self.message = request_name + status_text

        return self


class ServiceStatus(BaseModel):
    service: str
    url: str
    status: Literal["healthy", "unhealthy"]
    status_code: Optional[int] = None
    response_time_ms: float
    checked_at: str
    error: Optional[str] = None
