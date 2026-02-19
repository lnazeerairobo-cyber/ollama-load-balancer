# Ollama Load Balancer Design

**Date:** 2026-02-19  
**Status:** Approved  

## Overview

GPU-aware load balancer for managing 2-3 Ollama servers in production using FastAPI with Docker Compose. Routes requests to the least-loaded server based on active requests and GPU utilization to minimize queue wait times.

## Requirements

- Load balance across 2-3 Ollama instances
- GPU-aware routing (avoid queued servers)
- Support streaming (SSE) and non-streaming requests
- Automatic health checks and failover
- Simple deployment with Docker Compose
- Shared model storage across instances

## Architecture

```
                    ┌─────────────────────┐
                    │   FastAPI LB        │
                    │   :11434            │
                    │                     │
                    │  - Poll metrics     │
                    │  - Route to least   │
                    │    loaded server    │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
   ┌───────────┐         ┌───────────┐         ┌───────────┐
   │ Ollama 1  │         │ Ollama 2  │         │ Ollama 3  │
   │ :11435    │         │ :11436    │         │ :11437    │
   │           │         │           │         │           │
   │ + Sidecar │         │ + Sidecar │         │ + Sidecar │
   │   (GPU    │         │   (GPU    │         │   (GPU    │
   │  monitor) │         │  monitor) │         │  monitor) │
   └───────────┘         └───────────┘         └───────────┘
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │ Shared Volume       │
                    │ ollama_models       │
                    │ (/root/.ollama)     │
                    └─────────────────────┘
```

## Components

### 1. FastAPI Load Balancer

**Port:** 11434 (Ollama's default)

**Responsibilities:**
- Accept incoming requests
- Query cached server metrics
- Select server with lowest load
- Proxy requests with streaming support
- Track active requests per server
- Perform health checks

**Routing Algorithm:**
```
score = active_requests * 10 + gpu_utilization_percent
select server with lowest score
fallback to round-robin if scores equal
```

**Key Libraries:**
- `fastapi` - web framework
- `httpx` - async HTTP client
- `uvicorn` - ASGI server

### 2. GPU Monitor Sidecar

**One per Ollama instance**

**Responsibilities:**
- Poll GPU stats via `pynvml`
- Query Ollama `/api/ps` for active jobs
- Expose `/metrics` endpoint

**Metrics Endpoint Response:**
```json
{
  "active_requests": 2,
  "gpu_utilization": 75,
  "gpu_memory_used_gb": 12.5,
  "gpu_memory_total_gb": 24.0,
  "gpu_temperature": 65
}
```

**Polling Interval:** Every 2 seconds

### 3. Ollama Servers

**Ports:** 11435, 11436, 11437

**Configuration:**
- Share models via named volume
- Each has dedicated GPU monitor sidecar
- Standard Ollama container

### 4. Docker Compose

**Services:**
- `load-balancer` - FastAPI proxy
- `ollama-1`, `ollama-2`, `ollama-3` - Ollama instances
- `gpu-monitor-1`, `gpu-monitor-2`, `gpu-monitor-3` - Sidecars

**Volumes:**
- `ollama_models:/root/.ollama` - Shared model storage

## Data Flow

### Request Flow

```
Client Request
     │
     ▼
FastAPI LB (11434)
     │
     ├─► Check cached server metrics
     │
     ├─► Select least-loaded server
     │
     ├─► Increment request counter
     │
     ├─► Proxy request (streaming-aware)
     │
     └─► Decrement counter on completion
     │
     ▼
Client Response (streamed)
```

### Metrics Collection

```
FastAPI LB                          GPU Sidecar (each)
    │                                      │
    │──── GET /metrics ────────────────────│ (every 2s)
    │◄─── {active, gpu_util, mem} ────────│
    │                                      │
    │  Update in-memory server state       │
```

## Error Handling

### Backend Failures

| Scenario | Action |
|----------|--------|
| Request fails | Mark unhealthy, retry next server |
| 3 consecutive failures | Remove from rotation for 30s |
| Health check passes | Auto-recover into rotation |
| All backends down | Return 503, log alert |

### GPU Sidecar Failures

| Scenario | Action |
|----------|--------|
| `/metrics` unreachable | Use last known state |
| Stale for >10s | Fallback to round-robin |

### Streaming Errors

| Scenario | Action |
|----------|--------|
| Connection drop mid-stream | Cleanup counter, log error |
| Request timeout | 5 min default, configurable |

## Project Structure

```
ollama-lb/
├── docker-compose.yml
├── load-balancer/
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routing.py
│   │   ├── proxy.py
│   │   └── models.py
│   └── requirements.txt
├── gpu-monitor/
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── gpu.py
│   │   └── ollama.py
│   └── requirements.txt
└── tests/
    ├── test_routing.py
    ├── test_proxy.py
    └── test_integration.py
```

## Configuration

**Environment Variables (Load Balancer):**

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_SERVERS` | `ollama-1:11435,ollama-2:11436,ollama-3:11437` | Comma-separated backends |
| `METRICS_INTERVAL` | `2` | Metrics poll interval (seconds) |
| `HEALTH_CHECK_INTERVAL` | `5` | Health check interval (seconds) |
| `REQUEST_TIMEOUT` | `300` | Request timeout (seconds) |
| `UNHEALTHY_THRESHOLD` | `3` | Failures before removal |
| `RECOVERY_DELAY` | `30` | Seconds before retry |

**Environment Variables (GPU Monitor):**

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `localhost:11434` | Local Ollama instance |
| `METRICS_PORT` | `8080` | Metrics server port |
| `POLL_INTERVAL` | `2` | GPU poll interval (seconds) |

## Testing Strategy

### Unit Tests

- Routing algorithm correctness
- Metric parsing and aggregation
- Health check logic
- Score calculation

### Integration Tests

- End-to-end request proxying
- Streaming response handling
- Failover behavior
- Metrics collection

### Load Tests

- Concurrent request handling
- Load distribution verification
- GPU-aware routing effectiveness
- Performance under load

## Deployment

```bash
# Build and start
docker compose up -d --build

# Scale up
docker compose up -d --scale ollama=4

# View logs
docker compose logs -f load-balancer

# Stop
docker compose down
```

## Future Enhancements

- [ ] Prometheus metrics export
- [ ] Grafana dashboard
- [ ] API key authentication
- [ ] Rate limiting per client
- [ ] Request queueing with priority
- [ ] Multi-GPU per server support
