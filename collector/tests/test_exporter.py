import json
from datetime import UTC, datetime

from tech_news_app.config import PRODUCTS
from tech_news_app.exporter import render_news_json, write_news_json
from tech_news_app.models import Importance, NewsItem, SourceError


def make_news() -> NewsItem:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    return NewsItem(
        id=1,
        product="ChatGPT",
        source_name="ChatGPT Release Notes",
        source_url="https://example.com/source",
        item_url="https://example.com/item",
        title="Release title",
        published_at=now,
        fetched_at=now,
        first_seen_at=now,
        last_seen_at=now,
        content_hash="abc",
        summary_ja="・何が変わったか: テスト",
        raw_text="test",
        importance=Importance.MEDIUM,
        created_at=now,
        updated_at=now,
    )


def test_news_json_contains_required_fields() -> None:
    errors = [SourceError(source_name="ChatGPT Release Notes", message="403")]
    payload = json.loads(
        render_news_json([make_news()], errors, datetime(2026, 6, 23, tzinfo=UTC), 1)
    )
    assert payload["new_count"] == 1
    assert payload["products"] == list(PRODUCTS)
    assert payload["errors"] == [{"source_name": "ChatGPT Release Notes", "message": "403"}]
    item = payload["items"][0]
    for key in {
        "product",
        "title",
        "summary_ja",
        "published_at",
        "fetched_at",
        "source_name",
        "item_url",
        "importance",
        "is_new",
        "month",
    }:
        assert key in item
    assert item["month"] == "2026-06"


def test_write_news_json_creates_parent_dirs(tmp_path) -> None:
    output = tmp_path / "web" / "public" / "news.json"
    write_news_json(output, [make_news()], [], datetime(2026, 6, 23, tzinfo=UTC), 0)
    assert json.loads(output.read_text(encoding="utf-8"))["items"][0]["title"] == "Release title"
