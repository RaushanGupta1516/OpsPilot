from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class EnvironmentEnum(str, Enum):
    production = "production"
    staging = "staging"
    development = "development"


class AppCreate(BaseModel):
    name: str
    url: str
    environment: EnvironmentEnum = EnvironmentEnum.production
    render_id: Optional[str] = None


class AppResponse(BaseModel):
    id: str
    name: str
    url: str
    environment: str
    baseline_ready: bool
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MetricResponse(BaseModel):
    id: str
    app_id: str
    endpoint: str
    response_time_ms: Optional[int]
    status_code: Optional[int]
    error_rate: float
    memory_mb: Optional[float]
    cpu_percent: Optional[float]
    is_healthy: bool
    recorded_at: datetime

    class Config:
        from_attributes = True


class HealthCheckResult(BaseModel):
    app_id: str
    app_name: str
    is_healthy: bool
    response_time_ms: Optional[int]
    status_code: Optional[int]
    error_rate: float
    memory_mb: Optional[float]
    cpu_percent: Optional[float]
    message: str