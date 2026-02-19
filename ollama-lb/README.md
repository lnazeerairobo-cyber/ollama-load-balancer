# Ollama Load Balancer

GPU-aware load balancer for managing multiple Ollama servers in production.

## Features

- **GPU-Aware Routing**: Routes requests to least-loaded server based on GPU utilization and active requests
- **Streaming Support**: Handles SSE streaming responses
- **Automatic Failover**: Health checks with automatic server removal/recovery
- **Shared Model Storage**: Docker volume for models across instances

## Quick Start

```bash
docker compose up -d
```

## Architecture

```
Client → FastAPI LB (:11434) → Ollama 1/2/3 + GPU Sidecars
```

## Configuration

See `.env.example` for configuration options.
