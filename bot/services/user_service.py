from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Domain, Setting, User

DEFAULT_DOMAINS = [
    ("coding", 1.0),
    ("research", 1.0),
    ("admin", 1.0),
    ("creative", 1.0),
    ("health", 1.0),
    ("recreation", 1.0),
]


def get_or_create_user(session: Session, telegram_id: int, name: str) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    user = session.scalars(stmt).first()
    if user:
        return user
    user = User(telegram_id=telegram_id, name=name)
    session.add(user)
    session.flush()
    seed_domains(session)
    setting = Setting(user=user)
    session.add(setting)
    return user


def seed_domains(session: Session) -> None:
    existing = {name for (name,) in session.execute(select(Domain.name))}
    for name, weight in DEFAULT_DOMAINS:
        if name not in existing:
            session.add(Domain(name=name, weight_bias=weight))


def update_user_timezone(session: Session, user: User, timezone: str) -> None:
    user.tz = timezone
    session.add(user)


def set_setting(session: Session, user: User, key: str, value: str) -> None:
    if not user.setting:
        user.setting = Setting(user=user)
    data = user.setting.data
    import json

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        payload = {}
    payload[key] = value
    user.setting.data = json.dumps(payload)
    session.add(user.setting)


User.setting = property(lambda self: next((s for s in self.__dict__.get("_sa_instance_state").committed_state.values() if isinstance(s, Setting)), None))  # type: ignore
