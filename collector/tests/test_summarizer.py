from tech_news_app.config import Settings
from tech_news_app.models import FetchedItem
from tech_news_app.summarizer import FALLBACK_SUMMARY, Summarizer, needs_resummary


def test_fallback_summary_does_not_include_long_english_body(tmp_path) -> None:
    settings = Settings(
        db_path=tmp_path / "news.sqlite",
        output_path=tmp_path / "index.html",
        gemini_api_key=None,
        gemini_model="gemini-3.5-flash-lite",
        gemini_min_interval_seconds=0,
    )
    item = FetchedItem(
        product="Gemini",
        source_name="Gemini Release Notes",
        source_url="https://example.com",
        item_url="https://example.com/item",
        title="A feature is generally available",
        raw_text="This is a very long English release note. " * 30,
    )
    summary = Summarizer(settings, use_llm=False).summarize(item)
    assert summary == "要約未生成。公式ページで確認してください。"
    assert "This is a very long English release note" not in summary


def test_needs_resummary_detects_current_and_legacy_fallbacks() -> None:
    assert needs_resummary(FALLBACK_SUMMARY)
    assert needs_resummary("")
    assert needs_resummary("本文抜粋です。自動要約ではありません。")
    assert not needs_resummary("・何が変わったか: 新機能\n・影響: なし\n・注意点: なし")
