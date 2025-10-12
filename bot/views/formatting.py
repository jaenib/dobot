from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from humanize import naturaldelta

from ..models import EnergyLevel, Priority, Task, TimeHorizon

DOMAIN_EMOJI = {
    "coding": "🧩",
    "research": "📚",
    "admin": "🗂️",
    "creative": "🎨",
    "health": "💪",
    "recreation": "🎲",
}
PRIORITY_EMOJI = {
    Priority.MUST: "🔥",
    Priority.SHOULD: "⭐",
    Priority.NICE: "⛳",
}
ENERGY_EMOJI = {
    EnergyLevel.LOW: "🫧",
    EnergyLevel.MEDIUM: "⚙️",
    EnergyLevel.HIGH: "🔋",
}
HORIZON_LABELS = {
    TimeHorizon.NOW: "Now",
    TimeHorizon.SHORT: "Short",
    TimeHorizon.MID: "Mid",
    TimeHorizon.LONG: "Long",
}


def domain_badge(name: Optional[str]) -> str:
    if not name:
        return ""
    return f"{DOMAIN_EMOJI.get(name, '🧩')} {name.capitalize()}"


def priority_badge(priority: Priority) -> str:
    return f"{PRIORITY_EMOJI[priority]} {priority.value.upper()}"


def energy_badge(energy: EnergyLevel) -> str:
    return f"{ENERGY_EMOJI[energy]} {energy.value.capitalize()}"


def progress_bar(ratio: float, width: int = 10) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = int(round(ratio * width))
    return "▓" * filled + "░" * (width - filled)


def format_task_card(
    task: Task, projected_xp: Optional[float] = None, streak: Optional[int] = None
) -> str:
    lines = [f"{priority_badge(task.priority)} {task.title}"]
    details = [energy_badge(task.energy), HORIZON_LABELS[task.time_horizon]]
    if task.domain and task.domain.name:
        details.append(domain_badge(task.domain.name))
    lines.append(" | ".join(details))
    if task.due_at:
        delta = naturaldelta(task.due_at - datetime.utcnow())
        lines.append(f"Due: {task.due_at:%Y-%m-%d %H:%M} ({delta})")
    if projected_xp is not None:
        lines.append(f"Projected XP: {projected_xp:.2f}")
    if streak:
        lines.append(f"Streak: 🔁 x{streak}")
    return "\n".join(lines)


def bullet_list(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)
