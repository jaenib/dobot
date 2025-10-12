from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import floor
from typing import Any, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo

LEVEL_BASE = 100
LEVEL_MULTIPLIER = 2


@dataclass
class LevelState:
    level: int
    xp_total: float
    next_threshold: float
    progress_ratio: float


def level_threshold(level: int) -> float:
    threshold = LEVEL_BASE * (LEVEL_MULTIPLIER ** (level - 1))
    return float(threshold)


def resolve_level(xp_total: float, current_level: int) -> LevelState:
    level = current_level
    threshold = level_threshold(level)
    while xp_total >= threshold:
        level += 1
        threshold = level_threshold(level)
    prev_threshold = level_threshold(level - 1) if level > 1 else 0
    span = threshold - prev_threshold
    progress = (xp_total - prev_threshold) / span if span else 0.0
    return LevelState(level=level, xp_total=xp_total, next_threshold=threshold, progress_ratio=progress)


def overdue_modifier(days_overdue: float) -> float:
    if days_overdue <= 0:
        return 0.0
    return min(0.5, 0.1 * days_overdue)


def recurrence_modifier(recurrence: Optional[str]) -> float:
    if not recurrence:
        return 0.0
    if recurrence == "daily":
        return -0.15
    if recurrence == "weekly":
        return -0.05
    return 0.0


def energy_modifier(energy: Optional[str]) -> float:
    if energy == "high":
        return 0.25
    if energy == "medium":
        return 0.1
    return 0.0


def priority_modifier(priority: Optional[str]) -> float:
    if priority == "must":
        return 0.3
    if priority == "should":
        return 0.1
    return 0.0


def streak_modifier(streak: int) -> float:
    if streak <= 0:
        return 0.0
    return min(0.3, 0.05 * floor(streak / 3))


def domain_balance_modifier(domain_xp: float, average_xp: float) -> float:
    if average_xp <= 0:
        return 0.0
    if domain_xp < average_xp * 0.8:
        return 0.2
    return 0.0


def calculate_xp(
    base_weight: float,
    *,
    days_overdue: float = 0.0,
    recurrence: Optional[str] = None,
    energy: Optional[str] = None,
    novelty_bonus: bool = False,
    has_prior_completion: bool = False,
    streak: int = 0,
    priority: Optional[str] = None,
    domain_xp: float = 0.0,
    average_xp: float = 0.0,
    weight_bias: float = 1.0,
) -> float:
    weight = max(0.5, base_weight) * max(0.2, weight_bias or 1.0)
    modifiers = 1.0
    modifiers += overdue_modifier(days_overdue)
    modifiers += recurrence_modifier(recurrence)
    modifiers += energy_modifier(energy)
    modifiers += priority_modifier(priority)
    modifiers += streak_modifier(streak)
    modifiers += domain_balance_modifier(domain_xp, average_xp)
    if novelty_bonus and not has_prior_completion:
        modifiers += 0.2
    xp = weight * modifiers
    return max(0.3, round(xp, 2))


def parse_weekdays(values: Sequence[str]) -> Sequence[int]:
    mapping = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
    return tuple(mapping[v] for v in values if v in mapping)


def is_due_today(task: Mapping[str, Any], now: datetime) -> bool:
    due_at = task.get("due_at")
    if due_at:
        try:
            due_dt = datetime.fromisoformat(due_at)
            if due_dt.date() == now.date():
                return True
        except ValueError:
            pass
    recurrence = task.get("recurrence")
    if recurrence == "daily":
        return True
    if recurrence == "weekly":
        if due_at:
            try:
                due_dt = datetime.fromisoformat(due_at)
                return due_dt.weekday() == now.weekday()
            except ValueError:
                return now.weekday() == 0
        return now.weekday() == 0
    if recurrence and recurrence.startswith("custom:"):
        weekdays = parse_weekdays([p.strip() for p in recurrence.split(":", 1)[1].split(",") if p.strip()])
        return now.weekday() in weekdays
    return False


def next_due(task: Mapping[str, Any], completed_at: datetime) -> Optional[str]:
    recurrence = task.get("recurrence")
    due_at = task.get("due_at")
    anchor = completed_at
    if due_at:
        try:
            anchor = datetime.fromisoformat(due_at)
        except ValueError:
            anchor = completed_at
    if recurrence == "daily":
        return (anchor + timedelta(days=1)).isoformat()
    if recurrence == "weekly":
        return (anchor + timedelta(days=7)).isoformat()
    if recurrence and recurrence.startswith("custom:"):
        weekdays = list(parse_weekdays([p.strip() for p in recurrence.split(":", 1)[1].split(",") if p.strip()]))
        if not weekdays:
            return None
        weekdays.sort()
        current = completed_at.weekday()
        for offset in range(1, 8):
            candidate = completed_at + timedelta(days=offset)
            if candidate.weekday() in weekdays:
                return candidate.isoformat()
    return None


def update_streak(
    current: int,
    longest: int,
    last_completed_at: Optional[str],
    recurrence: Optional[str],
    completed_at: datetime,
) -> tuple[int, int]:
    last_dt: Optional[datetime] = None
    if last_completed_at:
        try:
            last_dt = datetime.fromisoformat(last_completed_at)
        except ValueError:
            last_dt = None
    if not last_dt:
        current = 1
    else:
        delta = completed_at - last_dt
        if recurrence == "daily":
            if completed_at.date() == last_dt.date():
                return current, longest
            if delta <= timedelta(days=1, hours=6):
                current += 1
            else:
                current = 1
        elif recurrence == "weekly":
            last_week = last_dt.isocalendar()[:2]
            this_week = completed_at.isocalendar()[:2]
            if this_week == last_week:
                return current, longest
            week_diff = (completed_at.isocalendar()[0] * 53 + completed_at.isocalendar()[1]) - (
                last_dt.isocalendar()[0] * 53 + last_dt.isocalendar()[1]
            )
            if week_diff <= 1:
                current += 1
            else:
                current = 1
        else:
            if delta.days == 0:
                return current, longest
            if delta <= timedelta(days=2):
                current += 1
            else:
                current = 1
    longest = max(longest, current)
    return current, longest


def ensure_tz(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except Exception:
        return ZoneInfo("Europe/Zurich")


def local_now(tz_name: str) -> datetime:
    tz = ensure_tz(tz_name)
    return datetime.now(tz)
