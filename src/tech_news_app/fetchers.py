from __future__ import annotations

import re

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import SOURCES, Settings, SourceConfig
from .models import FetchedItem, SourceError
from .parser import (
    find_databricks_month_urls,
    normalize_text,
    parse_claude_code_changelog,
    parse_claude_release_notes,
    parse_date,
    parse_heading_document,
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
        if source.kind == "claude_code":
            return parse_claude_code_changelog(html, source)
        if source.kind == "databricks":
            return self._fetch_databricks(html, source)
        return parse_heading_document(html, source)

    def _fetch_databricks(self, index_html: str, source: SourceConfig) -> list[FetchedItem]:
        items: list[FetchedItem] = []
        for month_url in find_databricks_month_urls(index_html, source.url):
            response = self.session.get(month_url, timeout=self.settings.request_timeout)
            response.raise_for_status()
            month_source = SourceConfig(
                product=source.product,
                source_name=source.source_name,
                url=month_url,
                max_items=source.max_items - len(items),
            )
            html = response.content.decode("utf-8", errors="replace")
            items.extend(parse_heading_document(html, month_source))
            if len(items) >= source.max_items:
                break
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
