# AGENTS.md

Guidelines for AI coding agents working in this repository.

## Project Overview

Ollama Load Balancer - A GPU-aware load balancer for managing multiple Ollama inference servers. Routes requests to the least-loaded server based on GPU utilization and active request count.

**Architecture:**
- `load-balancer/` - FastAPI reverse proxy with health checking and metrics collection
- `gpu-monitor/` - Sidecar service that exposes GPU metrics via HTTP
- `tests/` - pytest-based unit tests

## Build & Run Commands

```bash
# Start all services (requires Docker + NVIDIA GPU)
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f load-balancer
```

## Test Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a single test file
pytest tests/test_routing.py

# Run a single test function
pytest tests/test_routing.py::TestLoadBalancer::test_select_server_least_loaded

# Run tests matching a pattern
pytest -k "server"
```

## Lint & Type Check Commands

```bash
pip install ruff mypy
ruff check .
mypy load-balancer/app gpu-monitor/app
```

## Code Style Guidelines

### Imports

```python
# Standard library first
import asyncio
from datetime import datetime
from typing import Dict, Optional

# Third-party packages second
import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

# Local imports last (relative for intra-package)
from .models import ServerMetrics
from . import config
```

### Formatting

- 4-space indentation
- Max line length: ~100 characters
- Blank lines between logical sections

### Type Hints

Always use type hints for function signatures:

```python
def update_metrics(self, host: str, port: int, metrics_data: dict) -> None: ...
async def get_active_requests(ollama_host: str, ollama_port: int) -> int: ...
def select_server(self) -> Optional[ServerMetrics]: ...
```

Use `Optional[T]` for nullable return types. Use `list[T]` not `List[T]`.

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables/Functions | snake_case | `active_requests`, `select_server()` |
| Classes | PascalCase | `LoadBalancer`, `ServerMetrics` |
| Constants | snake_case | `OLLAMA_HOST`, `request_timeout` |
| Private methods | _leading_underscore | `_init_servers()` |

### Error Handling

```python
# HTTP operations
try:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url)
except httpx.RequestError as e:
    # Handle network errors

# FastAPI endpoints
from fastapi import HTTPException
if not server:
    raise HTTPException(status_code=503, detail="No healthy servers available")
```

Bare `except Exception:` is acceptable for background tasks where failures should be silently ignored.

### Pydantic Models

```python
from pydantic import BaseModel
from typing import Optional

class ServerMetrics(BaseModel):
    host: str
    port: int
    active_requests: int = 0
    is_healthy: bool = True
    last_check: Optional[datetime] = None

    def score(self) -> float:
        return self.active_requests * 10 + self.gpu_utilization
```

### Configuration

Use module-level variables in `config.py`. For env vars:

```python
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
```

### Async Patterns

```python
# Background tasks
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(metrics_collector())

# HTTP clients
async with httpx.AsyncClient(timeout=5.0) as client:
    resp = await client.get(url)
```

### Testing

- Place tests in `tests/` directory
- Use class-based organization: `class TestFeatureName:`
- Tests must be self-contained (import fresh instances)

```python
import sys
sys.path.insert(0, "/root/ollama-lb/load-balancer")

from app.routing import LoadBalancer

class TestLoadBalancer:
    def test_load_balancer_init(self):
        lb = LoadBalancer()
        assert len(lb.servers) == 3
```

## File Structure

```
ollama-lb/
├── load-balancer/
│   ├── app/main.py      # FastAPI app, routes, background tasks
│   ├── app/config.py    # Configuration constants
│   ├── app/models.py    # Pydantic models
│   ├── app/proxy.py     # Request proxying logic
│   └── app/routing.py   # LoadBalancer class
├── gpu-monitor/
│   ├── app/main.py      # FastAPI app
│   ├── app/gpu.py       # GPUMonitor class (pynvml)
│   └── app/ollama.py    # Ollama API client
├── tests/test_routing.py
├── docker-compose.yml
└── pytest.ini
```

## Key Dependencies

- **FastAPI** - Web framework
- **Pydantic** - Data validation/models
- **httpx** - Async HTTP client
- **pynvml** - NVIDIA GPU monitoring
- **pytest** + **pytest-asyncio** - Testing
