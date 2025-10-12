from __future__ import annotations

from datetime import datetime
from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Completion, Domain, Streak, Task, TaskStatus


def xp_by_domain(session: Session, user_id: int, since: datetime) -> Dict[str, float]:
    stmt = (
        select(Domain.name, func.sum(Completion.xp_earned))
        .join(Task, Task.domain_id == Domain.id)
        .join(Completion, Completion.task_id == Task.id)
        .where(Task.user_id == user_id, Completion.completed_at >= since)
        .group_by(Domain.name)
    )
    return {name: xp or 0.0 for name, xp in session.execute(stmt)}


def recent_domain_totals(session: Session, user_id: int, since: datetime) -> Dict[int, float]:
    stmt = (
        select(Task.domain_id, func.sum(Completion.xp_earned))
        .join(Completion, Completion.task_id == Task.id)
        .where(Task.user_id == user_id, Completion.completed_at >= since)
        .group_by(Task.domain_id)
    )
    return {domain_id: xp or 0.0 for domain_id, xp in session.execute(stmt) if domain_id is not None}


def overdue_count(session: Session, user_id: int, reference: datetime) -> int:
    stmt = select(func.count()).select_from(Task).where(
        Task.user_id == user_id,
        Task.due_at.is_not(None),
        Task.due_at < reference,
        Task.status == TaskStatus.ACTIVE,
    )
    return session.scalar(stmt) or 0


def streak_summary(session: Session, user_id: int) -> Dict[str, int]:
    stmt = (
        select(Task.title, func.coalesce(Streak.current_streak, 0))
        .join(Streak, Streak.task_id == Task.id, isouter=True)
        .where(Task.user_id == user_id)
    )
    return {title: value for title, value in session.execute(stmt)}
