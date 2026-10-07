import json
from datetime import UTC, date, datetime

from tech_news_app.config import PRODUCTS
from tech_news_app.exporter import (
    display_date,
    display_product,
    render_news_json,
    write_news_json,
)
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
        "is_new",
        "month",
    }:
        assert key in item
    assert item["month"] == "2026-06"


def test_write_news_json_creates_parent_dirs(tmp_path) -> None:
    output = tmp_path / "web" / "public" / "news.json"
    write_news_json(output, [make_news()], [], datetime(2026, 6, 23, tzinfo=UTC), 0)
    assert json.loads(output.read_text(encoding="utf-8"))["items"][0]["title"] == "Release title"


def news_at(published: datetime | None, first_seen: datetime) -> NewsItem:
    return make_news().model_copy(update={"published_at": published, "first_seen_at": first_seen})


def test_display_date_uses_first_seen_jst_for_date_only_release() -> None:
    # 米国の10/6リリース。日本では10/7 03:07 の定期実行で初めて見える。
    item = news_at(
        datetime(2026, 10, 6, tzinfo=UTC), datetime(2026, 10, 6, 18, 7, tzinfo=UTC)
    )
    assert display_date(item) == date(2026, 10, 7)


def test_display_date_keeps_published_date_for_initial_import() -> None:
    item = news_at(
        datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 10, 6, 18, 7, tzinfo=UTC)
    )
    assert display_date(item) == date(2026, 7, 1)


def test_display_date_converts_precise_timestamp_to_jst() -> None:
    item = news_at(
        datetime(2026, 10, 6, 20, 0, tzinfo=UTC), datetime(2026, 10, 6, 21, 0, tzinfo=UTC)
    )
    assert display_date(item) == date(2026, 10, 7)


def test_display_date_falls_back_to_first_seen_without_published_date() -> None:
    item = news_at(None, datetime(2026, 10, 6, 18, 7, tzinfo=UTC))
    assert display_date(item) == date(2026, 10, 7)


def test_news_json_exposes_display_date_and_month() -> None:
    item = news_at(
        datetime(2026, 9, 30, tzinfo=UTC), datetime(2026, 9, 30, 18, 7, tzinfo=UTC)
    )
    payload = json.loads(render_news_json([item], [], datetime(2026, 10, 1, tzinfo=UTC), 0))
    assert payload["items"][0]["date"] == "2026-10-01"
    assert payload["items"][0]["month"] == "2026-10"


def test_news_json_excludes_importance_and_removed_products() -> None:
    removed = make_news().model_copy(update={"id": 2, "product": "Gemini"})
    payload = json.loads(
        render_news_json([make_news(), removed], [], datetime(2026, 6, 23, tzinfo=UTC), 0)
    )
    assert [item["product"] for item in payload["items"]] == ["ChatGPT"]
    assert "importance" not in payload["items"][0]


def test_display_product_splits_chatgpt_work_by_title_or_body_prefix() -> None:
    def chatgpt(title: str, raw_text: str = "", product: str = "ChatGPT") -> NewsItem:
        return make_news().model_copy(
            update={"title": title, "raw_text": raw_text, "product": product}
        )

    assert display_product(chatgpt("GPT-6 Sol and Luna in Work and Codex")) == "ChatGPT Work"
    assert display_product(chatgpt("Introducing ChatGPT Work")) == "ChatGPT Work"
    assert (
        display_product(chatgpt("Use website tools", "ChatGPT Work and Codex can now use tools"))
        == "ChatGPT Work"
    )
    assert display_product(chatgpt("Organize your work in ChatGPT Space")) == "ChatGPT"
    assert display_product(chatgpt("Work with Apps on macOS")) == "ChatGPT"
    assert display_product(chatgpt("Update", "x" * 400 + " Work item")) == "ChatGPT"
    # 他プロダクト(Codex等)は題名に Work を含んでも変更しない
    assert display_product(chatgpt("GPT-6 in Codex and ChatGPT Work", product="Codex")) == "Codex"
