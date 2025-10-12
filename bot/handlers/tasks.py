from __future__ import annotations

from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from ..db import session_scope
from ..models import EnergyLevel, Priority, TimeHorizon
from ..services import task_service
from ..services.analytics_service import recent_domain_totals
from ..views.formatting import format_task_card
from ..views.messages import level_up_message, task_summary

ASK_TITLE, ASK_DOMAIN = range(2)


async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Title?")
    return ASK_TITLE


async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["title"] = update.message.text.strip()
    await update.message.reply_text("Domain id (optional, leave blank)?")
    return ASK_DOMAIN


async def receive_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    domain_text = update.message.text.strip()
    domain_id = int(domain_text) if domain_text.isdigit() else None
    with session_scope() as session:
        user_id = update.effective_user.id
        task_service.create_task(
            session,
            user_id=user_id,
            title=context.user_data.get("title"),
            description=None,
            time_horizon=TimeHorizon.SHORT,
            energy=EnergyLevel.MEDIUM,
            priority=Priority.SHOULD,
            domain_id=domain_id,
            base_weight=2,
            recurrence=None,
            due_at=None,
        )
    context.user_data.clear()
    await update.message.reply_text("Task created.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reference = datetime.utcnow()
    with session_scope() as session:
        user_id = update.effective_user.id
        overdue = task_service.overdue_tasks(session, user_id, reference)
        due = task_service.tasks_due_today(session, user_id, reference)
        totals = recent_domain_totals(session, user_id, reference - timedelta(days=30))
        projected = {t.id: task_service.compute_task_projection(t, reference, totals) for t in overdue + due}
        text = task_summary(overdue + due, projected)
    await update.message.reply_text(text)


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /done <task_id>")
        return
    task_id = int(args[0])
    reference = datetime.utcnow()
    with session_scope() as session:
        user_id = update.effective_user.id
        task = task_service.get_task(session, user_id, task_id)
        if not task:
            await update.message.reply_text("Task not found.")
            return
        totals = recent_domain_totals(session, user_id, reference - timedelta(days=30))
        completion = task_service.complete_task(session, task, reference, totals)
        leveled_up = getattr(completion, "level_up", False)
        user_level = task.user.level
        next_threshold = getattr(completion, "next_threshold", 0)
    messages = [f"Done. Earned {completion.xp_earned:.2f} XP"]
    if leveled_up:
        messages.append(level_up_message(user_level, next_threshold))
    await update.message.reply_text("\n".join(messages))


async def backlog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with session_scope() as session:
        user_id = update.effective_user.id
        tasks = task_service.list_active_tasks(session, user_id)
        text = "\n\n".join(format_task_card(task) for task in tasks) or "No tasks in backlog."
    await update.message.reply_text(text)


conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("add", add_entry)],
    states={
        ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
        ASK_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_domain)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
