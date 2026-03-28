from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def status_keyboard() -> InlineKeyboardMarkup:
    """Keyboard под /status - refresh и доп. действия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Обновить", callback_data="refresh_status"),
            InlineKeyboardButton(text="График", callback_data="overview_chart"),
        ],
        [
            InlineKeyboardButton(text="CPU детали", callback_data="detail_cpu"),
            InlineKeyboardButton(text="RAM детали", callback_data="detail_ram"),
        ],
        [
            InlineKeyboardButton(text="Диски", callback_data="detail_disk"),
        ]
    ])


def cpu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Обновить график", callback_data="refresh_cpu"),
        ],
        [
            InlineKeyboardButton(text="Назад к статусу", callback_data="back_status"),
        ]
    ])


def ram_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Refresh RAM chart", callback_data="refresh_ram"),
        ],
        [
            InlineKeyboardButton(text="Назад", callback_data="back_status"),
        ]
    ])


def disk_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Обновить", callback_data="refresh_disk"),
            InlineKeyboardButton(text="Назад", callback_data="back_status"),
        ]
    ])


def alerts_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    """Toggle alerts on/off"""
    toggle_text = "Выключить алерты" if enabled else "Включить алерты"
    toggle_data = "alerts_off" if enabled else "alerts_on"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=toggle_text, callback_data=toggle_data),
        ],
        [
            InlineKeyboardButton(text="Текущие пороги", callback_data="show_thresholds"),
        ]
    ])
