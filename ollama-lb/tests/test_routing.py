import pytest
import sys
sys.path.insert(0, "/root/ollama-lb/load-balancer")

from app.models import ServerMetrics


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
