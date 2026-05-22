from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


HELP_TEXT = """Telegram Reminder Bot

Commands:
/remind <time> | <content> [--every Nh] [--repeat daily|weekly|monthly|hourly|Nh]
/list
/done <id>
/delete <id>
/snooze <id> [hours]
/help

Examples:
/remind 2026-05-23 09:00 | pay electricity bill --every 1h
/remind mai 07:00 | drink medicine --repeat daily
/remind sau 2h | check deployment --every 3h

Without --every, the bot sends one notification only.

Time formats:
YYYY-MM-DD HH:MM, DD/MM/YYYY HH:MM, HH:MM, today HH:MM, tomorrow HH:MM, hom nay HH:MM, mai HH:MM, sau 30m, sau 2h, sau 1d
"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(HELP_TEXT)


def help_handlers() -> list[CommandHandler]:
    return [CommandHandler("help", help_command)]
