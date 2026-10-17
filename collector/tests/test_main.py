import json
from datetime import UTC, datetime, timedelta

import pytest

from tech_news_app import main
from tech_news_app.config import Settings
from tech_news_app.exporter import render_news_json
from tech_news_app.main import backfill_summaries
from tech_news_app.models import FetchedItem
from tech_news_app.parser import content_hash
from tech_news_app.storage import NewsStorage
from tech_news_app.summarizer import FALLBACK_SUMMARY, Summarizer


class StubSummarizer(Summarizer):
    def __init__(self, results: list[str]) -> None:
        settings = Settings(
            db_path=None,  # type: ignore[arg-type]
            output_path=None,  # type: ignore[arg-type]
            gemini_api_key="dummy",
            gemini_model="gemini-3.5-flash-lite",
            gemini_min_interval_seconds=0,
        )
        super().__init__(settings, use_llm=True)
        self.results = results
        self.calls = 0

    def summarize(self, item: FetchedItem) -> str:
        self.calls += 1
        return self.results.pop(0)


def make_item(index: int) -> FetchedItem:
    return FetchedItem(
        product="Codex",
        source_name="Codex Changelog",
        source_url="https://example.com",
        item_url=f"https://example.com/{index}",
        title=f"Release {index}",
        published_at=datetime(2026, 6, index, tzinfo=UTC),
        raw_text=f"body {index}",
    )


def test_backfill_updates_fallback_summaries(tmp_path) -> None:
    with NewsStorage(tmp_path / "news.sqlite") as storage:
        storage.save_item(make_item(1), FALLBACK_SUMMARY)
        storage.save_item(make_item(2), "・何が変わったか: 要約済み")
        summarizer = StubSummarizer(["・何が変わったか: 再要約"])
        assert backfill_summaries(storage, summarizer) == 1
        summaries = {item.title: item.summary_ja for item in storage.all_news()}
    assert summaries["Release 1"] == "・何が変わったか: 再要約"
    assert summaries["Release 2"] == "・何が変わったか: 要約済み"


def test_backfill_stops_after_failure_and_respects_skip_ids(tmp_path) -> None:
    with NewsStorage(tmp_path / "news.sqlite") as storage:
        skipped, _ = storage.save_item(make_item(3), FALLBACK_SUMMARY)
        for index in (1, 2):
            storage.save_item(make_item(index), FALLBACK_SUMMARY)
        summarizer = StubSummarizer([FALLBACK_SUMMARY, "unused"])
        assert backfill_summaries(storage, summarizer, skip_ids={skipped.id}) == 0
    assert summarizer.calls == 1


def configure_run(monkeypatch, tmp_path, fetched, summarizer) -> Settings:
    settings = Settings(
        db_path=tmp_path / "news.sqlite",
        output_path=tmp_path / "news.json",
        gemini_api_key="dummy",
        gemini_model="gemini-3.5-flash-lite",
        gemini_min_interval_seconds=0,
    )
    monkeypatch.setattr(Settings, "from_env", lambda **kwargs: settings)
    monkeypatch.setattr(main.NewsFetcher, "fetch_all", lambda self: (fetched, []))
    monkeypatch.setattr(main, "Summarizer", lambda *args, **kwargs: summarizer)
    return settings


def test_run_reuses_summary_and_preserves_export_for_unchanged_article(
    monkeypatch, tmp_path
) -> None:
    fetched = make_item(1)
    summarizer = StubSummarizer([])
    settings = configure_run(monkeypatch, tmp_path, [fetched], summarizer)
    with monkeypatch.context() as patch:
        yesterday = datetime.now(UTC) - timedelta(days=1)
        patch.setattr("tech_news_app.storage.utc_now", lambda: yesterday)
        with NewsStorage(settings.db_path) as storage:
            previous, _ = storage.save_item(fetched, "既存の要約")
    assert main.run() == 0
    with NewsStorage(settings.db_path) as storage:
        actual = storage.all_news()[0]
    volatile_fields = {"fetched_at", "last_seen_at", "updated_at", "is_new"}
    assert actual.model_dump(exclude=volatile_fields) == previous.model_dump(
        exclude=volatile_fields
    )
    # Compare the public payload against the previous behavior for an existing article.
    # The fetch time advances on every run, while its content and newness stay the same.
    previous.fetched_at = actual.fetched_at
    previous.is_new = False
    payload = json.loads(settings.output_path.read_text())
    run_at = datetime.fromisoformat(payload["generated_at"])
    assert payload == json.loads(render_news_json([previous], [], run_at, new_count=0))
    assert summarizer.calls == 0


