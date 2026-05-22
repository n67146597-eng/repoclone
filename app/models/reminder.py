from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.utils.datetime_helper import ensure_utc, now_utc


STATUS_ACTIVE = "active"
STATUS_DONE = "done"
STATUS_DELETED = "deleted"
RECURRENCES = {"none", "hourly", "daily", "weekly", "monthly"}


@dataclass
class Reminder:
    user_id: int
    chat_id: int
    text: str
    due_at: datetime
    timezone: str
    id: str | None = None
    status: str = STATUS_ACTIVE
    recurrence: str = "none"
    recurrence_interval: int = 1
    notify_every_hours: int | None = None
    next_notify_at: datetime | None = None
    last_notified_at: datetime | None = None
    fired_count: int = 0
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.due_at = ensure_utc(self.due_at)
        self.created_at = ensure_utc(self.created_at)
        self.updated_at = ensure_utc(self.updated_at)
        if self.next_notify_at is None:
            self.next_notify_at = self.due_at
        else:
            self.next_notify_at = ensure_utc(self.next_notify_at)
        if self.last_notified_at is not None:
            self.last_notified_at = ensure_utc(self.last_notified_at)
        if self.completed_at is not None:
            self.completed_at = ensure_utc(self.completed_at)

        if self.recurrence not in RECURRENCES:
            raise ValueError(f"Unsupported recurrence: {self.recurrence}")
        self.recurrence_interval = max(1, int(self.recurrence_interval))
        if self.notify_every_hours is not None:
            self.notify_every_hours = max(1, int(self.notify_every_hours))

    @property
    def public_id(self) -> str:
        return self.id or ""

    def to_document(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "text": self.text,
            "due_at": self.due_at,
            "timezone": self.timezone,
            "status": self.status,
            "recurrence": self.recurrence,
            "recurrence_interval": self.recurrence_interval,
            "notify_every_hours": self.notify_every_hours,
            "next_notify_at": self.next_notify_at,
            "last_notified_at": self.last_notified_at,
            "fired_count": self.fired_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "Reminder":
        return cls(
            id=str(document["_id"]),
            user_id=int(document["user_id"]),
            chat_id=int(document["chat_id"]),
            text=str(document["text"]),
            due_at=document["due_at"],
            timezone=str(document.get("timezone", "Asia/Bangkok")),
            status=str(document.get("status", STATUS_ACTIVE)),
            recurrence=str(document.get("recurrence", "none")),
            recurrence_interval=int(document.get("recurrence_interval", 1)),
            notify_every_hours=(
                int(document["notify_every_hours"])
                if document.get("notify_every_hours") is not None
                else None
            ),
            next_notify_at=document.get("next_notify_at"),
            last_notified_at=document.get("last_notified_at"),
            fired_count=int(document.get("fired_count", 0)),
            created_at=document.get("created_at", now_utc()),
            updated_at=document.get("updated_at", now_utc()),
            completed_at=document.get("completed_at"),
        )
