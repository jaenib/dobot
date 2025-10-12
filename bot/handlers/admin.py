from __future__ import annotations

import json
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from ..db import session_scope
from ..models import ALL_MODELS
from ..settings import get_settings


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    if update.effective_user.id != settings.owner_telegram_id:
        await update.message.reply_text("Not authorized.")
        return
    command = context.args[0] if context.args else "help"
    if command == "export":
        with session_scope() as session:
            data = {}
            for model in ALL_MODELS:
                rows = session.query(model).all()
                data[model.__tablename__] = [row_to_dict(row) for row in rows]
        await update.message.reply_document(document=json.dumps(data).encode(), filename="export.json")
    else:
        await update.message.reply_text("Available admin commands: export")


def row_to_dict(row) -> dict:
    return {col.key: getattr(row, col.key) for col in row.__table__.columns}
