from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_local(value: datetime, timezone_name: str) -> datetime:
    return ensure_utc(value).astimezone(ZoneInfo(timezone_name))


def format_local(value: datetime, timezone_name: str) -> str:
    return to_local(value, timezone_name).strftime("%Y-%m-%d %H:%M")


def next_recurrence_after(
    current_due_at: datetime,
    recurrence: str,
    interval: int,
    after: datetime,
) -> datetime | None:
    if recurrence == "none":
        return None

    interval = max(1, interval)
    next_due = add_recurrence(current_due_at, recurrence, interval)
    after = ensure_utc(after)

    guard = 0
    while next_due <= after:
        next_due = add_recurrence(next_due, recurrence, interval)
        guard += 1
        if guard > 1000:
            raise RuntimeError("Could not advance recurring reminder")
    return next_due


def add_recurrence(value: datetime, recurrence: str, interval: int) -> datetime:
    value = ensure_utc(value)
    interval = max(1, interval)

    if recurrence == "hourly":
        return value + timedelta(hours=interval)
    if recurrence == "daily":
        return value + timedelta(days=interval)
    if recurrence == "weekly":
        return value + timedelta(weeks=interval)
    if recurrence == "monthly":
        return _add_months(value, interval)
    raise ValueError(f"Unsupported recurrence: {recurrence}")


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
