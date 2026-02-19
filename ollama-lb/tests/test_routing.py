import pytest
import sys
sys.path.insert(0, "/root/ollama-lb/load-balancer")

from app.models import ServerMetrics, GPUMetrics


class TestLoadBalancer:
    def test_load_balancer_init(self):
        from app.routing import LoadBalancer
        lb = LoadBalancer()
        assert len(lb.servers) == 3

    def test_update_metrics(self):
        from app.routing import LoadBalancer
        lb = LoadBalancer()
        lb.update_metrics("ollama-1", 11434, {
            "active_requests": 2,
            "gpu_utilization": 75,
            "gpu_memory_used_gb": 12.0,
            "gpu_memory_total_gb": 24.0,
            "gpu_temperature": 65
        })
        
        server = lb.servers["ollama-1:11434"]
        assert server.active_requests == 2
        assert server.gpu_utilization == 75
        assert server.is_healthy == True

    def test_update_metrics_multi_gpu(self):
        from app.routing import LoadBalancer
        lb = LoadBalancer()
        lb.update_metrics("ollama-1", 11434, {
            "active_requests": 3,
            "gpus": [
                {"index": 0, "name": "RTX 4090", "utilization": 80, "memory_used_gb": 20.0, "memory_total_gb": 24.0, "temperature": 70},
                {"index": 1, "name": "RTX 4090", "utilization": 40, "memory_used_gb": 10.0, "memory_total_gb": 24.0, "temperature": 65}
            ],
            "gpu_count": 2,
            "gpu_utilization": 60,
            "gpu_memory_used_gb": 30.0,
            "gpu_memory_total_gb": 48.0,
            "gpu_temperature": 70
        })
        
        server = lb.servers["ollama-1:11434"]
        assert server.active_requests == 3
        assert server.gpu_count == 2
        assert len(server.gpus) == 2
        assert server.gpus[0].utilization == 80
        assert server.gpus[1].utilization == 40
        assert server.gpu_memory_total_gb == 48.0

    def test_select_server_least_loaded(self):
        from app.routing import LoadBalancer
        lb = LoadBalancer()
        
        lb.update_metrics("ollama-1", 11434, {"active_requests": 5, "gpu_utilization": 80})
        lb.update_metrics("ollama-2", 11434, {"active_requests": 1, "gpu_utilization": 30})
        lb.update_metrics("ollama-3", 11434, {"active_requests": 3, "gpu_utilization": 50})
        
        selected = lb.select_server()
        assert selected.host == "ollama-2"

    def test_mark_unhealthy(self):
        from app.routing import LoadBalancer
        lb = LoadBalancer()
        
        for _ in range(3):
            lb.mark_unhealthy("ollama-1", 11434)
        
        server = lb.servers["ollama-1:11434"]
        assert server.is_healthy == False

    def test_get_healthy_servers(self):
        from app.routing import LoadBalancer
        lb = LoadBalancer()
        
        lb.update_metrics("ollama-1", 11434, {"active_requests": 0, "gpu_utilization": 0})
        lb.update_metrics("ollama-2", 11434, {"active_requests": 0, "gpu_utilization": 0})
        
        for _ in range(3):
            lb.mark_unhealthy("ollama-1", 11434)
        
        healthy = lb.get_healthy_servers()
        assert len(healthy) == 2
        assert all(s.host != "ollama-1" for s in healthy)

    def test_server_score(self):
        server = ServerMetrics(
            host="test",
            port=11434,
            active_requests=2,
            gpu_utilization=50
        )
        
        assert server.score() == 70

    def test_server_get_least_loaded_gpu(self):
        server = ServerMetrics(
            host="test",
            port=11434,
            gpus=[
                GPUMetrics(index=0, name="GPU 0", utilization=80, memory_used_gb=20.0, memory_total_gb=24.0, temperature=70),
                GPUMetrics(index=1, name="GPU 1", utilization=30, memory_used_gb=10.0, memory_total_gb=24.0, temperature=65),
            ]
        )
        
        least_loaded = server.get_least_loaded_gpu()
        assert least_loaded.index == 1
        assert least_loaded.utilization == 30

    def test_server_available_capacity(self):
        server = ServerMetrics(
            host="test",
            port=11434,
            gpu_memory_used_gb=30.0,
            gpu_memory_total_gb=48.0,
            gpus=[
                GPUMetrics(index=0, name="GPU 0", utilization=80, memory_used_gb=20.0, memory_total_gb=24.0, temperature=70),
                GPUMetrics(index=1, name="GPU 1", utilization=30, memory_used_gb=10.0, memory_total_gb=24.0, temperature=65),
            ]
        )
        
        capacity = server.get_available_gpu_capacity()
        assert capacity == 18.0
