from datetime import UTC, datetime

from tech_news_app.models import Importance, NewsItem
from tech_news_app.renderer import render_html


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


def test_no_new_items_message_and_sections_and_link() -> None:
    html = render_html([make_news()], [], datetime(2026, 6, 23, tzinfo=UTC), 0)
    assert "本日の新ニュースはありませんでした。" in html
    assert "<h2>ChatGPT</h2>" in html
    assert "<h2>Claude</h2>" in html
    assert "<h2>Claude Code</h2>" in html
    assert "<h2>Databricks</h2>" in html
    assert 'href="https://example.com/item"' in html
