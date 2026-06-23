from tech_news_app.models import Importance
from tech_news_app.parser import classify_importance


def test_breaking_change_is_high() -> None:
    assert classify_importance("Breaking change in CLI authentication") == Importance.HIGH


def test_bug_fix_is_low() -> None:
    assert classify_importance("Bug fix for command output") == Importance.LOW


def test_unknown_is_medium() -> None:
    assert classify_importance("Updated behavior") == Importance.MEDIUM
