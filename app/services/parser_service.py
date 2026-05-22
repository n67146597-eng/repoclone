from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


class ReminderParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedReminder:
    due_at_utc: datetime
    text: str
    recurrence: str
    recurrence_interval: int
    notify_every_hours: int | None
    timezone: str


def parse_reminder_command(raw_text: str, default_timezone: str) -> ParsedReminder:
    raw_text = raw_text.strip()
    if not raw_text:
        raise ReminderParseError("Missing reminder details.")

    timezone_name, raw_text = _extract_timezone(raw_text, default_timezone)
    notify_every_hours, raw_text = _extract_notify_every(raw_text)
    recurrence, recurrence_interval, raw_text = _extract_recurrence(raw_text)

    time_text, reminder_text = _split_payload(raw_text)
    due_at_local = parse_datetime_text(time_text, timezone_name)
    now_local = datetime.now(ZoneInfo(timezone_name))

    if due_at_local <= now_local:
        raise ReminderParseError("Reminder time must be in the future.")

    return ParsedReminder(
        due_at_utc=due_at_local.astimezone(timezone.utc),
        text=reminder_text,
        recurrence=recurrence,
        recurrence_interval=recurrence_interval,
        notify_every_hours=notify_every_hours,
        timezone=timezone_name,
    )


def parse_datetime_text(time_text: str, timezone_name: str) -> datetime:
    value = time_text.strip()
    if not value:
        raise ReminderParseError("Missing reminder time.")

    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    normalized = _normalize(value)

    relative = _parse_relative(normalized)
    if relative is not None:
        return now + relative

    for prefix, days in (
        ("tomorrow ", 1),
        ("ngay mai ", 1),
        ("mai ", 1),
        ("today ", 0),
        ("hom nay ", 0),
    ):
        if normalized.startswith(prefix):
            parsed_time = _parse_time_of_day(normalized.removeprefix(prefix).strip())
            if parsed_time is None:
                raise ReminderParseError("Invalid time of day.")
            return datetime.combine(now.date() + timedelta(days=days), parsed_time, tzinfo=tz)

    parsed_time = _parse_time_of_day(normalized)
    if parsed_time is not None:
        due_at = datetime.combine(now.date(), parsed_time, tzinfo=tz)
        if due_at <= now:
            due_at += timedelta(days=1)
        return due_at

    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M",
    ):
        try:
            parsed = datetime.strptime(normalized, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=tz)

    raise ReminderParseError("Unsupported time format.")


def _extract_timezone(raw_text: str, default_timezone: str) -> tuple[str, str]:
    match = re.search(r"\s--tz\s+([A-Za-z0-9_./+-]+)", raw_text)
    if not match:
        return default_timezone, raw_text
    timezone_name = match.group(1)
    try:
        ZoneInfo(timezone_name)
    except Exception as exc:
        raise ReminderParseError(f"Invalid timezone: {timezone_name}") from exc
    return timezone_name, (raw_text[: match.start()] + raw_text[match.end() :]).strip()


def _extract_notify_every(raw_text: str) -> tuple[int | None, str]:
    match = re.search(
        r"\s--(?:every|notify-every|nhac-lai)\s+(\d+)\s*(?:h|hour|hours|gio)?",
        raw_text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, raw_text
    hours = int(match.group(1))
    if hours < 1:
        raise ReminderParseError("Notify interval must be at least 1 hour.")
    return hours, (raw_text[: match.start()] + raw_text[match.end() :]).strip()


def _extract_recurrence(raw_text: str) -> tuple[str, int, str]:
    match = re.search(r"\s--repeat\s+([A-Za-z0-9_-]+)", raw_text, flags=re.IGNORECASE)
    if not match:
        return "none", 1, raw_text

    value = _normalize(match.group(1)).replace("_", "-")
    recurrence, interval = _parse_recurrence_value(value)
    return recurrence, interval, (raw_text[: match.start()] + raw_text[match.end() :]).strip()


def _parse_recurrence_value(value: str) -> tuple[str, int]:
    hourly_interval = re.fullmatch(r"(\d+)h", value)
    if hourly_interval:
        return "hourly", int(hourly_interval.group(1))

    mapping = {
        "none": "none",
        "no": "none",
        "daily": "daily",
        "day": "daily",
        "hang-ngay": "daily",
        "weekly": "weekly",
        "week": "weekly",
        "hang-tuan": "weekly",
        "monthly": "monthly",
        "month": "monthly",
        "hang-thang": "monthly",
        "hourly": "hourly",
        "hour": "hourly",
    }
    recurrence = mapping.get(value)
    if recurrence is None:
        raise ReminderParseError("Unsupported repeat value.")
    return recurrence, 1


def _split_payload(raw_text: str) -> tuple[str, str]:
    if "|" not in raw_text:
        raise ReminderParseError("Use: /remind <time> | <content>")

    time_text, reminder_text = raw_text.split("|", 1)
    time_text = time_text.strip()
    reminder_text = reminder_text.strip()
    if not time_text:
        raise ReminderParseError("Missing reminder time.")
    if not reminder_text:
        raise ReminderParseError("Missing reminder content.")
    return time_text, reminder_text


def _parse_relative(normalized: str) -> timedelta | None:
    match = re.fullmatch(
        r"(?:in|sau)\s+(\d+)\s*(m|min|minute|minutes|phut|h|hour|hours|gio|d|day|days|ngay)",
        normalized,
    )
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)
    if amount < 1:
        raise ReminderParseError("Relative time must be positive.")
    if unit in {"m", "min", "minute", "minutes", "phut"}:
        return timedelta(minutes=amount)
    if unit in {"h", "hour", "hours", "gio"}:
        return timedelta(hours=amount)
    return timedelta(days=amount)


def _parse_time_of_day(normalized: str):
    colon_match = re.fullmatch(r"(\d{1,2}):(\d{2})", normalized)
    hour_match = re.fullmatch(r"(\d{1,2})h(?:(\d{1,2}))?", normalized)
    match = colon_match or hour_match
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if hour > 23 or minute > 59:
        raise ReminderParseError("Invalid time of day.")
    return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_marks).strip()
