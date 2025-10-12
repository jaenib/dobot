from __future__ import annotations

import enum
from datetime import datetime

from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class TimeHorizon(str, enum.Enum):
    NOW = "now"
    SHORT = "short"
    MID = "mid"
    LONG = "long"


class EnergyLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(str, enum.Enum):
    MUST = "must"
    SHOULD = "should"
    NICE = "nice"


class TaskStatus(str, enum.Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    ARCHIVED = "archived"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    tz: Mapped[str] = mapped_column(String(64), default="Europe/Zurich")
    xp_total: Mapped[float] = mapped_column(Float, default=0.0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    rewards: Mapped[List["Reward"]] = relationship("Reward", back_populates="user", cascade="all, delete-orphan")
    setting: Mapped[Optional["Setting"]] = relationship(
        "Setting", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    weight_bias: Mapped[float] = mapped_column(Float, default=1.0)


    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="domain")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_due_status", "due_at", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_horizon: Mapped[TimeHorizon] = mapped_column(Enum(TimeHorizon), default=TimeHorizon.SHORT)
    energy: Mapped[EnergyLevel] = mapped_column(Enum(EnergyLevel), default=EnergyLevel.MEDIUM)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.SHOULD)
    domain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("domains.id"), nullable=True)
    base_weight: Mapped[int] = mapped_column(Integer, default=1)
    recurrence: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.ACTIVE)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    novelty_bonus: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="tasks")
    domain: Mapped[Optional["Domain"]] = relationship("Domain", back_populates="tasks")
    subtasks: Mapped[List["SubTask"]] = relationship("SubTask", back_populates="task", cascade="all, delete-orphan")
    completions: Mapped[List["Completion"]] = relationship("Completion", back_populates="task", cascade="all, delete-orphan")
    streak: Mapped[Optional["Streak"]] = relationship(
        "Streak", back_populates="task", uselist=False, cascade="all, delete-orphan"
    )


class SubTask(Base):
    __tablename__ = "subtasks"
    __table_args__ = (
        UniqueConstraint("task_id", "order_idx", name="uq_subtask_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    order_idx: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="subtasks")


class Completion(Base):
    __tablename__ = "completions"
    __table_args__ = (
        Index("ix_completion_task_time", "task_id", "completed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    xp_earned: Mapped[float] = mapped_column(Float, default=0.0)
    streak_after: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped["Task"] = relationship("Task", back_populates="completions")


class Streak(Base):
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), unique=True)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="streak")


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    xp_cost: Mapped[int] = mapped_column(Integer, default=0)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="rewards")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    data: Mapped[str] = mapped_column(Text, default="{}")

    user: Mapped["User"] = relationship("User", back_populates="setting")


# convenience list
ALL_MODELS = [User, Domain, Task, SubTask, Completion, Streak, Reward, Setting]
