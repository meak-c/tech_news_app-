from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceConfig:
    product: str
    source_name: str
    url: str
    fetch_url: str | None = None
    kind: str = "html"
    max_items: int = 12


@dataclass(frozen=True)
class Settings:
    db_path: Path
    output_path: Path
    gemini_api_key: str | None
    gemini_model: str
    gemini_min_interval_seconds: float
    request_timeout: int = 30
    user_agent: str = "tech-news-app/0.1 (+personal official release-note reader)"

    @classmethod
    def from_env(cls, output_override: str | None = None) -> Settings:
        return cls(
            db_path=Path(os.getenv("TECH_NEWS_DB_PATH", "data/news.sqlite")),
            output_path=Path(
                output_override or os.getenv("TECH_NEWS_OUTPUT_PATH", "public/index.html")
            ),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
            gemini_min_interval_seconds=float(
                os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "4.1")
            ),
        )


SOURCES = (
    SourceConfig(
        product="ChatGPT",
        source_name="ChatGPT Release Notes",
        url="https://help.openai.com/en/articles/6825453-chatgpt-release-notes",
        fetch_url="https://help.openai.com/en/articles/6825453-chatgpt-release-notes.json",
    ),
    SourceConfig(
        product="Claude",
        source_name="Claude Release Notes",
        url="https://support.claude.com/en/articles/12138966-release-notes",
        kind="claude",
    ),
    SourceConfig(
        product="Claude Code",
        source_name="Claude Code Changelog",
        url="https://code.claude.com/docs/en/changelog",
        kind="claude_code",
    ),
    SourceConfig(
        product="Claude Code",
        source_name="Claude Code GitHub Releases",
        url="https://github.com/anthropics/claude-code/releases.atom",
        kind="atom",
    ),
    SourceConfig(
        product="Databricks",
        source_name="Databricks Release Notes",
        url="https://docs.databricks.com/aws/en/release-notes/",
        kind="databricks",
    ),
)

PRODUCTS = ("ChatGPT", "Claude", "Claude Code", "Databricks")
