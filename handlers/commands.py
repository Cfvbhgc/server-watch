import psutil
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from monitoring.collector import ServerCollector
from monitoring.charts import generate_cpu_chart, generate_ram_chart
from keyboards import status_keyboard, cpu_keyboard, ram_keyboard, disk_keyboard, alerts_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот для мониторинга сервера.\n\n"
        "Доступные команды:\n"
        "/status - обзор системы\n"
        "/cpu - загрузка процессора + график\n"
        "/ram - использование памяти + график\n"
        "/disk - информация о дисках\n"
        "/alerts - настройка уведомлений\n"
        "/help - помощь",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    # keep it short
    await message.answer(
        "<b>Server Watch Bot</b>\n\n"
        "/status - полная сводка\n"
        "/cpu - CPU info + chart\n"
        "/ram - RAM info + chart\n"
        "/disk - disk partitions\n"
        "/alerts - manage alert notifications",
        parse_mode="HTML"
    )


@router.message(Command("status"))
async def cmd_status(message: Message, collector: ServerCollector):
    """Большой хендлер - собираем всю инфу и красиво форматируем.
    This is intentionally verbose because status needs lots of detail."""
    collector.collect()  # свежие данные
    text = collector.format_status()

    # добавляем информацию о load average если доступно
    try:
        load1, load5, load15 = psutil.getloadavg()
        text += f"\n\n<b>Load Average:</b> {load1:.2f} / {load5:.2f} / {load15:.2f}"
    except (AttributeError, OSError):
        pass

    # top processes by CPU - полезно для отладки
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            info = proc.info
            if info['cpu_percent'] and info['cpu_percent'] > 0:
                procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    procs.sort(key=lambda x: x['cpu_percent'], reverse=True)
    if procs[:5]:
        text += "\n\n<b>Top processes (CPU):</b>\n"
        for p in procs[:5]:
            text += f"  <code>{p['name'][:20]:20s} {p['cpu_percent']:5.1f}%</code>\n"

    # temperature если есть (linux)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            text += "\n<b>Температура:</b>\n"
            for name, entries in list(temps.items())[:3]:
                for entry in entries[:2]:
                    text += f"  {name}/{entry.label or 'core'}: {entry.current:.0f}°C\n"
    except (AttributeError, RuntimeError):
        # not available on all platforms - это нормально
        pass

    await message.answer(text, parse_mode="HTML", reply_markup=status_keyboard())


@router.message(Command("cpu"))
async def cmd_cpu(message: Message, collector: ServerCollector):
    """CPU details + send chart as photo"""
    collector.collect()

    cpu_count_logical = psutil.cpu_count()
    cpu_count_physical = psutil.cpu_count(logical=False)
    freq = psutil.cpu_freq()
    per_cpu = psutil.cpu_percent(percpu=True, interval=0.3)

    text = f"<b>Процессор</b>\n{'─' * 25}\n\n"
    text += f"Ядер: {cpu_count_physical} physical / {cpu_count_logical} logical\n"
    if freq:
        text += f"Частота: {freq.current:.0f} MHz (max: {freq.max:.0f})\n"
    text += f"\nОбщая загрузка: <b>{collector.get_latest().cpu_percent:.1f}%</b>\n"

    # per-core breakdown
    if per_cpu:
        text += "\nПо ядрам:\n"
        for i, pct in enumerate(per_cpu):
            bar_len = int(pct / 10)
            bar = '█' * bar_len + '░' * (10 - bar_len)
            text += f"  Core {i}: {bar} {pct:.0f}%\n"

    await message.answer(text, parse_mode="HTML")

    # generate and send chart
    chart_buf = generate_cpu_chart(collector)
    photo = BufferedInputFile(chart_buf.read(), filename="cpu_chart.png")
    await message.answer_photo(photo, caption="CPU usage history",
                               reply_markup=cpu_keyboard())


@router.message(Command("ram"))
async def cmd_ram(message: Message, collector: ServerCollector):
    collector.collect()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # quick text summary
    text = (
        f"<b>Память (RAM)</b>\n{'─' * 25}\n\n"
        f"Total: {mem.total // (1024**2)} MB\n"
        f"Used: {mem.used // (1024**2)} MB ({mem.percent}%)\n"
        f"Available: {mem.available // (1024**2)} MB\n"
        f"Cached: {getattr(mem, 'cached', 0) // (1024**2)} MB\n\n"
        f"<b>Swap:</b>\n"
        f"Total: {swap.total // (1024**2)} MB\n"
        f"Used: {swap.used // (1024**2)} MB ({swap.percent}%)\n"
    )
    await message.answer(text, parse_mode="HTML")

    chart_buf = generate_ram_chart(collector)
    photo = BufferedInputFile(chart_buf.read(), filename="ram_chart.png")
    await message.answer_photo(photo, caption="RAM usage over time",
                               reply_markup=ram_keyboard())


@router.message(Command("disk"))
async def cmd_disk(message: Message):
    """Disk usage per partition"""
    partitions = psutil.disk_partitions()
    text = f"<b>Дисковое пространство</b>\n{'─' * 25}\n\n"

    for part in partitions:
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue

        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)

        # visual bar
        pct = usage.percent
        filled = int(pct / 5)
        bar = '█' * filled + '░' * (20 - filled)

        text += (
            f"<b>{part.mountpoint}</b> ({part.fstype})\n"
            f"  [{bar}] {pct}%\n"
            f"  {used_gb:.1f} / {total_gb:.1f} GB "
            f"(свободно: {free_gb:.1f} GB)\n\n"
        )

    # io counters if available
    try:
        io = psutil.disk_io_counters()
        if io:
            text += (
                f"<b>Disk I/O (total):</b>\n"
                f"  Read: {io.read_bytes // (1024**2)} MB\n"
                f"  Write: {io.write_bytes // (1024**2)} MB\n"
            )
    except RuntimeError:
        pass

    await message.answer(text, parse_mode="HTML", reply_markup=disk_keyboard())


@router.message(Command("alerts"))
async def cmd_alerts(message: Message, collector: ServerCollector, alert_users: set):
    user_id = message.from_user.id
    is_enabled = user_id in alert_users

    status_text = "включены" if is_enabled else "выключены"
    text = (
        f"<b>Настройки алертов</b>\n\n"
        f"Статус: <b>{status_text}</b>\n\n"
        f"Пороги:\n"
        f"  CPU: {collector.cpu_threshold}%\n"
        f"  RAM: {collector.ram_threshold}%\n\n"
        f"При превышении порогов бот отправит предупреждение."
    )
    await message.answer(text, parse_mode="HTML",
                         reply_markup=alerts_keyboard(is_enabled))
