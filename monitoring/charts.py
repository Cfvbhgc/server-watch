import io
import datetime
import matplotlib
matplotlib.use('Agg')  # headless backend, без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from monitoring.collector import ServerCollector


def _timestamps_to_labels(timestamps: list[float]) -> list[datetime.datetime]:
    return [datetime.datetime.fromtimestamp(t) for t in timestamps]


def generate_cpu_chart(collector: ServerCollector) -> io.BytesIO:
    """Line chart CPU% over time. Returns PNG as BytesIO."""
    cpu_data = collector.get_cpu_history()
    ts = collector.get_timestamps()

    if len(cpu_data) < 2:
        # not enough data - generate placeholder
        return _placeholder_chart("CPU", "Недостаточно данных для графика")

    times = _timestamps_to_labels(ts)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times, cpu_data, color='#e74c3c', linewidth=2, marker='o',
            markersize=3, label='CPU %')
    ax.fill_between(times, cpu_data, alpha=0.15, color='#e74c3c')
    ax.axhline(y=collector.cpu_threshold, color='orange',
               linestyle='--', alpha=0.7, label=f'Порог ({collector.cpu_threshold}%)')

    ax.set_ylim(0, 100)
    ax.set_title('CPU Usage', fontsize=14, fontweight='bold')
    ax.set_ylabel('%')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    plt.close(fig)
    return buf


def generate_ram_chart(collector: ServerCollector) -> io.BytesIO:
    ram_data = collector.get_ram_history()
    ts = collector.get_timestamps()

    if len(ram_data) < 2:
        return _placeholder_chart("RAM", "Мало данных, подождите")

    times = _timestamps_to_labels(ts)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times, ram_data, color='#3498db', linewidth=2,
            marker='s', markersize=3, label='RAM %')
    ax.fill_between(times, ram_data, alpha=0.15, color='#3498db')
    ax.axhline(y=collector.ram_threshold, color='orange',
               linestyle='--', alpha=0.7, label=f'Threshold ({collector.ram_threshold}%)')

    ax.set_ylim(0, 100)
    ax.set_title('RAM Usage', fontsize=14, fontweight='bold')
    ax.set_ylabel('%')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    plt.close(fig)
    return buf


def generate_overview_chart(collector: ServerCollector) -> io.BytesIO:
    """Combined chart - CPU and RAM на одном графике"""
    cpu_data = collector.get_cpu_history()
    ram_data = collector.get_ram_history()
    ts = collector.get_timestamps()

    if len(cpu_data) < 2:
        return _placeholder_chart("Overview", "Собираем данные...")

    times = _timestamps_to_labels(ts)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    # cpu subplot
    ax1.plot(times, cpu_data, color='#e74c3c', linewidth=2, label='CPU %')
    ax1.fill_between(times, cpu_data, alpha=0.1, color='#e74c3c')
    ax1.set_ylim(0, 100)
    ax1.set_title('Server Metrics Overview', fontsize=14, fontweight='bold')
    ax1.set_ylabel('CPU %')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # ram subplot
    ax2.plot(times, ram_data, color='#3498db', linewidth=2, label='RAM %')
    ax2.fill_between(times, ram_data, alpha=0.1, color='#3498db')
    ax2.set_ylim(0, 100)
    ax2.set_ylabel('RAM %')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    plt.close(fig)
    return buf


def _placeholder_chart(title: str, message: str) -> io.BytesIO:
    """Generate a simple placeholder when not enough data available"""
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.text(0.5, 0.5, message, transform=ax.transAxes,
            ha='center', va='center', fontsize=16, color='gray')
    ax.set_title(title)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    return buf
