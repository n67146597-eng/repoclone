from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import Settings
from app.models.reminder import Reminder, STATUS_ACTIVE, STATUS_DELETED
from app.utils.datetime_helper import ensure_utc


class MongoDatabase:
    def __init__(self, settings: Settings) -> None:
        self.client: MongoClient = MongoClient(
            settings.mongodb_uri,
            tz_aware=True,
            tzinfo=timezone.utc,
        )
        self.database: Database = self.client[settings.mongodb_db]
        self.reminders: Collection = self.database["reminders"]

    def ensure_indexes(self) -> None:
        self.reminders.create_index(
            [("status", ASCENDING), ("next_notify_at", ASCENDING)],
            name="status_next_notify_at",
        )
        self.reminders.create_index(
            [("user_id", ASCENDING), ("status", ASCENDING), ("due_at", ASCENDING)],
            name="user_status_due_at",
        )
        self.reminders.create_index(
            [("created_at", ASCENDING)],
            name="created_at",
        )

    def close(self) -> None:
        self.client.close()


class ReminderRepository:
    def __init__(self, collection: Collection) -> None:
        self.collection = collection

    def create(self, reminder: Reminder) -> Reminder:
        result = self.collection.insert_one(reminder.to_document())
        reminder.id = str(result.inserted_id)
        return reminder

    def get_by_id(self, reminder_id: str) -> Reminder | None:
        object_id = _to_object_id(reminder_id)
        if object_id is None:
            return None
        document = self.collection.find_one({"_id": object_id})
        return Reminder.from_document(document) if document else None

    def get_user_reminder(self, user_id: int, reminder_id: str) -> Reminder | None:
        object_id = _to_object_id(reminder_id)
        if object_id is None:
            return None
        document = self.collection.find_one({"_id": object_id, "user_id": user_id})
        return Reminder.from_document(document) if document else None

    def list_active_for_user(self, user_id: int, limit: int = 50) -> list[Reminder]:
        cursor = (
            self.collection.find({"user_id": user_id, "status": STATUS_ACTIVE})
            .sort("due_at", ASCENDING)
            .limit(limit)
        )
        return [Reminder.from_document(document) for document in cursor]

    def list_due(self, now: datetime, limit: int = 100) -> list[Reminder]:
        cursor = (
            self.collection.find(
                {
                    "status": STATUS_ACTIVE,
                    "next_notify_at": {"$lte": ensure_utc(now)},
                }
            )
            .sort("next_notify_at", ASCENDING)
            .limit(limit)
        )
        return [Reminder.from_document(document) for document in cursor]

    def update_fields(
        self,
        reminder_id: str,
        fields: dict[str, Any],
        increment: dict[str, int] | None = None,
    ) -> Reminder | None:
        object_id = _to_object_id(reminder_id)
        if object_id is None:
            return None

        update: dict[str, Any] = {"$set": fields}
        if increment:
            update["$inc"] = increment
        self.collection.update_one({"_id": object_id}, update)
        return self.get_by_id(reminder_id)

    def soft_delete_for_user(self, user_id: int, reminder_id: str, deleted_at: datetime) -> bool:
        object_id = _to_object_id(reminder_id)
        if object_id is None:
            return False

        result = self.collection.update_one(
            {"_id": object_id, "user_id": user_id, "status": STATUS_ACTIVE},
            {
                "$set": {
                    "status": STATUS_DELETED,
                    "updated_at": ensure_utc(deleted_at),
                    "completed_at": ensure_utc(deleted_at),
                }
            },
        )
        return result.modified_count > 0

    def stats(self) -> dict[str, int]:
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        stats = {item["_id"]: item["count"] for item in self.collection.aggregate(pipeline)}
        stats["total"] = self.collection.count_documents({})
        return stats


def _to_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class InMemoryReminderRepository:
    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def create(self, reminder: Reminder) -> Reminder:
        with self._lock:
            reminder.id = str(ObjectId())
            document = reminder.to_document()
            document["_id"] = ObjectId(reminder.id)
            self._documents[reminder.id] = document
            return Reminder.from_document(document)

    def get_by_id(self, reminder_id: str) -> Reminder | None:
        with self._lock:
            document = self._documents.get(reminder_id)
            return Reminder.from_document(document.copy()) if document else None

    def get_user_reminder(self, user_id: int, reminder_id: str) -> Reminder | None:
        reminder = self.get_by_id(reminder_id)
        if reminder is None or reminder.user_id != user_id:
            return None
        return reminder

    def list_active_for_user(self, user_id: int, limit: int = 50) -> list[Reminder]:
        with self._lock:
            reminders = [
                Reminder.from_document(document.copy())
                for document in self._documents.values()
                if document["user_id"] == user_id and document["status"] == STATUS_ACTIVE
            ]
        return sorted(reminders, key=lambda reminder: reminder.due_at)[:limit]

    def list_due(self, now: datetime, limit: int = 100) -> list[Reminder]:
        now = ensure_utc(now)
        with self._lock:
            reminders = [
                Reminder.from_document(document.copy())
                for document in self._documents.values()
                if document["status"] == STATUS_ACTIVE and document["next_notify_at"] <= now
            ]
        return sorted(reminders, key=lambda reminder: reminder.next_notify_at or reminder.due_at)[:limit]

    def update_fields(
        self,
        reminder_id: str,
        fields: dict[str, Any],
        increment: dict[str, int] | None = None,
    ) -> Reminder | None:
        with self._lock:
            document = self._documents.get(reminder_id)
            if document is None:
                return None
            document.update(fields)
            if increment:
                for key, value in increment.items():
                    document[key] = int(document.get(key, 0)) + value
            return Reminder.from_document(document.copy())

    def soft_delete_for_user(self, user_id: int, reminder_id: str, deleted_at: datetime) -> bool:
        with self._lock:
            document = self._documents.get(reminder_id)
            if (
                document is None
                or document["user_id"] != user_id
                or document["status"] != STATUS_ACTIVE
            ):
                return False

            document.update(
                {
                    "status": STATUS_DELETED,
                    "updated_at": ensure_utc(deleted_at),
                    "completed_at": ensure_utc(deleted_at),
                }
            )
            return True

    def stats(self) -> dict[str, int]:
        with self._lock:
            stats: dict[str, int] = {"total": len(self._documents)}
            for document in self._documents.values():
                status = str(document["status"])
                stats[status] = stats.get(status, 0) + 1
            return stats
