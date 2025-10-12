from __future__ import annotations

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..db import session_scope
from ..models import User
from ..services.analytics_service import recent_domain_totals
from ..services.reminder_service import build_daily_digest


class Scheduler:
    def __init__(self, timezone: str) -> None:
        self.scheduler = AsyncIOScheduler(timezone=timezone)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def schedule_daily_digest(self, application, hour: int = 8) -> None:
        self.scheduler.add_job(self._send_daily_digest, CronTrigger(hour=hour, minute=0), args=[application])

    def schedule_weekly_review(self, application, hour: int = 18, day_of_week: str = "sun") -> None:
        self.scheduler.add_job(
            self._send_weekly_review,
            CronTrigger(day_of_week=day_of_week, hour=hour, minute=0),
            args=[application],
        )

    def _send_daily_digest(self, application) -> None:
        with session_scope() as session:
            users = session.query(User).all()
            for user in users:
                text = build_daily_digest(session, user.id, datetime.utcnow())
                application.create_task(application.bot.send_message(chat_id=user.telegram_id, text=text))

    def _send_weekly_review(self, application) -> None:
        with session_scope() as session:
            users = session.query(User).all()
            for user in users:
                totals = recent_domain_totals(session, user.id, datetime.utcnow() - timedelta(days=7))
                lines = [f"Weekly XP for {user.name}:"]
                for domain_id, xp in totals.items():
                    lines.append(f"- Domain {domain_id}: {xp:.1f} XP")
                application.create_task(application.bot.send_message(chat_id=user.telegram_id, text="\n".join(lines)))


def create_scheduler(timezone: str) -> Scheduler:
    return Scheduler(timezone=timezone)
