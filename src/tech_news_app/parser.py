from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from .config import SourceConfig
from .models import FetchedItem, Importance

DATE_PATTERNS = (
    re.compile(
        r"^(January|February|March|April|May|June|July|August|September|October|"
        r"November|December)\s+\d{1,2},\s+\d{4}$",
        re.IGNORECASE,
    ),
    re.compile(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$"),
)

HIGH_KEYWORDS = (
    "new model",
    "launch",
    "generally available",
    " ga ",
    "pricing",
    "security",
    "breaking change",
    "deprecation",
    "deprecated",
    "authentication",
    "permission",
    "runtime",
)
MEDIUM_KEYWORDS = (
    "feature",
    "improvement",
    "preview",
    "beta",
    "connector",
    "integration",
    "admin",
    "management",
)
LOW_KEYWORDS = ("bug fix", "bugfix", "minor", "documentation", "small improvement", "fixed")


def normalize_text(value: str) -> str:
    value = value.replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", value).strip()


def content_hash(title: str, raw_text: str) -> str:
    normalized = normalize_text(f"{title}\n{raw_text}").lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def classify_importance(title: str, raw_text: str = "") -> Importance:
    haystack = f" {title} {raw_text[:1000]} ".lower()
    if any(keyword in haystack for keyword in HIGH_KEYWORDS):
        return Importance.HIGH
    if any(keyword in haystack for keyword in LOW_KEYWORDS):
        return Importance.LOW
    if any(keyword in haystack for keyword in MEDIUM_KEYWORDS):
        return Importance.MEDIUM
    return Importance.MEDIUM


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value, fuzzy=False)
    except (ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _looks_like_date(value: str) -> bool:
    text = normalize_text(value)
    return any(pattern.match(text) for pattern in DATE_PATTERNS)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def parse_heading_document(html: str, source: SourceConfig) -> list[FetchedItem]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("main, article") or soup
    headings = root.find_all(["h1", "h2"])
    current_date: datetime | None = None
    items: list[FetchedItem] = []

    for heading in headings:
        title = normalize_text(heading.get_text(" ", strip=True))
        if not title or title.lower() in {
            "release notes",
            "chatgpt — release notes",
            "claude code changelog",
        }:
            continue
        if _looks_like_date(title):
            current_date = parse_date(title)
            continue
        if heading.name != "h2":
            continue

        body_parts: list[str] = []
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag) and sibling.name in {"h1", "h2"}:
                break
            if isinstance(sibling, Tag):
                text = normalize_text(sibling.get_text(" ", strip=True))
                if text:
                    body_parts.append(text)
            if sum(map(len, body_parts)) >= 5000:
                break
        raw_text = normalize_text(" ".join(body_parts))[:6000]
        published_at = current_date
        if published_at is None:
            date_match = re.search(
                r"(January|February|March|April|May|June|July|August|September|October|"
                r"November|December)\s+\d{1,2},\s+\d{4}",
                raw_text,
                re.IGNORECASE,
            )
            if date_match:
                published_at = parse_date(date_match.group(0))
        if not raw_text and len(title) < 4:
            continue

        anchor = heading.get("id")
        if not anchor:
            nested_anchor = heading.find("a", href=True)
            anchor = nested_anchor.get("href", "").lstrip("#") if nested_anchor else ""
        fragment = anchor or _slug(
            f"{current_date.date().isoformat() if current_date else ''}-{title}"
        )
        items.append(
            FetchedItem(
                product=source.product,
                source_name=source.source_name,
                source_url=source.url,
                item_url=f"{source.url}#{fragment}",
                title=title[:500],
                published_at=published_at,
                raw_text=raw_text,
            )
        )
        if len(items) >= source.max_items:
            break
    return items


def parse_claude_release_notes(html: str, source: SourceConfig) -> list[FetchedItem]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("article, main") or soup
    items: list[FetchedItem] = []
    for heading in root.find_all("h3"):
        date_text = normalize_text(heading.get_text(" ", strip=True))
        published_at = parse_date(date_text) if _looks_like_date(date_text) else None
        if published_at is None:
            continue
        container = heading.parent
        body_parts: list[str] = []
        for sibling in container.next_siblings:
            if isinstance(sibling, Tag) and sibling.find(["h2", "h3"]):
                break
            if isinstance(sibling, Tag):
                text = normalize_text(sibling.get_text(" ", strip=True))
                if text:
                    body_parts.append(text)
            if sum(map(len, body_parts)) >= 6000:
                break
        raw_text = normalize_text(" ".join(body_parts))[:6000]
        if not raw_text:
            continue
        first_sentence = re.split(r"(?<=[.!?])\s+", raw_text, maxsplit=1)[0]
        title = first_sentence[:180] or f"Claude update: {date_text}"
        anchor = heading.get("id") or _slug(f"{date_text}-{title}")
        items.append(
            FetchedItem(
                product=source.product,
                source_name=source.source_name,
                source_url=source.url,
                item_url=f"{source.url}#{anchor}",
                title=title[:500],
                published_at=published_at,
                raw_text=raw_text,
            )
        )
        if len(items) >= source.max_items:
            break
    return items


def parse_claude_code_changelog(html: str, source: SourceConfig) -> list[FetchedItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[FetchedItem] = []
    for container in soup.select("div.update-container"):
        label = container.select_one('[data-component-part="update-label"]')
        description = container.select_one('[data-component-part="update-description"]')
        if label is None:
            continue
        version = normalize_text(label.get_text(" ", strip=True))
        published_at = parse_date(description.get_text(" ", strip=True) if description else None)
        content = container.select_one(".prose") or container
        raw_text = normalize_text(content.get_text(" ", strip=True))[:6000]
        container_id = container.get("id") or _slug(version)
        items.append(
            FetchedItem(
                product=source.product,
                source_name=source.source_name,
                source_url=source.url,
                item_url=f"{source.url}#{container_id}",
                title=f"v{version.lstrip('v')}",
                published_at=published_at,
                raw_text=raw_text,
            )
        )
        if len(items) >= source.max_items:
            break
    return items


def find_databricks_month_urls(html: str, source_url: str, limit: int = 2) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("main") or soup
    urls: list[str] = []
    for link in root.find_all("a", href=True):
        item_url = urljoin(source_url, link["href"])
        if re.search(r"/release-notes/product/\d{4}/[a-z]+/?$", item_url) and item_url not in urls:
            urls.append(item_url)
        if len(urls) >= limit:
            break
    return urls
