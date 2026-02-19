import httpx
from typing import Optional


async def get_active_requests(ollama_host: str, ollama_port: int) -> int:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://{ollama_host}:{ollama_port}/api/ps")
            if resp.status_code == 200:
                data = resp.json()
                return len(data.get("models", []))
    except Exception:
        pass
    return 0
