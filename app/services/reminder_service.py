from __future__ import annotations

from datetime import timedelta

from app.config import Settings
from app.database import ReminderRepository
from app.models.reminder import Reminder, STATUS_ACTIVE, STATUS_DONE
from app.services.parser_service import parse_reminder_command
from app.utils.datetime_helper import format_local, next_recurrence_after, now_utc


class ReminderService:
    def __init__(self, repository: ReminderRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def create_from_command(self, user_id: int, chat_id: int, raw_text: str) -> Reminder:
        parsed = parse_reminder_command(raw_text, self.settings.timezone)
        reminder = Reminder(
            user_id=user_id,
            chat_id=chat_id,
            text=parsed.text,
            due_at=parsed.due_at_utc,
            timezone=parsed.timezone,
            recurrence=parsed.recurrence,
            recurrence_interval=parsed.recurrence_interval,
            notify_every_hours=parsed.notify_every_hours,
        )
        return self.repository.create(reminder)

    def list_active(self, user_id: int) -> list[Reminder]:
        return self.repository.list_active_for_user(user_id)

    def due_reminders(self, limit: int = 100) -> list[Reminder]:
        return self.repository.list_due(now_utc(), limit=limit)

    def mark_notified(self, reminder: Reminder) -> Reminder | None:
        now = now_utc()
        if reminder.notify_every_hours is None:
            if reminder.recurrence != "none":
                next_due = next_recurrence_after(
                    reminder.due_at,
                    reminder.recurrence,
                    reminder.recurrence_interval,
                    now,
                )
                return self.repository.update_fields(
                    reminder.public_id,
                    {
                        "due_at": next_due,
                        "next_notify_at": next_due,
                        "last_notified_at": now,
                        "fired_count": 0,
                        "updated_at": now,
                        "completed_at": None,
                        "status": STATUS_ACTIVE,
                    },
                )

            return self.repository.update_fields(
                reminder.public_id,
                {
                    "status": STATUS_DONE,
                    "next_notify_at": None,
                    "last_notified_at": now,
                    "updated_at": now,
                    "completed_at": now,
                },
                increment={"fired_count": 1},
            )

        return self.repository.update_fields(
            reminder.public_id,
            {
                "last_notified_at": now,
                "next_notify_at": now + timedelta(hours=reminder.notify_every_hours),
                "updated_at": now,
            },
            increment={"fired_count": 1},
        )

    def complete(self, user_id: int, reminder_id: str) -> tuple[str, Reminder | None]:
        reminder = self.repository.get_user_reminder(user_id, reminder_id)
        if reminder is None or reminder.status != STATUS_ACTIVE:
            return "not_found", None

        now = now_utc()
        if reminder.recurrence != "none":
            next_due = next_recurrence_after(
                reminder.due_at,
                reminder.recurrence,
                reminder.recurrence_interval,
                now,
            )
            updated = self.repository.update_fields(
                reminder.public_id,
                {
                    "due_at": next_due,
                    "next_notify_at": next_due,
                    "last_notified_at": None,
                    "fired_count": 0,
                    "updated_at": now,
                    "completed_at": None,
                    "status": STATUS_ACTIVE,
                },
            )
            return "rescheduled", updated

        updated = self.repository.update_fields(
            reminder.public_id,
            {
                "status": STATUS_DONE,
                "updated_at": now,
                "completed_at": now,
            },
        )
        return "done", updated

    def snooze(self, user_id: int, reminder_id: str, hours: int) -> Reminder | None:
        if hours < 1:
            hours = 1

        reminder = self.repository.get_user_reminder(user_id, reminder_id)
        if reminder is None or reminder.status != STATUS_ACTIVE:
            return None

        now = now_utc()
        snoozed_until = now + timedelta(hours=hours)
        return self.repository.update_fields(
            reminder.public_id,
            {
                "due_at": snoozed_until,
                "next_notify_at": snoozed_until,
                "last_notified_at": None,
                "updated_at": now,
            },
        )

    def delete(self, user_id: int, reminder_id: str) -> bool:
        return self.repository.soft_delete_for_user(user_id, reminder_id, now_utc())

    def stats(self) -> dict[str, int]:
        return self.repository.stats()

    def format_summary(self, reminder: Reminder) -> str:
        due_at = format_local(reminder.due_at, reminder.timezone)
        recurrence = reminder.recurrence
        if recurrence == "hourly" and reminder.recurrence_interval > 1:
            recurrence = f"every {reminder.recurrence_interval}h"
        notify_text = (
            f"every {reminder.notify_every_hours}h"
            if reminder.notify_every_hours is not None
            else "once"
        )
        return (
            f"{reminder.text}\n"
            f"ID: {reminder.public_id}\n"
            f"Due: {due_at} ({reminder.timezone})\n"
            f"Repeat: {recurrence}\n"
            f"Notify: {notify_text}"
        )
