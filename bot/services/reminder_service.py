from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Tuple

from sqlalchemy.orm import Session

from ..models import Task, TaskStatus
from ..recurrence import is_due_today
from ..views.messages import today_digest


def build_daily_digest(session: Session, user_id: int, reference: datetime) -> str:
    overdue = []
    due_today = []
    balance = []
    tasks = session.query(Task).filter(Task.user_id == user_id).all()
    for task in tasks:
        if task.status != TaskStatus.ACTIVE:
            continue
        if task.due_at and task.due_at < reference:
            overdue.append(task.title)
        elif is_due_today(task.recurrence, task.due_at, reference):
            due_today.append(task.title)
    if tasks:
        user = tasks[0].user
        level = user.level
        xp_progress = (user.xp_total, 100.0)
    else:
        level = 1
        xp_progress = (0.0, 100.0)
    return today_digest(overdue[:3], due_today[:5], balance[:3], level, xp_progress)
