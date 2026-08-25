# Defines Pydantic data models for validating and standardizing monitoring logs
# and service health-check results.
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Defines the allowed log severity levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Defines the structure and validation rules for logs received by the Monitoring Service
class LogCreate(BaseModel):
    # Defaults make this endpoint compatible with Student B's gateway
    # middleware, which sends only request execution details.
    service: str = Field(default="api-gateway", min_length=1, max_length=100)

    # Log severity level such as INFO, WARNING, or ERROR
    level: Optional[LogLevel] = None

    # Type of event being logged
    event: str = Field(default="api_request", max_length=100)
    # Human-readable description of the log
    message: Optional[str] = Field(default=None, min_length=1, max_length=2000)
     # HTTP request method such as GET, POST, PUT, or DELETE
    method: Optional[str] = Field(default=None, max_length=10)
    # API endpoint associated with the log
    endpoint: Optional[str] = Field(default=None, max_length=500)
     # HTTP response status code
    status_code: Optional[int] = Field(default=None, ge=100, le=599)
     # Request response time measured in milliseconds
    response_time_ms: Optional[float] = Field(default=None, ge=0)
    # Request execution time measured in seconds
    execution_time_seconds: Optional[float] = Field(default=None, ge=0)
    # Stores optional additional information about the log
    metadata: Optional[dict[str, Any]] = None

    # Automatically normalizes and completes log information after validation
    @model_validator(mode="after")
    def normalize_gateway_log(self):
        # Converts execution time from seconds to milliseconds when needed
        if (
            self.response_time_ms is None
            and self.execution_time_seconds is not None
        ):
            self.response_time_ms = round(
                self.execution_time_seconds * 1000,
                2
            )
        # Automatically determines the log level based on HTTP status code
        if self.level is None:
            if self.status_code is not None and self.status_code >= 500:
                self.level = "ERROR"
             # Client errors (4xx) are classified as WARNING
            elif self.status_code is not None and self.status_code >= 400:
                self.level = "WARNING"
            else: # Other responses are classified as INFO
                self.level = "INFO"

        # Automatically generates a message if none was provided
        if self.message is None:
            # Combines the HTTP method and endpoint
            request_name = " ".join(
                part for part in (self.method, self.endpoint) if part
            ) or "API request"
            # Adds the HTTP status code when available
            status_text = (
                f" returned HTTP {self.status_code}"
                if self.status_code is not None
                else " completed"
            )
            self.message = request_name + status_text

        return self

# Defines the structure of a microservice health-check result
class ServiceStatus(BaseModel):
    service: str # Name of the monitored service
    url: str # Base URL of the service
    status: Literal["healthy", "unhealthy"]  # HTTP response status code
    status_code: Optional[int] = None # Service response time in milliseconds
    response_time_ms: float # Service response time in milliseconds
    checked_at: str  # Time when the health check was performed
    error: Optional[str] = None # Error details if the health check failed
