import json
from unittest.mock import Mock

import requests

from tech_news_app import main
from tech_news_app.config import Settings
from tech_news_app.models import FetchedItem
from tech_news_app.storage import NewsStorage
from tech_news_app.summarizer import FALLBACK_SUMMARY


def make_item(index):
    return FetchedItem(
        product="Codex",
        source_name="Codex Changelog",
        source_url="https://example.com",
        item_url=f"https://example.com/{index}",
        title=f"Release {index}",
        raw_text=f"Body {index}",
    )


def test_run_shares_budget_between_new_and_backfill_and_next_run(monkeypatch, tmp_path):
    settings = Settings(
        db_path=tmp_path / "news.sqlite",
        output_path=tmp_path / "news.json",
        gemini_api_key="test",
        gemini_model="test",
        gemini_min_interval_seconds=0,
        gemini_max_requests_per_day=2,
    )
    monkeypatch.setattr(Settings, "from_env", lambda **kwargs: settings)
    monkeypatch.setattr(main.NewsFetcher, "fetch_all", lambda self: ([make_item(3)], []))
    monkeypatch.setattr("tech_news_app.summarizer.time.sleep", lambda _: None)
    with NewsStorage(settings.db_path) as storage:
        storage.save_item(make_item(1), FALLBACK_SUMMARY)
        storage.save_item(make_item(2), FALLBACK_SUMMARY)
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(
        {"candidates": [{"content": {"parts": [{"text": "生成された要約"}]}}]}
    ).encode()
    post = Mock(return_value=response)
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert main.run() == 0
    assert post.call_count == 2
    with NewsStorage(settings.db_path) as storage:
        articles = storage.all_news()
        assert sum(item.summary_ja == FALLBACK_SUMMARY for item in articles) == 1
        assert (
            next(item for item in articles if item.item_url.endswith("/3")).summary_ja
            == "生成された要約"
        )
    assert main.run() == 0
    assert post.call_count == 2
    with NewsStorage(settings.db_path) as storage:
        assert (
            storage.connection.execute(
                "SELECT SUM(request_count) FROM gemini_request_usage"
            ).fetchone()[0]
            == 2
        )
