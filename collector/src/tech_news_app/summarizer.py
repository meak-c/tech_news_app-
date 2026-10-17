from __future__ import annotations

import sqlite3
import time
from contextlib import closing

import requests

from .budget import RequestBudget
from .config import Settings
from .models import FetchedItem
from .parser import normalize_text

FALLBACK_SUMMARY = "要約未生成。公式ページで確認してください。"
# 過去バージョンで保存された簡易要約。これを含む要約も再要約の対象にする。
LEGACY_FALLBACK_MARKERS = ("自動要約ではありません。",)


def needs_resummary(summary: str) -> bool:
    """保存済み要約がフォールバック(未要約)扱いかどうかを返す。"""
    if not summary or summary == FALLBACK_SUMMARY:
        return True
    return any(marker in summary for marker in LEGACY_FALLBACK_MARKERS)


class Summarizer:
    def __init__(
        self, settings: Settings, use_llm: bool = True, budget: RequestBudget | None = None
    ) -> None:
        self.settings = settings
        self.use_llm = use_llm and bool(settings.gemini_api_key)
        self.last_request_at = 0.0
        self.budget = budget
        self.requests_stopped = False

    def summarize(self, item: FetchedItem) -> str:
        if not self.use_llm or self.requests_stopped:
            return self.fallback(item)
        try:
            return self._gemini(item)
        except (requests.RequestException, ValueError, KeyError):
            return self.fallback(item)

    def fallback(self, item: FetchedItem) -> str:
        return FALLBACK_SUMMARY

    def _gemini(self, item: FetchedItem) -> str:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent"
        )
        prompt = (
            "次の公開済み公式リリースノートを日本語で簡潔に要約してください。\n"
            "出力は必ず日本語にしてください。英語本文をそのまま貼り付けないでください。\n"
            "製品名、機能名、API名、CLIコマンドだけは英語のままで構いません。\n"
            "必ず3行で、次の形式だけを返してください。\n"
            "・何が変わったか: ...\n・影響: ...\n・注意点: ...\n"
            "利用可能時期、Preview/GA、破壊的変更、料金、権限、セキュリティが"
            "明記されている場合は優先してください。推測はしないでください。\n"
            "ヘルプ記事の更新の場合は、日付や「What changed」など、最近の変更点を述べている"
            "節を優先して要約してください。\n\n"
            f"製品: {item.product}\nタイトル: {item.title}\n本文:\n{item.raw_text[:6000]}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }
        for attempt in range(3):
            elapsed = time.monotonic() - self.last_request_at
            wait_seconds = self.settings.gemini_min_interval_seconds - elapsed
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            if not self._acquire_request():
                self.requests_stopped = True
                return self.fallback(item)
            self.last_request_at = time.monotonic()
            try:
                response = requests.post(
                    endpoint,
                    headers={
                        "x-goog-api-key": self.settings.gemini_api_key or "",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=45,
                )
                if response.status_code == 429:
                    self.requests_stopped = True
                    return self.fallback(item)
                response.raise_for_status()
            except requests.RequestException as exc:
                # Retry only transient server and transport failures.
                status = exc.response.status_code if exc.response is not None else None
                retryable = isinstance(exc, (requests.Timeout, requests.ConnectionError)) or (
                    status is not None and 500 <= status < 600
                )
                if not retryable or attempt == 2:
                    return self.fallback(item)
                time.sleep(2**attempt)
                continue
            return self._response_text(response.json())
        return self.fallback(item)

    def _acquire_request(self) -> bool:
        if self.budget is not None:
            return self.budget.try_acquire()
        # Standalone callers share the same persisted budget as the collector.
        self.settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.settings.db_path)) as connection:
            return RequestBudget(
                connection, self.settings.gemini_max_requests_per_day
            ).try_acquire()

    @staticmethod
    def _response_text(data: object) -> str:
        if not isinstance(data, dict):
            raise ValueError("Invalid Gemini response")
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError("Gemini returned no candidates")
        candidate = candidates[0]
        content = candidate.get("content") if isinstance(candidate, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list) or not parts or not isinstance(parts[0], dict):
            raise ValueError("Gemini returned no text parts")
        text = parts[0].get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Gemini returned empty text")
        normalized = normalize_text(text).replace(" ・", "\n・")
        if not normalized:
            raise ValueError("Gemini returned empty normalized text")
        return normalized
