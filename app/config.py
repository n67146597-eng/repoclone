from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    mongodb_uri: str
    mongodb_db: str
    storage_backend: str
    timezone: str
    admin_user_ids: frozenset[int]
    scheduler_interval_seconds: int
    log_level: str


def load_settings() -> Settings:
    load_dotenv()

    bot_token = _required("BOT_TOKEN")
    storage_backend = os.getenv("STORAGE_BACKEND", "mongo").strip().lower()
    if storage_backend not in {"mongo", "memory"}:
        raise RuntimeError("STORAGE_BACKEND must be either 'mongo' or 'memory'")

    mongodb_uri = os.getenv("MONGODB_URI", "").strip()
    if storage_backend == "mongo" and not mongodb_uri:
        raise RuntimeError("Missing required environment variable: MONGODB_URI")

    mongodb_db = os.getenv("MONGODB_DB", "telegram_reminder_bot").strip()
    timezone_name = os.getenv("TIMEZONE", "Asia/Bangkok").strip()

    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Invalid TIMEZONE: {timezone_name}") from exc

    return Settings(
        bot_token=bot_token,
        mongodb_uri=mongodb_uri,
        mongodb_db=mongodb_db,
        storage_backend=storage_backend,
        timezone=timezone_name,
        admin_user_ids=_parse_admin_ids(os.getenv("ADMIN_USER_IDS", "")),
        scheduler_interval_seconds=_parse_int(
            "SCHEDULER_INTERVAL_SECONDS",
            default=30,
            minimum=5,
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_admin_ids(raw: str) -> frozenset[int]:
    if not raw.strip():
        return frozenset()

    admin_ids: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            admin_ids.add(int(item))
        except ValueError as exc:
            raise RuntimeError(f"Invalid ADMIN_USER_IDS item: {item}") from exc
    return frozenset(admin_ids)


def _parse_int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}")
    return value
