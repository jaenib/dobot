from datetime import datetime

from bot.recurrence import is_due_today, parse_recurrence


def test_parse_weekly():
    info = parse_recurrence("WEEKLY:MO,WE")
    assert info["type"] == "WEEKLY"
    assert "MO" in info["byweekday"]


def test_is_due_daily_without_due_at():
    now = datetime(2024, 1, 10, 8, 0, 0)
    assert is_due_today("DAILY", None, now)
