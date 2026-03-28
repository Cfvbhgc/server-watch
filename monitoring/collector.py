import psutil
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MetricSnapshot:
    timestamp: float
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    net_bytes_sent: int
    net_bytes_recv: int


class ServerCollector:
    """Собирает метрики сервера и хранит историю.
    Keeps last N readings in a deque for chart generation."""

    def __init__(self, max_readings: int = 60,
                 cpu_threshold: float = 80.0,
                 ram_threshold: float = 90.0):
        self.history: deque[MetricSnapshot] = deque(maxlen=max_readings)
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        # для расчета скорости сети
        self._last_net = psutil.net_io_counters()
        self._last_net_time = time.time()

    def collect(self) -> MetricSnapshot:
        """Collect current metrics and append to history"""
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent

        net = psutil.net_io_counters()
        snapshot = MetricSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu,
            ram_percent=ram,
            disk_percent=disk,
            net_bytes_sent=net.bytes_sent,
            net_bytes_recv=net.bytes_recv,
        )
        self.history.append(snapshot)
        self._last_net = net
        self._last_net_time = time.time()
        return snapshot

    def get_latest(self) -> Optional[MetricSnapshot]:
        if self.history:
            return self.history[-1]
        return self.collect()

    def check_alerts(self) -> list[str]:
        """Check thresholds, вернуть список предупреждений"""
        alerts = []
        latest = self.get_latest()
        if latest is None:
            return alerts

        if latest.cpu_percent > self.cpu_threshold:
            alerts.append(
                f"CPU загрузка {latest.cpu_percent:.1f}% "
                f"(порог: {self.cpu_threshold}%)"
            )
        if latest.ram_percent > self.ram_threshold:
            alerts.append(
                f"RAM использование {latest.ram_percent:.1f}% "
                f"(порог: {self.ram_threshold}%)"
            )
        return alerts

    def get_cpu_history(self) -> list[float]:
        return [s.cpu_percent for s in self.history]

    def get_ram_history(self) -> list[float]:
        return [s.ram_percent for s in self.history]

    def get_timestamps(self) -> list[float]:
        return [s.timestamp for s in self.history]

    # quick summary for /status
    def format_status(self) -> str:
        snap = self.get_latest()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot = psutil.boot_time()
        uptime_sec = time.time() - boot
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        mins = int((uptime_sec % 3600) // 60)

        net = psutil.net_io_counters()
        sent_mb = net.bytes_sent / (1024 * 1024)
        recv_mb = net.bytes_recv / (1024 * 1024)

        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"

        text = (
            f"<b>Обзор сервера</b>\n"
            f"{'─' * 28}\n\n"
            f"<b>CPU:</b> {snap.cpu_percent:.1f}% ({cpu_count} cores, {freq_str})\n"
            f"<b>RAM:</b> {snap.ram_percent:.1f}% "
            f"({mem.used // (1024**2)} / {mem.total // (1024**2)} MB)\n"
            f"<b>Disk:</b> {snap.disk_percent:.1f}% "
            f"({disk.used // (1024**3)} / {disk.total // (1024**3)} GB)\n\n"
            f"<b>Network:</b>\n"
            f"  ↑ Sent: {sent_mb:.1f} MB\n"
            f"  ↓ Recv: {recv_mb:.1f} MB\n\n"
            f"<b>Uptime:</b> {days}d {hours}h {mins}m\n"
            f"{'─' * 28}\n"
            f"<i>readings in buffer: {len(self.history)}</i>"
        )
        return text
