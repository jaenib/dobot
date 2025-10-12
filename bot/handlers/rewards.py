from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..db import session_scope
from ..services.reward_service import ensure_rewards, list_claimable
from ..services.user_service import get_or_create_user


async def rewards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    if not tg_user:
        return
    with session_scope() as session:
        user = get_or_create_user(session, tg_user.id, tg_user.full_name or tg_user.username or "User")
        ensure_rewards(session, user)
        rewards = list_claimable(session, user)
    lines = ["Rewards:"]
    for reward in rewards:
        status = "claimed" if reward.claimed_at else "available"
        lines.append(f"- {reward.title} ({reward.xp_cost} XP) — {status}")
    await update.message.reply_text("\n".join(lines))
