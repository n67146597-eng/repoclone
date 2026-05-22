from __future__ import annotations

import logging
from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import Settings
from app.services.reminder_service import ReminderService
from app.services.telegram_service import TelegramService
from app.utils.datetime_helper import now_utc

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(
        self,
        reminder_service: ReminderService,
        telegram_service: TelegramService,
        settings: Settings,
    ) -> None:
        self.reminder_service = reminder_service
        self.telegram_service = telegram_service
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=timezone.utc)

    def start(self) -> None:
        self.scheduler.add_job(
            self.dispatch_due_reminders,
            trigger=IntervalTrigger(seconds=self.settings.scheduler_interval_seconds),
            id="dispatch_due_reminders",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            next_run_time=now_utc(),
        )
        self.scheduler.start()
        logger.info("Reminder scheduler started")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Reminder scheduler stopped")

    async def dispatch_due_reminders(self) -> None:
        reminders = self.reminder_service.due_reminders()
        if not reminders:
            return

        logger.info("Dispatching %s due reminder(s)", len(reminders))
        for reminder in reminders:
            try:
                await self.telegram_service.send_reminder(reminder)
                self.reminder_service.mark_notified(reminder)
            except Exception:
                logger.exception("Failed to send reminder %s", reminder.public_id)
