from datetime import datetime, timedelta

from bot.scoring import update_streak


class StubTask:
    def __init__(self, recurrence: str | None = None):
        self.recurrence = recurrence
        self.streak = None


def test_daily_streak_continues():
    task = StubTask(recurrence="DAILY")
    current = datetime.utcnow()
    update_streak(task, current - timedelta(days=1))
    current_count, _ = update_streak(task, current)
    assert current_count == 2


def test_weekly_breaks():
    task = StubTask(recurrence="WEEKLY:MO")
    now = datetime.utcnow()
    update_streak(task, now - timedelta(days=7))
    current, _ = update_streak(task, now + timedelta(days=8))
    assert current == 1
