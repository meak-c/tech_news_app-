import json
from unittest.mock import Mock

import pytest
import requests

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


@pytest.fixture
def llm(tmp_path, monkeypatch):
    settings = Settings(
        db_path=tmp_path / "news.sqlite",
        output_path=tmp_path / "news.json",
        gemini_api_key="test-key",
        gemini_model="test-model",
        gemini_min_interval_seconds=0,
    )
    monkeypatch.setattr("tech_news_app.summarizer.time.sleep", lambda _: None)
    return Summarizer(settings)


@pytest.fixture
def item():
    return FetchedItem(
        product="Test",
        source_name="Test",
        source_url="https://example.com",
        item_url="https://example.com/item",
        title="Feature",
        raw_text="New feature",
    )


def api_response(data, status=200):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(data).encode()
    return response


def success_response():
    return api_response(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "・何が変わったか: 新機能\n・影響: なし\n・注意点: なし"}
                        ]
                    }
                }
            ]
        }
    )


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {},
        {"candidates": []},
        {"candidates": {}},
        {"candidates": [None]},
        {"candidates": [{}]},
        {"candidates": [{"content": []}]},
        {"candidates": [{"content": {"parts": []}}]},
        {"candidates": [{"content": {"parts": "text"}}]},
        {"candidates": [{"content": {"parts": [None]}}]},
        *[
            {"candidates": [{"content": {"parts": [{"text": text}]}}]}
            for text in (None, "", "  \n ", "\u200b\ufeff", 1, [], {})
        ],
    ],
)
def test_malformed_response_falls_back_without_retry(llm, item, monkeypatch, data):
    post = Mock(return_value=api_response(data))
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert llm.summarize(item) == FALLBACK_SUMMARY
    assert post.call_count == 1


def test_normal_response_keeps_existing_normalization(llm, item, monkeypatch):
    from tech_news_app.parser import normalize_text

    text = "・何が変わったか: 新機能\n・影響: なし\n・注意点: なし"
    monkeypatch.setattr(
        "tech_news_app.summarizer.requests.post", Mock(return_value=success_response())
    )
    assert llm.summarize(item) == normalize_text(text).replace(" ・", "\n・")


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429])
def test_permanent_errors_do_not_retry(llm, item, monkeypatch, status):
    post = Mock(return_value=api_response({}, status))
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert llm.summarize(item) == FALLBACK_SUMMARY
    assert post.call_count == 1
    if status == 429:
        assert llm.summarize(item) == FALLBACK_SUMMARY
        assert post.call_count == 1


@pytest.mark.parametrize("failure", [requests.Timeout(), api_response({}, 503)])
def test_transient_errors_retry_and_count_each_attempt(llm, item, monkeypatch, failure):
    post = Mock(side_effect=[failure, success_response()])
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert llm.summarize(item) != FALLBACK_SUMMARY
    assert post.call_count == 2
    import sqlite3

    with sqlite3.connect(llm.settings.db_path) as connection:
        assert (
            connection.execute("SELECT SUM(request_count) FROM gemini_request_usage").fetchone()[0]
            == 2
        )


def test_budget_shared_across_instances_and_includes_retries(llm, item, monkeypatch):
    from dataclasses import replace

    settings = replace(llm.settings, gemini_max_requests_per_day=2)
    post = Mock(side_effect=[requests.Timeout(), success_response()])
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert Summarizer(settings).summarize(item) != FALLBACK_SUMMARY
    assert Summarizer(settings).summarize(item) == FALLBACK_SUMMARY
    assert post.call_count == 2


def test_zero_budget_disables_http(llm, item, monkeypatch):
    from dataclasses import replace

    post = Mock()
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert (
        Summarizer(replace(llm.settings, gemini_max_requests_per_day=0)).summarize(item)
        == FALLBACK_SUMMARY
    )
    post.assert_not_called()


def test_retries_are_bounded(llm, item, monkeypatch):
    post = Mock(side_effect=requests.Timeout())
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert llm.summarize(item) == FALLBACK_SUMMARY
    assert post.call_count == 3


def test_invalid_json_falls_back_without_retry(llm, item, monkeypatch):
    response = api_response({})
    response._content = b"not-json"
    post = Mock(return_value=response)
    monkeypatch.setattr("tech_news_app.summarizer.requests.post", post)
    assert llm.summarize(item) == FALLBACK_SUMMARY
    assert post.call_count == 1
