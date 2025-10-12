from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def addcheck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Quick checks are not yet implemented. Use /add for now.")
