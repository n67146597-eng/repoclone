from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.config import Settings
from app.services.reminder_service import ReminderService


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    settings: Settings = context.application.bot_data["settings"]
    if user.id not in settings.admin_user_ids:
        await message.reply_text("You are not allowed to use this command.")
        return

    service: ReminderService = context.application.bot_data["reminder_service"]
    stats = service.stats()
    await message.reply_text(
        "Bot stats\n"
        f"Total: {stats.get('total', 0)}\n"
        f"Active: {stats.get('active', 0)}\n"
        f"Done: {stats.get('done', 0)}\n"
        f"Deleted: {stats.get('deleted', 0)}"
    )


def admin_handlers() -> list[CommandHandler]:
    return [CommandHandler("admin", admin_command)]
