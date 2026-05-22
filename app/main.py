
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application

from app.config import load_settings
from app.database import InMemoryReminderRepository, MongoDatabase, ReminderRepository
from app.handlers.admin import admin_handlers
from app.handlers.help import help_handlers
from app.handlers.reminder import reminder_handlers
from app.handlers.start import start_handlers
from app.scheduler import ReminderScheduler
from app.services.reminder_service import ReminderService
from app.services.telegram_service import TelegramService
from app.utils.logger import configure_logging

logger = logging.getLogger(__name__)


def build_application() -> Application:
    settings = load_settings()
    configure_logging(settings.log_level)

    database = None
    if settings.storage_backend == "memory":
        repository = InMemoryReminderRepository()
        logger.warning("Using in-memory storage. Reminders will be lost on restart.")
    else:
        database = MongoDatabase(settings)
        database.ensure_indexes()
        repository = ReminderRepository(database.reminders)
    reminder_service = ReminderService(repository, settings)

    async def post_init(application: Application) -> None:
        telegram_service = TelegramService(application.bot, reminder_service)
        scheduler = ReminderScheduler(reminder_service, telegram_service, settings)
        application.bot_data["scheduler"] = scheduler
        scheduler.start()

    async def post_shutdown(application: Application) -> None:
        scheduler = application.bot_data.get("scheduler")
        if scheduler is not None:
            scheduler.shutdown()
        if database is not None:
            database.close()

    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["reminder_service"] = reminder_service
    if database is not None:
        application.bot_data["database"] = database

    for handler in (
        start_handlers()
        + help_handlers()
        + reminder_handlers()
        + admin_handlers()
    ):
        application.add_handler(handler)

    return application


def main() -> None:
    application = build_application()
    logger.info("Starting Telegram reminder bot")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
