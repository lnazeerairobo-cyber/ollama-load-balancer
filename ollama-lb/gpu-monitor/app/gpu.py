import pynvml
from typing import Optional


class GPUMonitor:
    def __init__(self):
        self.initialized = False
        try:
            pynvml.nvmlInit()
            self.device_count = pynvml.nvmlDeviceGetCount()
            self.initialized = True
        except Exception:
            self.device_count = 0

    def get_metrics(self) -> dict:
        if not self.initialized:
            return {
                "gpus": [],
                "gpu_count": 0,
                "gpu_utilization": 0,
                "gpu_memory_used_gb": 0.0,
                "gpu_memory_total_gb": 0.0,
                "gpu_temperature": 0,
            }

        gpus = []
        total_util = 0
        total_mem_used = 0
        total_mem = 0
        max_temp = 0

        for i in range(self.device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                total_util += util.gpu

                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_mem_used += mem_info.used
                total_mem += mem_info.total

                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                max_temp = max(max_temp, temp)

                gpus.append({
                    "index": i,
                    "name": pynvml.nvmlDeviceGetName(handle),
                    "utilization": util.gpu,
                    "memory_used_gb": round(mem_info.used / (1024**3), 2),
                    "memory_total_gb": round(mem_info.total / (1024**3), 2),
                    "temperature": temp,
                })
            except Exception:
                continue

        avg_util = total_util // len(gpus) if gpus else 0

        return {
            "gpus": gpus,
            "gpu_count": len(gpus),
            "gpu_utilization": avg_util,
            "gpu_memory_used_gb": round(total_mem_used / (1024**3), 2),
            "gpu_memory_total_gb": round(total_mem / (1024**3), 2),
            "gpu_temperature": max_temp,
        }

    def __del__(self):
        if self.initialized:
            pynvml.nvmlShutdown()
