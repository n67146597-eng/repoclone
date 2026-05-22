from __future__ import annotations

from datetime import timezone

from app.services.parser_service import parse_datetime_text, parse_reminder_command


def test_parse_absolute_reminder() -> None:
    parsed = parse_reminder_command(
        "2099-01-02 09:30 | pay bill --repeat daily --every 2h",
        "Asia/Bangkok",
    )

    assert parsed.text == "pay bill"
    assert parsed.recurrence == "daily"
    assert parsed.notify_every_hours == 2
    assert parsed.due_at_utc.tzinfo == timezone.utc


def test_parse_vietnamese_relative_hours() -> None:
    parsed = parse_reminder_command("sau 2h | check server --every 3h", "Asia/Bangkok")

    assert parsed.text == "check server"
    assert parsed.recurrence == "none"
    assert parsed.notify_every_hours == 3


def test_parse_without_every_notifies_once() -> None:
    parsed = parse_reminder_command("2099-01-02 09:30 | pay bill", "Asia/Bangkok")

    assert parsed.notify_every_hours is None


def test_parse_time_only_rolls_forward() -> None:
    due_at = parse_datetime_text("23:59", "Asia/Bangkok")

    assert due_at.hour == 23
    assert due_at.minute == 59
