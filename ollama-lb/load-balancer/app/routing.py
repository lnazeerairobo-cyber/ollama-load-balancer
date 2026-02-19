from typing import Dict, Optional
from .models import ServerMetrics
from . import config


class LoadBalancer:
    def __init__(self):
        self.servers: Dict[str, ServerMetrics] = {}
        self._init_servers()

    def _init_servers(self):
        for i, server in enumerate(config.ollama_servers):
            key = f"{server['host']}:{server['port']}"
            self.servers[key] = ServerMetrics(
                host=server["host"],
                port=server["port"]
            )

    def update_metrics(self, host: str, port: int, metrics_data: dict):
        key = f"{host}:{port}"
        if key in self.servers:
            server = self.servers[key]
            server.active_requests = metrics_data.get("active_requests", 0)
            server.gpu_utilization = metrics_data.get("gpu_utilization", 0)
            server.gpu_memory_used_gb = metrics_data.get("gpu_memory_used_gb", 0.0)
            server.gpu_memory_total_gb = metrics_data.get("gpu_memory_total_gb", 0.0)
            server.gpu_temperature = metrics_data.get("gpu_temperature", 0)
            from datetime import datetime
            server.last_check = datetime.utcnow()
            server.is_healthy = True
            server.consecutive_failures = 0

    def mark_unhealthy(self, host: str, port: int):
        key = f"{host}:{port}"
        if key in self.servers:
            server = self.servers[key]
            server.consecutive_failures += 1
            if server.consecutive_failures >= config.unhealthy_threshold:
                server.is_healthy = False

    def get_healthy_servers(self) -> list[ServerMetrics]:
        return [s for s in self.servers.values() if s.is_healthy]

    def select_server(self) -> Optional[ServerMetrics]:
        healthy = self.get_healthy_servers()
        if not healthy:
            return None
        return min(healthy, key=lambda s: s.score())

    def increment_requests(self, host: str, port: int):
        key = f"{host}:{port}"
        if key in self.servers:
            self.servers[key].active_requests += 1

    def decrement_requests(self, host: str, port: int):
        key = f"{host}:{port}"
        if key in self.servers:
            self.servers[key].active_requests = max(0, self.servers[key].active_requests - 1)


lb = LoadBalancer()
