from datetime import UTC, datetime

from tech_news_app.models import FetchedItem
from tech_news_app.storage import NewsStorage


def make_item(url: str = "https://example.com/releases/1") -> FetchedItem:
    return FetchedItem(
        product="Claude Code",
        source_name="Official Releases",
        source_url="https://example.com/releases",
        item_url=url,
        title="Version 1",
        published_at=datetime(2026, 6, 23, tzinfo=UTC),
        raw_text="A new feature.",
    )


def test_insert_news(tmp_path) -> None:
    with NewsStorage(tmp_path / "news.sqlite") as storage:
        item, is_new = storage.save_item(make_item(), "要約")
        assert is_new is True
        assert item.id is not None


def test_same_url_is_not_inserted_twice(tmp_path) -> None:
    with NewsStorage(tmp_path / "news.sqlite") as storage:
        storage.save_item(make_item(), "要約")
        _, is_new = storage.save_item(make_item(), "別の要約")
        assert is_new is False
        assert len(storage.latest_news()) == 1


def test_latest_news_remains_available_without_new_items(tmp_path) -> None:
    with NewsStorage(tmp_path / "news.sqlite") as storage:
        storage.save_item(make_item(), "要約")
        assert storage.latest_news()[0].title == "Version 1"
