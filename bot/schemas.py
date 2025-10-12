from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .models import EnergyLevel, Priority, TimeHorizon


@dataclass
class TaskCreate:
    title: str
    description: Optional[str]
    time_horizon: TimeHorizon
    energy: EnergyLevel
    priority: Priority
    domain_id: Optional[int]
    base_weight: int
    recurrence: Optional[str]
    due_at: Optional[datetime]
    novelty_bonus: bool = False


@dataclass
class SubTaskToggle:
    subtask_id: int
    done: bool
