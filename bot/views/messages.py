from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Tuple

from ..models import Task
from ..scoring import XPBreakdown
from .formatting import bullet_list, format_task_card, progress_bar


def welcome_message(name: str) -> str:
    return (
        f"Welcome, {name}!\n"
        "Use /add to capture a task, /today for a daily brief, and /stats for analytics."
    )


def level_up_message(level: int, next_threshold: float) -> str:
    return (
        f"Level up! You reached Level {level}.\n"
        f"Next threshold: {next_threshold:.0f} XP. Consider claiming a reward with /rewards."
    )


def task_summary(tasks: Iterable[Task], projected: Dict[int, XPBreakdown]) -> str:
    rendered = [format_task_card(task, projected.get(task.id, XPBreakdown(0, {}, 0)).total) for task in tasks]
    return bullet_list(rendered) if rendered else "No tasks found."


def today_digest(
    overdue: List[str],
    due_today: List[str],
    balance: List[str],
    level: int,
    xp_progress: Tuple[float, float],
) -> str:
    current_xp, next_threshold = xp_progress
    parts = ["Today's Focus:"]
    if overdue:
        parts.append("Overdue:")
        parts.extend(f"  {item}" for item in overdue)
    if due_today:
        parts.append("Due Today:")
        parts.extend(f"  {item}" for item in due_today)
    if balance:
        parts.append("Balance Picks:")
        parts.extend(f"  {item}" for item in balance)
    parts.append(f"Level {level} — {current_xp:.0f}/{next_threshold:.0f} XP")
    return "\n".join(parts)


def stats_overview(header: str, by_domain: Dict[str, float], overdue_count: int, streaks: Dict[str, int]) -> str:
    lines = [header, "By domain:"]
    for domain, xp in by_domain.items():
        lines.append(f"- {domain}: {xp:.1f} XP")
    lines.append(f"Overdue tasks: {overdue_count}")
    if streaks:
        lines.append("Streaks:")
        for name, value in streaks.items():
            lines.append(f"  {name}: {value}")
    return "\n".join(lines)
