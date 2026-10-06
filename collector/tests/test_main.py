from datetime import UTC, datetime

from tech_news_app.config import Settings
from tech_news_app.main import backfill_summaries
from tech_news_app.models import FetchedItem
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
