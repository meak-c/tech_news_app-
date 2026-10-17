import pytest

from tech_news_app.config import Settings


def test_daily_budget_default_and_override(monkeypatch):
    monkeypatch.delenv("GEMINI_MAX_REQUESTS_PER_DAY", raising=False)
    assert Settings.from_env().gemini_max_requests_per_day == 20
    monkeypatch.setenv("GEMINI_MAX_REQUESTS_PER_DAY", "0")
    assert Settings.from_env().gemini_max_requests_per_day == 0


@pytest.mark.parametrize("value", ["-1", "invalid", "1.5"])
def test_daily_budget_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("GEMINI_MAX_REQUESTS_PER_DAY", value)
    with pytest.raises(ValueError):
        Settings.from_env()
