from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bot.db import Base
from bot.models import Completion, Domain, Task, TaskStatus, User
from bot.services.analytics_service import overdue_count, xp_by_domain


def setup_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_overdue_and_domain_totals():
    engine = setup_db()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with SessionLocal() as session:
        user = User(telegram_id=1, name="Tester")
        domain = Domain(name="coding")
        session.add_all([user, domain])
        session.commit()
        task = Task(
            user_id=user.id,
            title="Task",
            time_horizon="short",
            energy="medium",
            priority="should",
            domain_id=domain.id,
            base_weight=2,
            due_at=datetime.utcnow() - timedelta(days=1),
            status=TaskStatus.ACTIVE,
        )
        session.add(task)
        session.commit()
        completion = Completion(task_id=task.id, xp_earned=5.0, completed_at=datetime.utcnow())
        session.add(completion)
        session.commit()
        domains = xp_by_domain(session, user.id, datetime.utcnow() - timedelta(days=7))
        assert domains["coding"] == pytest.approx(5.0)
        overdue = overdue_count(session, user.id, datetime.utcnow())
        assert overdue == 1
