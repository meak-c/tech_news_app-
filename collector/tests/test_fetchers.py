import json
from datetime import UTC, datetime, timedelta

import pytest

from tech_news_app.config import Settings, SourceConfig
from tech_news_app.fetchers import NewsFetcher


class StubResponse:
    def __init__(self, text: str, status: int = 200) -> None:
        self.content = text.encode()
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class StubSession:
    def __init__(self, pages: dict[str, StubResponse]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str, timeout: int) -> StubResponse:
        self.requested.append(url)
        return self.pages[url]


def collection_page(articles: list[tuple[str, datetime]]) -> StubResponse:
    summaries = [
        {
            "id": str(index),
            "title": title,
            "url": f"https://support.example.com/en/articles/{index}-a",
            "lastUpdatedDate": updated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for index, (title, updated) in enumerate(articles, start=1)
    ]
    data = {"props": {"collection": {"articleSummaries": summaries}}}
    return StubResponse(
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'
    )


def make_fetcher(pages: dict[str, StubResponse], tmp_path) -> NewsFetcher:
    settings = Settings(
        db_path=tmp_path / "news.sqlite",
        output_path=tmp_path / "news.json",
        gemini_api_key=None,
        gemini_model="gemini-3.5-flash-lite",
        gemini_min_interval_seconds=0,
    )
    fetcher = NewsFetcher(settings)
    fetcher.session = StubSession(pages)  # type: ignore[assignment]
    return fetcher


SOURCE = SourceConfig(
    product="Claude Cowork",
    source_name="Claude Cowork Help Center",
    url="https://support.example.com/en/collections/1-cowork",
    kind="helpcenter",
    max_age_days=14,
)


def test_helpcenter_fetches_only_recently_updated_articles(tmp_path) -> None:
    now = datetime.now(UTC)
    recent = now - timedelta(days=1)
    pages = {
        SOURCE.url: collection_page([("Recent", recent), ("Old", now - timedelta(days=60))]),
        "https://support.example.com/en/articles/1-a": StubResponse(
            "<article>What changed on October 6</article>"
        ),
    }
    fetcher = make_fetcher(pages, tmp_path)
    items = fetcher.fetch_source(SOURCE)
    assert len(items) == 1
    item = items[0]
    assert item.title == "Help Center: Recent"
    assert item.item_url.startswith("https://support.example.com/en/articles/1-a#updated-")
    assert item.published_at == recent.replace(microsecond=0)
    assert item.raw_text == "What changed on October 6"
    assert fetcher.session.requested == [SOURCE.url, "https://support.example.com/en/articles/1-a"]  # type: ignore[attr-defined]


def test_helpcenter_skips_failed_article_but_keeps_others(tmp_path) -> None:
    now = datetime.now(UTC)
    pages = {
        SOURCE.url: collection_page([("First", now), ("Second", now - timedelta(hours=1))]),
        "https://support.example.com/en/articles/1-a": StubResponse("boom", status=500),
        "https://support.example.com/en/articles/2-a": StubResponse("<article>ok</article>"),
    }
    items = make_fetcher(pages, tmp_path).fetch_source(SOURCE)
    assert [item.title for item in items] == ["Help Center: Second"]


def test_helpcenter_raises_when_every_article_fails(tmp_path) -> None:
    now = datetime.now(UTC)
    pages = {
        SOURCE.url: collection_page([("First", now)]),
        "https://support.example.com/en/articles/1-a": StubResponse("boom", status=500),
    }
    with pytest.raises(ValueError):
        make_fetcher(pages, tmp_path).fetch_source(SOURCE)
