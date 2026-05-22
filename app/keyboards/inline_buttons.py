from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def reminder_action_keyboard(reminder_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Done", callback_data=f"done:{reminder_id}"),
                InlineKeyboardButton("+1h", callback_data=f"snooze:{reminder_id}:1"),
                InlineKeyboardButton("+3h", callback_data=f"snooze:{reminder_id}:3"),
            ],
            [InlineKeyboardButton("Delete", callback_data=f"delete:{reminder_id}")],
        ]
    )
