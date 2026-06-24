from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .models import FetchedItem, NewsItem, RunLog
from .parser import classify_importance, content_hash


def utc_now() -> datetime:
    return datetime.now(UTC)


class NewsStorage:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> NewsStorage:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                item_url TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT,
                fetched_at TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                summary_ja TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                importance TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_news_product_published
                ON news(product, published_at DESC);
            CREATE INDEX IF NOT EXISTS idx_news_item_url ON news(item_url);
            CREATE INDEX IF NOT EXISTS idx_news_hash ON news(content_hash);
            CREATE TABLE IF NOT EXISTS run_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL,
                status TEXT NOT NULL,
                new_item_count INTEGER NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def save_item(self, item: FetchedItem, summary_ja: str) -> tuple[NewsItem, bool]:
        now = utc_now()
        digest = content_hash(item.title, item.raw_text)
        published = item.published_at.isoformat() if item.published_at else None
        existing = self.connection.execute(
            """
            SELECT * FROM news
            WHERE item_url = ?
               OR content_hash = ?
               OR (
                    product = ? AND lower(title) = lower(?)
                    AND COALESCE(published_at, '') = COALESCE(?, '')
               )
            ORDER BY id
            LIMIT 1
            """,
            (item.item_url, digest, item.product, item.title, published),
        ).fetchone()

        if existing:
            self.connection.execute(
                """
                UPDATE news
                SET last_seen_at = ?, fetched_at = ?, raw_text = ?, summary_ja = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    now.isoformat(),
                    now.isoformat(),
                    item.raw_text,
                    summary_ja,
                    now.isoformat(),
                    existing["id"],
                ),
            )
            self.connection.commit()
            row = self.connection.execute(
                "SELECT * FROM news WHERE id = ?", (existing["id"],)
            ).fetchone()
            return self._row_to_item(row, is_new=False), False

        cursor = self.connection.execute(
            """
            INSERT INTO news (
                product, source_name, source_url, item_url, title, published_at,
                fetched_at, first_seen_at, last_seen_at, content_hash, summary_ja,
                raw_text, importance, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.product,
                item.source_name,
                item.source_url,
                item.item_url,
                item.title,
                published,
                now.isoformat(),
                now.isoformat(),
                now.isoformat(),
                digest,
                summary_ja,
                item.raw_text,
                classify_importance(item.title, item.raw_text).value,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        self.connection.commit()
        row = self.connection.execute(
            "SELECT * FROM news WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return self._row_to_item(row, is_new=True), True

    def find_existing(self, items: Iterable[FetchedItem]) -> dict[str, NewsItem]:
        result: dict[str, NewsItem] = {}
        for item in items:
            row = self.connection.execute(
                "SELECT * FROM news WHERE item_url = ? LIMIT 1", (item.item_url,)
            ).fetchone()
            if row:
                result[item.item_url] = self._row_to_item(row)
        return result

    def latest_news(self, per_product: int = 20) -> list[NewsItem]:
        rows = self.connection.execute(
            """
            SELECT * FROM (
                SELECT news.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY product
                           ORDER BY COALESCE(published_at, first_seen_at) DESC, id DESC
                       ) AS product_rank
                FROM news
            )
            WHERE product_rank <= ?
            ORDER BY product, COALESCE(published_at, first_seen_at) DESC, id DESC
            """,
            (per_product,),
        ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def all_news(self) -> list[NewsItem]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM news
            ORDER BY COALESCE(published_at, first_seen_at) DESC, id DESC
            """
        ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def add_run_log(self, log: RunLog) -> None:
        self.connection.execute(
            """
            INSERT INTO run_logs (run_at, status, new_item_count, error_message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                log.run_at.isoformat(),
                log.status,
                log.new_item_count,
                log.error_message,
                log.created_at.isoformat(),
            ),
        )
        self.connection.commit()

    @staticmethod
    def _row_to_item(row: sqlite3.Row, is_new: bool = False) -> NewsItem:
        values = dict(row)
        values.pop("product_rank", None)
        values["is_new"] = is_new
        return NewsItem.model_validate(values)
