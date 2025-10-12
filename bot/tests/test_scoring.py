from datetime import datetime, timedelta

import pytest

from bot.models import EnergyLevel, Priority
from bot.scoring import clamp_xp, compute_task_xp


class DummyTask:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.streak = None


@pytest.fixture
def base_task():
    return DummyTask(
        base_weight=3,
        due_at=None,
        recurrence=None,
        energy=EnergyLevel.LOW,
        priority=Priority.NICE,
        domain_id=1,
        novelty_bonus=True,
    )


def test_overdue_bonus(base_task):
    reference = datetime.utcnow()
    base_task.due_at = reference - timedelta(days=4)
    breakdown = compute_task_xp(base_task, reference, streak=0, recent_domain_totals={1: 0}, first_completion=True)
    assert breakdown.total > base_task.base_weight


def test_daily_penalty(base_task):
    reference = datetime.utcnow()
    base_task.recurrence = "DAILY"
    breakdown = compute_task_xp(base_task, reference, streak=0, recent_domain_totals={}, first_completion=False)
    assert breakdown.total < base_task.base_weight


def test_clamp(base_task):
    assert clamp_xp(1, 0.1) >= 0.5
