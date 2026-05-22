from __future__ import annotations

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from app.services.parser_service import ReminderParseError
from app.services.reminder_service import ReminderService


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    if user is None or chat is None or message is None:
        return

    raw_text = _command_payload(message.text or "")
    service = _service(context)

    try:
        reminder = service.create_from_command(user.id, chat.id, raw_text)
    except ReminderParseError as exc:
        await message.reply_text(
            f"{exc}\n\n"
            "Use: /remind <time> | <content> [--every Nh] [--repeat daily|weekly|monthly|Nh]"
        )
        return

    await message.reply_text(
        "Reminder created\n\n"
        f"{service.format_summary(reminder)}"
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    reminders = _service(context).list_active(user.id)
    if not reminders:
        await message.reply_text("No active reminders.")
        return

    service = _service(context)
    lines: list[str] = ["Active reminders"]
    for index, reminder in enumerate(reminders, start=1):
        lines.append(f"\n{index}. {service.format_summary(reminder)}")

    await message.reply_text("\n".join(lines[:80]))


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    reminder_id = _first_arg(context)
    if reminder_id is None:
        await message.reply_text("Use: /done <id>")
        return

    status, reminder = _service(context).complete(user.id, reminder_id)
    if status == "not_found" or reminder is None:
        await message.reply_text("Reminder not found.")
    elif status == "rescheduled":
        await message.reply_text(
            "Recurring reminder completed and rescheduled\n\n"
            f"{_service(context).format_summary(reminder)}"
        )
    else:
        await message.reply_text("Reminder completed.")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    reminder_id = _first_arg(context)
    if reminder_id is None:
        await message.reply_text("Use: /delete <id>")
        return

    deleted = _service(context).delete(user.id, reminder_id)
    await message.reply_text("Reminder deleted." if deleted else "Reminder not found.")


async def snooze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    reminder_id = _first_arg(context)
    if reminder_id is None:
        await message.reply_text("Use: /snooze <id> [hours]")
        return

    hours = _parse_hours(context.args[1] if len(context.args) > 1 else None, default=1)
    reminder = _service(context).snooze(user.id, reminder_id, hours)
    if reminder is None:
        await message.reply_text("Reminder not found.")
        return
    await message.reply_text(
        f"Reminder snoozed {hours}h\n\n"
        f"{_service(context).format_summary(reminder)}"
    )


async def reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or not query.data:
        return

    await query.answer()
    parts = query.data.split(":")
    action = parts[0]
    reminder_id = parts[1] if len(parts) > 1 else ""
    service = _service(context)

    if action == "done":
        status, reminder = service.complete(user.id, reminder_id)
        if status == "rescheduled" and reminder is not None:
            response = "Completed and rescheduled\n\n" + service.format_summary(reminder)
        elif status == "done":
            response = "Reminder completed."
        else:
            response = "Reminder not found."
        await _remove_keyboard(query)
        await query.message.reply_text(response) if query.message else None
        return

    if action == "delete":
        deleted = service.delete(user.id, reminder_id)
        await _remove_keyboard(query)
        if query.message:
            await query.message.reply_text("Reminder deleted." if deleted else "Reminder not found.")
        return

    if action == "snooze":
        hours = _parse_hours(parts[2] if len(parts) > 2 else None, default=1)
        reminder = service.snooze(user.id, reminder_id, hours)
        if query.message:
            if reminder is None:
                await query.message.reply_text("Reminder not found.")
            else:
                await query.message.reply_text(
                    f"Reminder snoozed {hours}h\n\n"
                    f"{service.format_summary(reminder)}"
                )


def reminder_handlers() -> list:
    return [
        CommandHandler("remind", remind_command),
        CommandHandler("list", list_command),
        CommandHandler("done", done_command),
        CommandHandler("delete", delete_command),
        CommandHandler("snooze", snooze_command),
        CallbackQueryHandler(reminder_callback, pattern=r"^(done|delete|snooze):"),
    ]


def _service(context: ContextTypes.DEFAULT_TYPE) -> ReminderService:
    return context.application.bot_data["reminder_service"]


def _command_payload(message_text: str) -> str:
    parts = message_text.split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


def _first_arg(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    if not context.args:
        return None
    return context.args[0].strip()


def _parse_hours(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return max(1, int(value.lower().removesuffix("h")))
    except ValueError:
        return default


async def _remove_keyboard(query) -> None:
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except TelegramError:
        pass
