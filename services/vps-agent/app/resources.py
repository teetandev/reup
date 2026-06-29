"""Host resource sampling (CPU / RAM / disk) for /status and future heartbeats."""

from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass
class ResourceInfo:
    """A point-in-time snapshot of host resource usage."""

    cpu_percent: float
    ram_used_mb: int
    ram_total_mb: int
    disk_free_gb: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "disk_free_gb": self.disk_free_gb,
        }


def sample_resources(disk_path: str) -> ResourceInfo:
    """Sample CPU, memory, and free disk space for ``disk_path``.

    ``cpu_percent`` uses a non-blocking read (``interval=None``): it reports
    usage since the previous call, so the first sample after start may be 0.0.
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_path)
    return ResourceInfo(
        cpu_percent=round(psutil.cpu_percent(interval=None), 1),
        ram_used_mb=int(mem.used / (1024 * 1024)),
        ram_total_mb=int(mem.total / (1024 * 1024)),
        disk_free_gb=round(disk.free / (1024 * 1024 * 1024), 1),
    )
