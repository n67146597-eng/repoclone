from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.handlers.help import HELP_TEXT


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Bot is ready.\n\n"
            "Create a reminder with:\n"
            "/remind <time> | <content>\n\n"
            f"{HELP_TEXT}"
        )


def start_handlers() -> list[CommandHandler]:
    return [CommandHandler("start", start_command)]
