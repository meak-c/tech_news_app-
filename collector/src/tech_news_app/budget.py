"""Persist the shared Gemini request budget in the existing SQLite database."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from zoneinfo import ZoneInfo


class RequestBudget:
    def __init__(self, connection: sqlite3.Connection, max_requests_per_day: int) -> None:
        if max_requests_per_day < 0:
            raise ValueError("Gemini daily request budget must be non-negative")
        self.connection = connection
        self.max_requests_per_day = max_requests_per_day
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS gemini_request_usage "
            "(usage_date TEXT PRIMARY KEY, request_count INTEGER NOT NULL)"
        )
        self.connection.commit()

    def try_acquire(self, now: datetime | None = None) -> bool:
        """Reserve one attempt atomically; Gemini resets daily quotas at Pacific midnight."""
        if self.max_requests_per_day == 0:
            return False
        usage_date = (now or datetime.now(UTC)).astimezone(ZoneInfo("America/Los_Angeles"))
        with self.connection:
            row = self.connection.execute(
                "INSERT INTO gemini_request_usage (usage_date, request_count) VALUES (?, 1) "
                "ON CONFLICT(usage_date) DO UPDATE SET request_count = request_count + 1 "
                "WHERE request_count < ? RETURNING request_count",
                (usage_date.date().isoformat(), self.max_requests_per_day),
            ).fetchone()
        return row is not None
