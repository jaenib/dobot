from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import floor
from typing import Iterable

from .models import EnergyLevel, Priority, Streak, Task


class _TransientStreak:
    def __init__(self) -> None:
        self.current_streak = 0
        self.longest_streak = 0
        self.last_completed_at = None

# Configurable constants
DOMAIN_NEGLECT_LOOKBACK_DAYS = 30
STREAK_BONUS_STEP = 3
STREAK_BONUS_VALUE = 0.05
STREAK_BONUS_CAP = 0.3
NOVELTY_BONUS_VALUE = 0.2
PRIORITY_BONUSES = {
    Priority.MUST: 0.3,
    Priority.SHOULD: 0.1,
    Priority.NICE: 0.0,
}
ENERGY_BONUSES = {
    EnergyLevel.LOW: 0.0,
    EnergyLevel.MEDIUM: 0.1,
    EnergyLevel.HIGH: 0.25,
}
DAILY_RECUR_PENALTY = -0.15
WEEKLY_RECUR_PENALTY = -0.05
MIN_XP_FRACTION = 0.5
MIN_XP_FLAT = 0.3
OVERDUE_DAILY_INCREASE = 0.1
OVERDUE_CAP = 0.5
LEVEL_BASE = 100


@dataclass
class XPBreakdown:
    base: float
    multipliers: dict[str, float]
    total: float


def compute_overdue_multiplier(due_at: datetime | None, reference: datetime) -> float:
    if due_at is None or due_at >= reference:
        return 0.0
    overdue_days = (reference - due_at).days or 1
    bonus = min(OVERDUE_CAP, overdue_days * OVERDUE_DAILY_INCREASE)
    return bonus


def compute_recurrence_multiplier(recurrence: str | None) -> float:
    if not recurrence:
        return 0.0
    if recurrence.upper().startswith("DAILY"):
        return DAILY_RECUR_PENALTY
    if recurrence.upper().startswith("WEEKLY"):
        return WEEKLY_RECUR_PENALTY
    return 0.0


def compute_streak_multiplier(streak: int) -> float:
    steps = floor(streak / STREAK_BONUS_STEP)
    return min(STREAK_BONUS_CAP, steps * STREAK_BONUS_VALUE)


def compute_domain_balance_multiplier(domain_id: int | None, recent_domain_totals: dict[int, float]) -> float:
    if domain_id is None or not recent_domain_totals:
        return 0.0
    average = sum(recent_domain_totals.values()) / len(recent_domain_totals)
    domain_total = recent_domain_totals.get(domain_id, 0.0)
    threshold = average * 0.8
    if domain_total < threshold:
        return 0.2
    return 0.0


def clamp_xp(base: int, xp: float) -> float:
    minimum = max(MIN_XP_FLAT, base * MIN_XP_FRACTION)
    return max(minimum, round(xp, 2))


def compute_task_xp(
    task: Task,
    reference: datetime,
    streak: int,
    recent_domain_totals: dict[int, float],
    first_completion: bool = False,
) -> XPBreakdown:
    multipliers: dict[str, float] = {}
    multipliers["overdue"] = compute_overdue_multiplier(task.due_at, reference)
    multipliers["recurrence"] = compute_recurrence_multiplier(task.recurrence)
    multipliers["energy"] = ENERGY_BONUSES[task.energy]
    multipliers["priority"] = PRIORITY_BONUSES[task.priority]
    multipliers["streak"] = compute_streak_multiplier(streak)
    multipliers["domain_balance"] = compute_domain_balance_multiplier(task.domain_id, recent_domain_totals)
    if first_completion and task.novelty_bonus:
        multipliers["novelty"] = NOVELTY_BONUS_VALUE
    else:
        multipliers["novelty"] = 0.0

    total_multiplier = 1 + sum(multipliers.values())
    xp_raw = task.base_weight * total_multiplier
    xp = clamp_xp(task.base_weight, xp_raw)
    return XPBreakdown(base=task.base_weight, multipliers=multipliers, total=xp)


def xp_for_level(level: int) -> int:
    return LEVEL_BASE * (2 ** (level - 1))


def level_for_xp(total_xp: float, current_level: int) -> tuple[int, float]:
    level = current_level
    next_threshold = xp_for_level(level)
    while total_xp >= next_threshold:
        level += 1
        next_threshold = xp_for_level(level)
    return level, next_threshold


def apply_completion(task: Task, xp: float, completed_at: datetime) -> None:
    completion = TaskCompletion(task=task, xp=xp, completed_at=completed_at)
    return completion


class TaskCompletion:
    def __init__(self, task: Task, xp: float, completed_at: datetime) -> None:
        self.task = task
        self.xp = xp
        self.completed_at = completed_at


def within_daily_window(last_completed_at: datetime | None, completed_at: datetime) -> bool:
    if last_completed_at is None:
        return False
    return abs((completed_at - last_completed_at).total_seconds()) <= 30 * 60 * 60


def within_weekly_window(last_completed_at: datetime | None, completed_at: datetime) -> bool:
    if last_completed_at is None:
        return False
    last_iso = last_completed_at.isocalendar()
    current_iso = completed_at.isocalendar()
    return last_iso[:2] == current_iso[:2]


def update_streak(task: Task, completed_at: datetime) -> tuple[int, int]:
    if task.streak is None:
        if isinstance(task, Task):
            task.streak = Streak(task=task, current_streak=0, longest_streak=0)
        else:
            task.streak = _TransientStreak()
    streak = task.streak
    current = streak.current_streak or 0
    longest = streak.longest_streak or 0
    previous = streak.last_completed_at

    recurrence = (task.recurrence or "").upper()
    continued = False
    if recurrence.startswith("DAILY"):
        continued = within_daily_window(previous, completed_at)
    elif recurrence.startswith("WEEKLY"):
        continued = within_weekly_window(previous, completed_at)

    if continued:
        current += 1
    else:
        current = 1

    streak.current_streak = current
    streak.longest_streak = max(longest, current)
    streak.last_completed_at = completed_at
    return current, streak.longest_streak
