import sqlite3
from datetime import datetime

import pytest

from tech_news_app.budget import RequestBudget


def test_pacific_midnight_resets_budget(tmp_path):
    with sqlite3.connect(tmp_path / "test.sqlite") as connection:
        budget = RequestBudget(connection, 1)
        assert budget.try_acquire(datetime.fromisoformat("2026-07-01T06:59:59+00:00"))
        assert not budget.try_acquire(datetime.fromisoformat("2026-07-01T06:59:59+00:00"))
        assert budget.try_acquire(datetime.fromisoformat("2026-07-01T07:00:00+00:00"))
        assert not budget.try_acquire(datetime.fromisoformat("2026-07-01T23:59:59+00:00"))


def test_counter_survives_connection_restart_and_shared_limit(tmp_path):
    path = tmp_path / "test.sqlite"
    with sqlite3.connect(path) as connection:
        assert RequestBudget(connection, 1).try_acquire()
    with sqlite3.connect(path) as connection:
        assert not RequestBudget(connection, 1).try_acquire()


def test_negative_budget_is_rejected():
    with sqlite3.connect(":memory:") as connection, pytest.raises(ValueError):
        RequestBudget(connection, -1)


def test_pacific_winter_midnight_reset():
    with sqlite3.connect(":memory:") as connection:
        budget = RequestBudget(connection, 1)
        assert budget.try_acquire(datetime.fromisoformat("2026-12-01T07:59:59+00:00"))
        assert not budget.try_acquire(datetime.fromisoformat("2026-12-01T07:59:59+00:00"))
        assert budget.try_acquire(datetime.fromisoformat("2026-12-01T08:00:00+00:00"))
