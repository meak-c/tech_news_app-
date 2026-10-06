from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import PRODUCTS
from .models import NewsItem, SourceError
from .summarizer import FALLBACK_SUMMARY

JST = ZoneInfo("Asia/Tokyo")


def _month(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    return value.astimezone(JST).strftime("%Y-%m")


def render_news_json(
    items: list[NewsItem],
    errors: list[SourceError],
    run_at: datetime,
    new_count: int,
) -> str:
    """Webフロントエンド(web/)が読み込む news.json の内容を生成する。"""
    payload = {
        "generated_at": run_at.astimezone(JST).isoformat(),
        "new_count": new_count,
        "products": list(PRODUCTS),
        "errors": [error.model_dump() for error in errors],
        "items": [
            {
                "id": item.id,
                "product": item.product,
                "title": item.title,
                "summary_ja": item.summary_ja or FALLBACK_SUMMARY,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "fetched_at": item.fetched_at.isoformat(),
                "source_name": item.source_name,
                "item_url": item.item_url,
                "importance": item.importance.value,
                "is_new": item.is_new,
                "month": _month(item.published_at),
            }
            for item in items
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_news_json(
    output_path: Path,
    items: list[NewsItem],
    errors: list[SourceError],
    run_at: datetime,
    new_count: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_news_json(items, errors, run_at, new_count) + "\n", encoding="utf-8"
    )
