import os
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from monitoring.collector import ServerCollector
from handlers import commands as cmd_handlers
from handlers import callbacks as cb_handlers
from middleware import AlertMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CPU_THRESHOLD = float(os.getenv("ALERT_CPU_THRESHOLD", "80"))
RAM_THRESHOLD = float(os.getenv("ALERT_RAM_THRESHOLD", "90"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))


# глобальный коллектор метрик
collector = ServerCollector(
    max_readings=60,
    cpu_threshold=CPU_THRESHOLD,
    ram_threshold=RAM_THRESHOLD,
)

# users who opted in for alerts
alert_users: set[int] = set()
if ADMIN_ID:
    alert_users.add(ADMIN_ID)


async def background_collector(bot: Bot):
    """Background task - collect metrics and send proactive alerts.
    Runs every CHECK_INTERVAL seconds."""
    logger.info("Background collector started, interval=%ds", CHECK_INTERVAL)
    while True:
        try:
            collector.collect()
            # проверяем пороги и шлем алерты
            alerts = collector.check_alerts()
            if alerts and alert_users:
                text = (
                    "⚠️ <b>Alert!</b>\n\n"
                    + "\n".join(f"• {a}" for a in alerts)
                )
                for uid in alert_users:
                    try:
                        await bot.send_message(uid, text, parse_mode="HTML")
                    except Exception as e:
                        logger.warning("Could not send alert to %s: %s", uid, e)
        except Exception as e:
            logger.error("Collector error: %s", e)

        await asyncio.sleep(CHECK_INTERVAL)


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Check .env file")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    # inject dependencies
    dp["collector"] = collector
    dp["alert_users"] = alert_users

    # middleware
    dp.message.middleware(AlertMiddleware(collector, alert_users))

    # register routers
    dp.include_router(cmd_handlers.router)
    dp.include_router(cb_handlers.router)

    # initial collection
    collector.collect()
    logger.info("Initial metrics collected")

    # запускаем фоновый сбор метрик
    asyncio.create_task(background_collector(bot))

    logger.info("Bot starting...")
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, "Server Watch бот запущен и работает.")
        except Exception:
            pass

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
