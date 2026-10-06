from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Importance(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NewsItem(BaseModel):
    id: int | None = None
    product: str
    source_name: str
    source_url: str
    item_url: str
    title: str
    published_at: datetime | None = None
    fetched_at: datetime
    first_seen_at: datetime
    last_seen_at: datetime
    content_hash: str
    summary_ja: str = ""
    raw_text: str = ""
    importance: Importance = Importance.MEDIUM
    created_at: datetime
    updated_at: datetime
    is_new: bool = False


class FetchedItem(BaseModel):
    product: str
    source_name: str
    source_url: str
    item_url: str
    title: str
    published_at: datetime | None = None
    raw_text: str = ""


class SourceError(BaseModel):
    source_name: str
    message: str


class RunLog(BaseModel):
    run_at: datetime
    status: str
    new_item_count: int = 0
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
