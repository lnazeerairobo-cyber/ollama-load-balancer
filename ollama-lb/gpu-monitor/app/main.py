from fastapi import FastAPI
import os
import asyncio
from .gpu import GPUMonitor
from .ollama import get_active_requests
from pydantic import BaseModel
from typing import list

app = FastAPI(title="GPU Monitor Sidecar")

gpu_monitor = GPUMonitor()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

cached_active_requests = 0


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_ollama())


async def poll_ollama():
    global cached_active_requests
    while True:
        cached_active_requests = await get_active_requests(OLLAMA_HOST, OLLAMA_PORT)
        await asyncio.sleep(2)


class GPUMetrics(BaseModel):
    index: int
    name: str
    utilization: int
    memory_used_gb: float
    memory_total_gb: float
    temperature: int


class MetricsResponse(BaseModel):
    active_requests: int
    gpus: list[GPUMetrics]
    gpu_count: int
    gpu_utilization: int
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    gpu_temperature: int


@app.get("/metrics", response_model=MetricsResponse)
async def metrics():
    gpu_metrics = gpu_monitor.get_metrics()
    return MetricsResponse(
        active_requests=cached_active_requests,
        gpus=[GPUMetrics(**gpu) for gpu in gpu_metrics["gpus"]],
        gpu_count=gpu_metrics["gpu_count"],
        gpu_utilization=gpu_metrics["gpu_utilization"],
        gpu_memory_used_gb=gpu_metrics["gpu_memory_used_gb"],
        gpu_memory_total_gb=gpu_metrics["gpu_memory_total_gb"],
        gpu_temperature=gpu_metrics["gpu_temperature"],
    )


@app.get("/health")
async def health():
    return {"status": "healthy"}
