from tech_news_app.config import Settings
from tech_news_app.models import FetchedItem
from tech_news_app.summarizer import Summarizer


def test_fallback_summary_does_not_include_long_english_body(tmp_path) -> None:
    settings = Settings(
        db_path=tmp_path / "news.sqlite",
        output_path=tmp_path / "index.html",
        gemini_api_key=None,
        gemini_model="gemini-2.5-flash-lite",
        gemini_min_interval_seconds=0,
    )
    item = FetchedItem(
        product="Databricks",
        source_name="Databricks Release Notes",
        source_url="https://example.com",
        item_url="https://example.com/item",
        title="A feature is generally available",
        raw_text="This is a very long English release note. " * 30,
    )
    summary = Summarizer(settings, use_llm=False).summarize(item)
    assert summary == "要約未生成。公式ページで確認してください。"
    assert "This is a very long English release note" not in summary
