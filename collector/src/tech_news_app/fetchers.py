from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import SOURCES, Settings, SourceConfig
from .models import FetchedItem, SourceError
from .parser import (
    normalize_text,
    parse_claude_release_notes,
    parse_codex_changelog,
    parse_date,
    parse_heading_document,
    parse_helpcenter_article,
    parse_helpcenter_collection,
    parse_mintlify_changelog,
)


class NewsFetcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def fetch_all(self) -> tuple[list[FetchedItem], list[SourceError]]:
        all_items: list[FetchedItem] = []
        errors: list[SourceError] = []
        for source in SOURCES:
            try:
                all_items.extend(self.fetch_source(source))
            except Exception as exc:  # Continue rendering when a source is unavailable.
                errors.append(SourceError(source_name=source.source_name, message=str(exc)))
        return self._deduplicate(all_items), errors

    def fetch_source(self, source: SourceConfig) -> list[FetchedItem]:
        response = self.session.get(
            source.fetch_url or source.url, timeout=self.settings.request_timeout
        )
        response.raise_for_status()
        html = response.content.decode("utf-8", errors="replace")
        if source.kind == "atom":
            return self._parse_atom(response.content, source)
        if source.kind == "claude":
            return parse_claude_release_notes(html, source)
        if source.kind == "helpcenter":
            return self._fetch_helpcenter(html, source)
        if source.kind == "mintlify":
            return parse_mintlify_changelog(html, source)
        if source.kind == "codex":
            return parse_codex_changelog(html, source)
        return parse_heading_document(html, source)

    def _fetch_helpcenter(self, collection_html: str, source: SourceConfig) -> list[FetchedItem]:
        """コレクション内の記事のうち、期間内に更新されたものを「更新」として取得する。

        更新のたびに別の記事として扱えるよう、item_url に更新日時を含める。
        """
        articles = parse_helpcenter_collection(collection_html)
        if source.max_age_days is not None:
            threshold = datetime.now(UTC) - timedelta(days=source.max_age_days)
            articles = [article for article in articles if article.updated_at >= threshold]
        items: list[FetchedItem] = []
        failures: list[str] = []
        for article in articles[: source.max_items]:
            try:
                response = self.session.get(article.url, timeout=self.settings.request_timeout)
                response.raise_for_status()
                raw_text = parse_helpcenter_article(response.content.decode("utf-8", "replace"))
            except Exception as exc:  # 1記事の失敗で他の記事を落とさない
                failures.append(f"{article.url}: {exc}")
                continue
            stamp = article.updated_at.strftime("%Y%m%dT%H%M%SZ")
            items.append(
                FetchedItem(
                    product=source.product,
                    source_name=source.source_name,
                    source_url=source.url,
                    item_url=f"{article.url}#updated-{stamp}",
                    title=f"Help Center: {article.title}"[:500],
                    published_at=article.updated_at,
                    raw_text=raw_text,
                )
            )
        if failures and not items:
            raise ValueError(f"All help center articles failed: {failures[0]}")
        return items

    def _parse_atom(self, content: bytes, source: SourceConfig) -> list[FetchedItem]:
        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            raise ValueError(f"Atom feed parse error: {feed.bozo_exception}")
        items: list[FetchedItem] = []
        for entry in feed.entries[: source.max_items]:
            raw_html = (
                entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
            )
            raw_text = normalize_text(
                BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
            )
            items.append(
                FetchedItem(
                    product=source.product,
                    source_name=source.source_name,
                    source_url=source.url,
                    item_url=entry.get("link", source.url),
                    title=normalize_text(entry.get("title", "Untitled release"))[:500],
                    published_at=parse_date(entry.get("published") or entry.get("updated")),
                    raw_text=raw_text[:6000],
                )
            )
        return items

    @staticmethod
    def _deduplicate(items: list[FetchedItem]) -> list[FetchedItem]:
        result: list[FetchedItem] = []
        keys: set[tuple[str, str, str]] = set()
        for item in items:
            date_key = item.published_at.date().isoformat() if item.published_at else ""
            normalized_title = re.sub(r"^v(?=\d)", "", item.title.lower())
            key = (item.product.lower(), normalized_title, date_key)
            url_key = (item.product.lower(), item.item_url.lower(), "")
            if key in keys or url_key in keys:
                continue
            keys.add(key)
            keys.add(url_key)
            result.append(item)
        return result
