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
                "gpu_utilization": 0,
                "gpu_memory_used_gb": 0.0,
                "gpu_memory_total_gb": 0.0,
                "gpu_temperature": 0,
            }

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
            except Exception:
                continue

        avg_util = total_util // self.device_count if self.device_count > 0 else 0

        return {
            "gpu_utilization": avg_util,
            "gpu_memory_used_gb": round(total_mem_used / (1024**3), 2),
            "gpu_memory_total_gb": round(total_mem / (1024**3), 2),
            "gpu_temperature": max_temp,
        }

    def __del__(self):
        if self.initialized:
            pynvml.nvmlShutdown()
