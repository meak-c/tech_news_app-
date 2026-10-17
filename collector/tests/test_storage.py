from datetime import UTC, datetime

from tech_news_app.models import FetchedItem
from tech_news_app.parser import classify_importance, content_hash
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


def test_update_keeps_content_summary_and_metadata_consistent(tmp_path) -> None:
    original = make_item()
    changed = original.model_copy(
        update={"title": "Breaking change", "raw_text": "Security vulnerability fixed."}
    )
    with NewsStorage(tmp_path / "news.sqlite") as storage:
        previous, _ = storage.save_item(original, "以前の要約")
        saved, is_new = storage.save_item(changed, "更新後の要約")
        assert not is_new
        assert saved.id == previous.id
        assert saved.first_seen_at == previous.first_seen_at
        assert saved.created_at == previous.created_at
        assert saved.published_at == previous.published_at
        assert saved.title == changed.title
        assert saved.raw_text == changed.raw_text
        assert saved.content_hash == content_hash(changed.title, changed.raw_text)
        assert saved.importance == classify_importance(changed.title, changed.raw_text)
        assert saved.summary_ja == "更新後の要約"
        assert len(storage.all_news()) == 1


def test_unchanged_update_preserves_stored_values(tmp_path) -> None:
    with NewsStorage(tmp_path / "news.sqlite") as storage:
        previous, _ = storage.save_item(make_item(), "既存の要約")
        saved, is_new = storage.save_item(make_item(), previous.summary_ja)
        volatile_fields = {"fetched_at", "last_seen_at", "updated_at", "is_new"}
        assert saved.model_dump(exclude=volatile_fields) == previous.model_dump(
            exclude=volatile_fields
        )
        assert not is_new
