from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..db import session_scope
from ..services.reward_service import ensure_rewards
from ..services.user_service import get_or_create_user
from ..views.messages import welcome_message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    with session_scope() as session:
        db_user = get_or_create_user(session, user.id, user.full_name or user.username or "Stranger")
        ensure_rewards(session, db_user)
    await update.message.reply_text(welcome_message(user.first_name))
