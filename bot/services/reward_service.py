from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Reward, User

DEFAULT_REWARDS = [
    ("Take a creative break", 100),
    ("Buy a book", 200),
    ("Plan a day trip", 400),
]


def ensure_rewards(session: Session, user: User) -> None:
    existing_titles = {title for (title,) in session.execute(select(Reward.title).where(Reward.user_id == user.id))}
    for title, cost in DEFAULT_REWARDS:
        if title not in existing_titles:
            session.add(Reward(user=user, title=title, xp_cost=cost))


def list_claimable(session: Session, user: User) -> Sequence[Reward]:
    stmt = select(Reward).where(Reward.user_id == user.id).order_by(Reward.xp_cost)
    return session.scalars(stmt).all()


def claim_reward(session: Session, reward: Reward) -> Reward:
    reward.claimed_at = reward.claimed_at or datetime.utcnow()
    session.add(reward)
    return reward