@pytest.mark.parametrize(
    "update",
    [{"raw_text": "Changed body"}, {"title": "Changed title"}],
)
def test_run_resummarizes_changed_article(monkeypatch, tmp_path, update) -> None:
    original = make_item(1)
    changed = original.model_copy(update=update)
    summarizer = StubSummarizer(["更新後の要約"])
    settings = configure_run(monkeypatch, tmp_path, [changed], summarizer)
    with NewsStorage(settings.db_path) as storage:
        previous, _ = storage.save_item(original, "既存の要約")
    assert main.run() == 0
    with NewsStorage(settings.db_path) as storage:
        saved = storage.all_news()[0]
    assert saved.summary_ja == "更新後の要約"
    assert saved.title == changed.title
    assert saved.raw_text == changed.raw_text
    assert saved.content_hash == content_hash(changed.title, changed.raw_text)
    assert saved.id == previous.id
    assert saved.first_seen_at == previous.first_seen_at
    assert summarizer.calls == 1


def test_run_retries_changed_article_after_failed_summary(monkeypatch, tmp_path) -> None:
    original = make_item(1)
    changed = original.model_copy(update={"raw_text": "Changed body"})
    summarizer = StubSummarizer([FALLBACK_SUMMARY, "再試行後の要約"])
    settings = configure_run(monkeypatch, tmp_path, [changed], summarizer)
    with NewsStorage(settings.db_path) as storage:
        storage.save_item(original, "古い本文の要約")
    assert main.run() == 0
    with NewsStorage(settings.db_path) as storage:
        assert storage.all_news()[0].summary_ja == FALLBACK_SUMMARY
    assert main.run() == 0
    with NewsStorage(settings.db_path) as storage:
        assert storage.all_news()[0].summary_ja == "再試行後の要約"
    assert summarizer.calls == 2


def test_run_resummarizes_legacy_inconsistent_hash(monkeypatch, tmp_path) -> None:
    fetched = make_item(1)
    summarizer = StubSummarizer(["修復後の要約"])
    settings = configure_run(monkeypatch, tmp_path, [fetched], summarizer)
    with NewsStorage(settings.db_path) as storage:
        storage.save_item(fetched, "以前の要約")
        storage.connection.execute("UPDATE news SET content_hash = 'legacy-stale-hash'")
        storage.connection.commit()
    assert main.run() == 0
    with NewsStorage(settings.db_path) as storage:
        saved = storage.all_news()[0]
    assert saved.summary_ja == "修復後の要約"
    assert saved.content_hash == content_hash(fetched.title, fetched.raw_text)
    assert summarizer.calls == 1


def test_two_runs_keep_morning_and_late_updates_in_today_then_clear_next_day(
    monkeypatch, tmp_path
):
    import json

    from tech_news_app import storage as storage_module

    clock = [datetime.fromisoformat("2026-10-18T03:07:00+09:00")]

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0].astimezone(tz)

    morning = make_item(1).model_copy(update={
        "published_at": datetime.fromisoformat("2026-10-17T23:00:00+09:00")
    })
    noon = make_item(2).model_copy(update={
        "published_at": datetime.fromisoformat("2026-10-18T10:00:00+09:00")
    })
    fetched = [morning]
    summarizer = StubSummarizer(["朝の要約", "昼の要約"])
    settings = configure_run(monkeypatch, tmp_path, fetched, summarizer)
    monkeypatch.setattr(main, "datetime", Clock)
    monkeypatch.setattr(storage_module, "utc_now", lambda: clock[0].astimezone(UTC))
    assert main.run() == 0
    first = json.loads(settings.output_path.read_text())
    assert first["new_count"] == 1
    assert first["items"][0]["date"] == "2026-10-18"

    clock[0] = datetime.fromisoformat("2026-10-18T11:15:00+09:00")
    fetched.append(noon)
    assert main.run() == 0
    second = json.loads(settings.output_path.read_text())
    assert second["new_count"] == 2
    assert all(item["is_new"] and item["date"] == "2026-10-18" for item in second["items"])
    assert summarizer.calls == 2

    # No new items on another same-day run must not clear today's highlights.
    assert main.run() == 0
    assert json.loads(settings.output_path.read_text())["new_count"] == 2
    clock[0] = datetime.fromisoformat("2026-10-19T00:01:00+09:00")
    assert main.run() == 0
    third = json.loads(settings.output_path.read_text())
    assert third["new_count"] == 0
    assert all(not item["is_new"] and item["date"] == "2026-10-18" for item in third["items"])
    assert summarizer.calls == 2
