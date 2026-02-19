from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from .proxy import proxy_request, proxy_streaming_request, is_streaming_request
from .routing import lb
from . import config
import httpx
import asyncio
from datetime import datetime, timedelta

app = FastAPI(title="Ollama Load Balancer")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(metrics_collector())
    asyncio.create_task(health_checker())


async def metrics_collector():
    while True:
        for server in config.ollama_servers:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    sidecar_port = server["port"] + 1000
                    resp = await client.get(f"http://{server['host']}-monitor:{sidecar_port}/metrics")
                    if resp.status_code == 200:
                        lb.update_metrics(server["host"], server["port"], resp.json())
            except Exception:
                lb.mark_unhealthy(server["host"], server["port"])
        await asyncio.sleep(config.metrics_interval)


async def health_checker():
    while True:
        for server in config.ollama_servers:
            if not lb.servers.get(f"{server['host']}:{server['port']}", None):
                continue
            server_state = lb.servers[f"{server['host']}:{server['port']}"]
            if not server_state.is_healthy:
                if server_state.last_check and \
                   datetime.utcnow() - server_state.last_check > timedelta(seconds=config.recovery_delay):
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            resp = await client.get(f"http://{server['host']}:{server['port']}/api/tags")
                            if resp.status_code == 200:
                                server_state.is_healthy = True
                                server_state.consecutive_failures = 0
                    except Exception:
                        pass
        await asyncio.sleep(config.health_check_interval)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path: str):
    server = lb.select_server()
    if not server:
        raise HTTPException(status_code=503, detail="No healthy servers available")

    try:
        if is_streaming_request(request):
            return await proxy_streaming_request(request, server.host, server.port)
        else:
            return await proxy_request(request, server.host, server.port)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/servers")
async def list_servers():
    return {
        "servers": [
            {
                "host": s.host,
                "port": s.port,
                "active_requests": s.active_requests,
                "gpus": [gpu.model_dump() for gpu in s.gpus],
                "gpu_count": s.gpu_count,
                "gpu_utilization": s.gpu_utilization,
                "gpu_memory_used_gb": s.gpu_memory_used_gb,
                "gpu_memory_total_gb": s.gpu_memory_total_gb,
                "gpu_temperature": s.gpu_temperature,
                "is_healthy": s.is_healthy,
                "score": s.score()
            }
            for s in lb.servers.values()
        ]
    }
