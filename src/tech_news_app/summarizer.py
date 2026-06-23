from __future__ import annotations

import time

import requests

from .config import Settings
from .models import FetchedItem
from .parser import normalize_text


class Summarizer:
    def __init__(self, settings: Settings, use_llm: bool = True) -> None:
        self.settings = settings
        self.use_llm = use_llm and bool(settings.gemini_api_key)
        self.last_request_at = 0.0

    def summarize(self, item: FetchedItem) -> str:
        if not self.use_llm:
            return self.fallback(item)
        try:
            return self._gemini(item)
        except (requests.RequestException, ValueError, KeyError):
            return self.fallback(item)

    def fallback(self, item: FetchedItem) -> str:
        text = normalize_text(item.raw_text)
        if not text:
            text = item.title
        excerpt = text[:280]
        if len(text) > 280:
            excerpt = excerpt.rstrip() + "…"
        return (
            f"・何が変わったか: {excerpt}\n"
            "・影響: 公式リンクで詳細を確認してください。\n"
            "・注意点: 自動要約ではありません。"
        )

    def _gemini(self, item: FetchedItem) -> str:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent"
        )
        prompt = (
            "次の公開済み公式リリースノートを日本語で簡潔に要約してください。\n"
            "必ず3行で、次の形式だけを返してください。\n"
            "・何が変わったか: ...\n・影響: ...\n・注意点: ...\n"
            "利用可能時期、Preview/GA、破壊的変更、料金、権限、セキュリティが"
            "明記されている場合は優先してください。推測はしないでください。\n\n"
            f"製品: {item.product}\nタイトル: {item.title}\n本文:\n{item.raw_text[:6000]}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                elapsed = time.monotonic() - self.last_request_at
                wait_seconds = self.settings.gemini_min_interval_seconds - elapsed
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                self.last_request_at = time.monotonic()
                response = requests.post(
                    endpoint,
                    headers={
                        "x-goog-api-key": self.settings.gemini_api_key or "",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=45,
                )
                if response.status_code == 429 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return normalize_text(text).replace(" ・", "\n・")
            except (requests.RequestException, ValueError, KeyError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        raise ValueError(f"Gemini summarization failed: {last_error}")
