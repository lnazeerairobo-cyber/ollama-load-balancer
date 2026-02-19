load_balancer_host = "0.0.0.0"
load_balancer_port = 11434

ollama_servers = [
    {"host": "ollama-1", "port": 11434},
    {"host": "ollama-2", "port": 11434},
    {"host": "ollama-3", "port": 11434},
]

metrics_interval = 2
health_check_interval = 5
request_timeout = 300
unhealthy_threshold = 3
recovery_delay = 30
