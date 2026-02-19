from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ServerMetrics(BaseModel):
    host: str
    port: int
    active_requests: int = 0
    gpu_utilization: int = 0
    gpu_memory_used_gb: float = 0.0
    gpu_memory_total_gb: float = 0.0
    gpu_temperature: int = 0
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_check: Optional[datetime] = None

    def score(self) -> float:
        return self.active_requests * 10 + self.gpu_utilization


class ServerMetricsResponse(BaseModel):
    active_requests: int
    gpu_utilization: int
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    gpu_temperature: int
