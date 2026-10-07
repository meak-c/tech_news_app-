from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import PRODUCTS
from .models import NewsItem, SourceError
from .summarizer import FALLBACK_SUMMARY

JST = ZoneInfo("Asia/Tokyo")
# 公開日が日付のみの記事で、初回取得が公開日からこの日数以内なら取得日(JST)を表示日にする。
# 超える場合は初回取り込みなどで取得日に意味がないため、公開日をそのまま使う。
MAX_DETECTION_LAG_DAYS = 3


def display_date(item: NewsItem) -> date | None:
    """画面に表示する日付(JST)を返す。

    リリースノートの日付はベンダー現地の日付なので、日本から見える日付とは1日ずれうる。
    公開日が日付のみ(UTC 0:00固定)の場合は、このアプリが初めて取得した日(JST)を使う。
    """
    published = item.published_at
    first_seen = item.first_seen_at.astimezone(JST).date()
    if published is None:
        return first_seen
    if published.astimezone(UTC).time() != time(0, 0):
        return published.astimezone(JST).date()
    published_date = published.astimezone(UTC).date()
    lag_days = (first_seen - published_date).days
    if 0 <= lag_days <= MAX_DETECTION_LAG_DAYS:
        return first_seen
    return published_date


def render_news_json(
    items: list[NewsItem],
    errors: list[SourceError],
    run_at: datetime,
    new_count: int,
) -> str:
    """Webフロントエンド(web/)が読み込む news.json の内容を生成する。

    取得元から外した製品(PRODUCTSにないもの)の記事はDBに残っていても出力しない。
    """
    items = [item for item in items if item.product in PRODUCTS]
    payload = {
        "generated_at": run_at.astimezone(JST).isoformat(),
        "new_count": new_count,
        "products": list(PRODUCTS),
        "errors": [error.model_dump() for error in errors],
        "items": [
            {
                "id": item.id,
                "date": display_date(item).isoformat(),
                "product": item.product,
                "title": item.title,
                "summary_ja": item.summary_ja or FALLBACK_SUMMARY,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "fetched_at": item.fetched_at.isoformat(),
                "source_name": item.source_name,
                "item_url": item.item_url,
                "is_new": item.is_new,
                "month": display_date(item).strftime("%Y-%m"),
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
