from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GPUMetrics(BaseModel):
    index: int
    name: str
    utilization: int
    memory_used_gb: float
    memory_total_gb: float
    temperature: int


class ServerMetrics(BaseModel):
    host: str
    port: int
    active_requests: int = 0
    gpus: list[GPUMetrics] = []
    gpu_count: int = 0
    gpu_utilization: int = 0
    gpu_memory_used_gb: float = 0.0
    gpu_memory_total_gb: float = 0.0
    gpu_temperature: int = 0
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_check: Optional[datetime] = None

    def score(self) -> float:
        return self.active_requests * 10 + self.gpu_utilization

    def get_available_gpu_capacity(self) -> float:
        if not self.gpus or self.gpu_memory_total_gb == 0:
            return 0.0
        return self.gpu_memory_total_gb - self.gpu_memory_used_gb

    def get_least_loaded_gpu(self) -> Optional[GPUMetrics]:
        if not self.gpus:
            return None
        return min(self.gpus, key=lambda g: g.utilization)


class ServerMetricsResponse(BaseModel):
    active_requests: int
    gpus: list[GPUMetrics]
    gpu_count: int
    gpu_utilization: int
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    gpu_temperature: int
