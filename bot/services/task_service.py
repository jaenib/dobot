from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Sequence

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from ..models import Completion, SubTask, Task, TaskStatus
from ..scoring import XPBreakdown, compute_task_xp, level_for_xp, update_streak


def list_active_tasks(session: Session, user_id: int, limit: int = 20, page: int = 1) -> Sequence[Task]:
    stmt = (
        select(Task)
        .where(Task.user_id == user_id, Task.status == TaskStatus.ACTIVE)
        .order_by(Task.due_at.is_(None), Task.due_at, Task.created_at)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return session.scalars(stmt).all()


def get_task(session: Session, user_id: int, task_id: int) -> Task | None:
    stmt = select(Task).where(Task.user_id == user_id, Task.id == task_id)
    return session.scalars(stmt).first()


def create_task(session: Session, user_id: int, **kwargs) -> Task:
    task = Task(user_id=user_id, **kwargs)
    session.add(task)
    session.flush()
    return task


def complete_task(session: Session, task: Task, reference: datetime, recent_domain_totals: dict[int, float]) -> Completion:
    first_completion = len(task.completions) == 0
    streak_value = task.streak.current_streak if task.streak else 0
    breakdown = compute_task_xp(task, reference, streak_value, recent_domain_totals, first_completion=first_completion)
    completion = Completion(task=task, xp_earned=breakdown.total, completed_at=reference)
    session.add(completion)
    current, _ = update_streak(task, reference)
    completion.streak_after = current
    task.status = TaskStatus.ARCHIVED if not task.recurrence else TaskStatus.ACTIVE
    user = task.user
    user.xp_total += breakdown.total
    new_level, next_threshold = level_for_xp(user.xp_total, user.level)
    completion.level_up = new_level > user.level  # type: ignore[attr-defined]
    completion.next_threshold = next_threshold  # type: ignore[attr-defined]
    user.level = new_level
    session.add_all([task, user])
    return completion


def toggle_subtask(session: Session, subtask: SubTask, done: bool, timestamp: datetime) -> SubTask:
    subtask.done = done
    subtask.done_at = timestamp if done else None
    session.add(subtask)
    return subtask


def ensure_subtasks_completion(session: Session, task: Task, timestamp: datetime) -> None:
    if all(sub.done for sub in task.subtasks) and task.status == TaskStatus.ACTIVE:
        complete_task(session, task, timestamp, recent_domain_totals={})


def add_subtask(session: Session, task: Task, title: str, order_idx: int | None = None) -> SubTask:
    order = order_idx if order_idx is not None else (max((s.order_idx for s in task.subtasks), default=0) + 1)
    subtask = SubTask(task=task, title=title, order_idx=order)
    session.add(subtask)
    return subtask


def overdue_tasks(session: Session, user_id: int, reference: datetime) -> Sequence[Task]:
    stmt = select(Task).where(
        Task.user_id == user_id,
        Task.status == TaskStatus.ACTIVE,
        Task.due_at.is_not(None),
        Task.due_at < reference,
    )
    return session.scalars(stmt).all()


def tasks_due_today(session: Session, user_id: int, reference: datetime) -> Sequence[Task]:
    stmt = select(Task).where(
        Task.user_id == user_id,
        Task.status == TaskStatus.ACTIVE,
        Task.due_at.is_not(None),
        Task.due_at.between(reference.replace(hour=0, minute=0, second=0, microsecond=0), reference.replace(hour=23, minute=59, second=59, microsecond=999999)),
    )
    return session.scalars(stmt).all()


def neglected_domains(session: Session, user_id: int, recent_domain_totals: dict[int, float]) -> list[int]:
    if not recent_domain_totals:
        return []
    avg = sum(recent_domain_totals.values()) / len(recent_domain_totals)
    threshold = avg * 0.8
    return [domain_id for domain_id, total in recent_domain_totals.items() if total < threshold]


def compute_task_projection(task: Task, reference: datetime, recent_domain_totals: dict[int, float]) -> XPBreakdown:
    streak_value = task.streak.current_streak if task.streak else 0
    return compute_task_xp(task, reference, streak_value, recent_domain_totals, first_completion=False)


