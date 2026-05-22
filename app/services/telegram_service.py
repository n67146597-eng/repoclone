from __future__ import annotations

import logging

from telegram import Bot

from app.keyboards.inline_buttons import reminder_action_keyboard
from app.models.reminder import Reminder
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, bot: Bot, reminder_service: ReminderService) -> None:
        self.bot = bot
        self.reminder_service = reminder_service

    async def send_reminder(self, reminder: Reminder) -> None:
        repeat_note = (
            "This notification repeats until you mark it done."
            if reminder.notify_every_hours is not None
            else "This notification is sent once."
        )
        message = (
            "Reminder due\n\n"
            f"{self.reminder_service.format_summary(reminder)}\n\n"
            f"{repeat_note}"
        )
        await self.bot.send_message(
            chat_id=reminder.chat_id,
            text=message,
            reply_markup=reminder_action_keyboard(reminder.public_id),
        )
