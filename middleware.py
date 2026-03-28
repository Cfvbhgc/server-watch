import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from monitoring.collector import ServerCollector

logger = logging.getLogger(__name__)


class AlertMiddleware(BaseMiddleware):
    """
    Middleware для проверки порогов при каждом входящем сообщении.
    If thresholds exceeded - send proactive alert to the user.
    Не спамит: шлет алерт максимум раз в 5 минут на юзера.
    """

    def __init__(self, collector: ServerCollector, alert_users: set):
        self.collector = collector
        self.alert_users = alert_users  # set of user ids who enabled alerts
        self._last_alert: dict[int, float] = {}  # user_id -> timestamp
        self._cooldown = 300  # 5 min cooldown between alerts

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # only check on incoming messages
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            if user_id in self.alert_users:
                import time
                now = time.time()
                last = self._last_alert.get(user_id, 0)

                if now - last > self._cooldown:
                    alerts = self.collector.check_alerts()
                    if alerts:
                        self._last_alert[user_id] = now
                        alert_text = (
                            "⚠️ <b>Внимание! Превышены пороги:</b>\n\n"
                            + "\n".join(f"• {a}" for a in alerts)
                        )
                        try:
                            bot = data.get("bot")
                            if bot:
                                await bot.send_message(
                                    user_id, alert_text, parse_mode="HTML"
                                )
                        except Exception as e:
                            logger.error(f"Failed to send alert: {e}")

        return await handler(event, data)
