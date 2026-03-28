import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile

from monitoring.collector import ServerCollector
from monitoring.charts import generate_cpu_chart, generate_ram_chart, generate_overview_chart
from keyboards import status_keyboard, cpu_keyboard, ram_keyboard, disk_keyboard, alerts_keyboard
import psutil

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "refresh_status")
async def cb_refresh_status(callback: CallbackQuery, collector: ServerCollector):
    collector.collect()
    text = collector.format_status()
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=status_keyboard())
    await callback.answer("Обновлено")


@router.callback_query(F.data == "overview_chart")
async def cb_overview(callback: CallbackQuery, collector: ServerCollector):
    """Send combined overview chart"""
    collector.collect()
    chart_buf = generate_overview_chart(collector)
    photo = BufferedInputFile(chart_buf.read(), filename="overview.png")
    await callback.message.answer_photo(photo, caption="Общий обзор метрик")
    await callback.answer()


@router.callback_query(F.data == "detail_cpu")
async def cb_cpu_detail(callback: CallbackQuery, collector: ServerCollector):
    collector.collect()
    chart_buf = generate_cpu_chart(collector)
    photo = BufferedInputFile(chart_buf.read(), filename="cpu.png")
    await callback.message.answer_photo(
        photo, caption="CPU usage chart", reply_markup=cpu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "detail_ram")
async def cb_ram_detail(callback: CallbackQuery, collector: ServerCollector):
    collector.collect()
    buf = generate_ram_chart(collector)
    photo = BufferedInputFile(buf.read(), filename="ram.png")
    await callback.message.answer_photo(
        photo, caption="RAM chart", reply_markup=ram_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "detail_disk")
async def cb_disk_detail(callback: CallbackQuery):
    """Показать инфу о дисках - same as /disk basically"""
    partitions = psutil.disk_partitions()
    text = f"<b>Диски</b>\n{'─' * 25}\n\n"
    for part in partitions:
        try:
            u = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        pct = u.percent
        filled = int(pct / 5)
        bar = '█' * filled + '░' * (20 - filled)
        text += (
            f"<b>{part.mountpoint}</b>\n"
            f"  [{bar}] {pct}%\n"
            f"  {u.used // (1024**3)}/{u.total // (1024**3)} GB\n\n"
        )
    await callback.message.answer(text, parse_mode="HTML",
                                  reply_markup=disk_keyboard())
    await callback.answer()


@router.callback_query(F.data == "refresh_cpu")
async def cb_refresh_cpu(callback: CallbackQuery, collector: ServerCollector):
    collector.collect()
    buf = generate_cpu_chart(collector)
    photo = BufferedInputFile(buf.read(), filename="cpu_refresh.png")
    await callback.message.answer_photo(photo, caption="CPU (обновлено)",
                                        reply_markup=cpu_keyboard())
    await callback.answer("График обновлен")


@router.callback_query(F.data == "refresh_ram")
async def cb_refresh_ram(callback: CallbackQuery, collector: ServerCollector):
    collector.collect()
    buf = generate_ram_chart(collector)
    photo = BufferedInputFile(buf.read(), filename="ram_refresh.png")
    await callback.message.answer_photo(photo, caption="RAM (updated)",
                                        reply_markup=ram_keyboard())
    await callback.answer("Done")


@router.callback_query(F.data == "refresh_disk")
async def cb_refresh_disk(callback: CallbackQuery):
    # просто триггерим заново
    partitions = psutil.disk_partitions()
    text = f"<b>Диски</b>\n\n"
    for part in partitions:
        try:
            u = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        text += f"{part.mountpoint}: {u.percent}% ({u.used//(1024**3)}/{u.total//(1024**3)} GB)\n"
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=disk_keyboard())
    await callback.answer()


@router.callback_query(F.data == "back_status")
async def cb_back_status(callback: CallbackQuery, collector: ServerCollector):
    collector.collect()
    text = collector.format_status()
    await callback.message.answer(text, parse_mode="HTML",
                                  reply_markup=status_keyboard())
    await callback.answer()


# alert toggles
@router.callback_query(F.data == "alerts_on")
async def cb_alerts_on(callback: CallbackQuery, collector: ServerCollector, alert_users: set):
    uid = callback.from_user.id
    alert_users.add(uid)
    await callback.message.edit_text(
        f"Алерты <b>включены</b> для вас.\n\n"
        f"CPU порог: {collector.cpu_threshold}%\n"
        f"RAM порог: {collector.ram_threshold}%",
        parse_mode="HTML",
        reply_markup=alerts_keyboard(True)
    )
    await callback.answer("Alerts enabled")


@router.callback_query(F.data == "alerts_off")
async def cb_alerts_off(callback: CallbackQuery, collector: ServerCollector, alert_users: set):
    uid = callback.from_user.id
    alert_users.discard(uid)
    await callback.message.edit_text(
        "Алерты <b>выключены</b>.",
        parse_mode="HTML",
        reply_markup=alerts_keyboard(False)
    )
    await callback.answer("Alerts disabled")


@router.callback_query(F.data == "show_thresholds")
async def cb_thresholds(callback: CallbackQuery, collector: ServerCollector):
    await callback.answer(
        f"CPU: {collector.cpu_threshold}% | RAM: {collector.ram_threshold}%",
        show_alert=True
    )
