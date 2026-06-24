import json
from datetime import UTC, datetime

from tech_news_app.models import Importance, NewsItem
from tech_news_app.renderer import render_html, render_news_json, write_site


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
    assert '<select id="product-filter">' in html
    assert '<select id="month-filter">' in html
    assert '<select id="importance-filter">' in html
    assert '<input id="search-filter"' in html
    assert 'href="styles.css"' in html
    assert 'src="app.js"' in html


def test_html_does_not_inline_all_news_cards() -> None:
    html = render_html([make_news()], [], datetime(2026, 6, 23, tzinfo=UTC), 0)
    assert "Release title" not in html
    assert "https://example.com/item" not in html
    assert 'id="news-list"' in html


def test_news_json_contains_required_fields() -> None:
    payload = json.loads(render_news_json([make_news()], datetime(2026, 6, 23, tzinfo=UTC), 1))
    assert payload["new_count"] == 1
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


def test_write_site_creates_html_css_js_and_json(tmp_path) -> None:
    output = tmp_path / "public" / "index.html"
    write_site(output, [make_news()], [], datetime(2026, 6, 23, tzinfo=UTC), 0)
    assert output.exists()
    assert (tmp_path / "public" / "styles.css").exists()
    assert (tmp_path / "public" / "app.js").exists()
    assert (tmp_path / "public" / "news.json").exists()
