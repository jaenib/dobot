from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

from .keyboards import DOMAIN_ICONS, ENERGY_ICONS, PRIORITY_ICONS


def ascii_bar(ratio: float, width: int = 10) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = int(round(ratio * width))
    return '#' * filled + '.' * (width - filled)


def _domain_label(name: Optional[str]) -> str:
    if not name:
        return "unsorted"
    icon = DOMAIN_ICONS.get(name, "")
    return f"{icon} {name}".strip()


def _priority_label(priority: Optional[str]) -> str:
    return PRIORITY_ICONS.get(priority or "", priority or "")


def _energy_label(energy: Optional[str]) -> str:
    return ENERGY_ICONS.get(energy or "", energy or "")


def format_task_card(task: dict, *, projected_xp: Optional[float] = None, streak: Optional[int] = None) -> str:
    lines = []
    priority = _priority_label(task.get("priority"))
    title = task.get("title", "(untitled)")
    lines.append(f"{priority} {title}")
    domain = _domain_label(task.get("domain_name"))
    energy = _energy_label(task.get("energy"))
    horizon = task.get("time_horizon", "")
    lines.append(f"Domain: {domain} | Energy: {energy} | Horizon: {horizon}")
    due_at = task.get("due_at")
    if due_at:
        try:
            due_dt = datetime.fromisoformat(due_at)
            lines.append(f"Due: {due_dt.strftime('%Y-%m-%d %H:%M')}")
        except ValueError:
            lines.append(f"Due: {due_at}")
    else:
        lines.append("Due: unset")
    if projected_xp is not None:
        lines.append(f"Projected XP: {projected_xp:.2f}")
    if streak:
        lines.append(f"Streak: x{streak}")
    return "\n".join(lines)


def render_task_list(tasks: Sequence[dict], page: int, total_pages: int) -> str:
    if not tasks:
        return "No tasks on this page."
    header = f"Tasks page {page + 1}/{total_pages}"
    body = "\n\n".join(format_task_card(task, projected_xp=None) for task in tasks)
    return f"{header}\n\n{body}"


def render_today(overdue: Sequence[dict], due: Sequence[dict], picks: Sequence[dict]) -> str:
    parts: List[str] = []
    if overdue:
        parts.append("Overdue:")
        parts.extend(f"- {t['title']} (due {t.get('due_at','?')})" for t in overdue)
    if due:
        parts.append("Due Today:")
        parts.extend(f"- {t['title']}" for t in due)
    if picks:
        parts.append("Balance Picks:")
        parts.extend(f"- {t['title']}" for t in picks)
    if not parts:
        return "You are clear for today."
    return "\n".join(parts)


def render_stats(snapshot: dict, days: int) -> str:
    lines = [f"Stats for last {days} days"]
    domains = snapshot.get("domains", [])
    if domains:
        lines.append("XP by domain:")
        for row in domains:
            xp = float(row["xp"] or 0)
            name = row["domain"]
            bar = ascii_bar(min(1.0, xp / max(1.0, domains[0]["xp"] or 1.0)))
            lines.append(f"  {name:12} {xp:6.1f} {bar}")
    horizons = snapshot.get("horizons", [])
    if horizons:
        lines.append("Horizon mix:")
        total = sum(row["cnt"] for row in horizons) or 1
        for row in horizons:
            ratio = row["cnt"] / total
            bar = ascii_bar(ratio)
            lines.append(f"  {row['time_horizon']:7} {row['cnt']:3d} {bar}")
    lines.append(f"Overdue active tasks: {snapshot.get('overdue', 0)}")
    lines.append(f"Completions: {snapshot.get('completions', 0)}")
    return "\n".join(lines)


def render_level(state, xp_total: float) -> str:
    bar = ascii_bar(state.progress_ratio)
    lines = [f"Level {state.level}"]
    lines.append(f"Total XP: {xp_total:.1f}")
    lines.append(f"Next threshold: {state.next_threshold:.1f}")
    lines.append(f"Progress: {bar}")
    return "\n".join(lines)


def render_streaks(best: Sequence[dict], weakest: Sequence[dict], risk: Sequence[dict]) -> str:
    lines: List[str] = []
    if best:
        lines.append("Strongest streaks:")
        lines.extend(f"- {row['title']} x{row['current_streak']}" for row in best)
    if weakest:
        lines.append("Weakest streaks:")
        lines.extend(f"- {row['title']} x{row['current_streak']}" for row in weakest)
    if risk:
        lines.append("At risk:")
        lines.extend(f"- {row['title']} last {row['last_completed_at']}" for row in risk)
    if not lines:
        return "No streak data yet."
    return "\n".join(lines)


def render_rewards(rewards: Sequence[dict]) -> str:
    if not rewards:
        return "No rewards configured yet."
    lines = ["Rewards:"]
    for reward in rewards:
        status = "claimed" if reward.get("claimed_at") else "open"
        lines.append(
            f"- {reward['title']} (cost {reward['xp_cost']:.1f}, level {reward['level_req']}) [{status}]"
        )
    return "\n".join(lines)
