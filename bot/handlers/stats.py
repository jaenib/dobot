from __future__ import annotations

from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from ..db import session_scope
from ..services.analytics_service import overdue_count, streak_summary, xp_by_domain
from ..views.messages import stats_overview


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    days = int(args[0].rstrip("d")) if args and args[0].endswith("d") else 30
    since = datetime.utcnow() - timedelta(days=days)
    with session_scope() as session:
        user_id = update.effective_user.id
        domains = xp_by_domain(session, user_id, since)
        overdue = overdue_count(session, user_id, datetime.utcnow())
        streaks = streak_summary(session, user_id)
    text = stats_overview(f"Stats for last {days}d", domains, overdue, streaks)
    await update.message.reply_text(text)
