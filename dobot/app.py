from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from telegram import Bot, Update
from zoneinfo import ZoneInfo
from telegram.ext import (
    AIORateLimiter,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import db, keyboards, scoring, views

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

ADD_TITLE, ADD_DOMAIN, ADD_HORIZON, ADD_ENERGY, ADD_PRIORITY, ADD_WEIGHT, ADD_RECURRENCE, ADD_CUSTOM, ADD_DUE, ADD_CONFIRM = range(10)
ADD_CHECK_TITLE, ADD_CHECK_DOMAIN = range(2)


def load_env() -> str:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN missing")
    return token


async def run_db(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


async def ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[Dict[str, Any]]:
    if not update.effective_user:
        return None
    user = await run_db(db.get_user, update.effective_user.id)
    if user:
        return dict(user)
    await run_db(db.init_db)
    name = update.effective_user.full_name or "Unknown"
    user_row = await run_db(db.upsert_user, update.effective_user.id, name)
    return dict(user_row)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    await update.message.reply_text(
        "Welcome back. Use /help for the quick reference."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Commands:\n"
        "/add — create a task\n"
        "/addcheck — quick recurring check\n"
        "/list — list active tasks\n"
        "/today — daily focus\n"
        "/done <id> — finish a task\n"
        "/skip <id> — skip\n"
        "/snooze <id> <days> — postpone\n"
        "/stats — analytics\n"
        "/streaks — streak overview\n"
        "/level — progression\n"
        "/rewards — manage rewards\n"
        "/settings — timezone and digests"
    )
    await update.message.reply_text(text)


async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await ensure_user(update, context)
    context.user_data["add"] = {}
    await update.message.reply_text("Title?")
    return ADD_TITLE


async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.setdefault("add", {})["title"] = update.message.text.strip()
    domains = await run_db(db.list_domains)
    await update.message.reply_text(
        "Choose domain:", reply_markup=keyboards.domain_choice_keyboard([(d["id"], d["name"]) for d in domains])
    )
    return ADD_DOMAIN


async def add_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    domain_id = int(query.data.split(":")[1])
    context.user_data.setdefault("add", {})["domain_id"] = domain_id
    await query.edit_message_text("Time horizon?", reply_markup=keyboards.time_horizon_keyboard())
    return ADD_HORIZON


async def add_horizon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["add"]["time_horizon"] = query.data.split(":")[1]
    await query.edit_message_text("Energy level?", reply_markup=keyboards.energy_keyboard())
    return ADD_ENERGY


async def add_energy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["add"]["energy"] = query.data.split(":")[1]
    await query.edit_message_text("Priority?", reply_markup=keyboards.priority_keyboard())
    return ADD_PRIORITY


async def add_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["add"]["priority"] = query.data.split(":")[1]
    await query.edit_message_text("Base weight?", reply_markup=keyboards.weight_keyboard())
    return ADD_WEIGHT


async def add_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["add"]["base_weight"] = int(query.data.split(":")[1])
    await query.edit_message_text("Recurrence?", reply_markup=keyboards.recurrence_keyboard())
    return ADD_RECURRENCE


async def add_recurrence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    value = query.data.split(":")[1]
    if value == "none":
        context.user_data["add"]["recurrence"] = None
        await query.edit_message_text("Due date? (ISO date or skip)")
        return ADD_DUE
    if value == "custom":
        await query.edit_message_text("Enter weekdays like MO,TH")
        return ADD_CUSTOM
    context.user_data["add"]["recurrence"] = value
    await query.edit_message_text("Due date? (ISO date or skip)")
    return ADD_DUE


async def add_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["add"]["recurrence"] = f"custom:{text}"
    await update.message.reply_text("Due date? (ISO date or skip)")
    return ADD_DUE


def parse_due(text: str, tz_name: str) -> Optional[str]:
    if text.lower() in {"skip", "none", ""}:
        return None
    tz = scoring.ensure_tz(tz_name)
    try:
        if "T" in text:
            dt = datetime.fromisoformat(text)
        else:
            dt = datetime.fromisoformat(text + "T09:00")
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(ZoneInfo("UTC")).isoformat()


async def add_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await ensure_user(update, context)
    due = parse_due(update.message.text.strip(), user.get("tz", "Europe/Zurich")) if user else None
    if due:
        context.user_data["add"]["due_at"] = due
    summary = context.user_data["add"].copy()
    summary.setdefault("domain_name", "")
    card = views.format_task_card(summary)
    await update.message.reply_text(card, reply_markup=keyboards.confirmation_keyboard())
    return ADD_CONFIRM


async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "add:cancel":
        context.user_data.pop("add", None)
        await query.edit_message_text("Cancelled")
        return ConversationHandler.END
    data = context.user_data.pop("add", {})
    user = await ensure_user(update, context)
    if not user:
        await query.edit_message_text("No user")
        return ConversationHandler.END
    task_data = {k: v for k, v in data.items() if v is not None}
    if "domain_id" not in task_data:
        task_data["domain_id"] = None
    task_id = await run_db(db.create_task, user["id"], task_data)
    await query.edit_message_text(f"Task {task_id} saved")
    return ConversationHandler.END


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("add", None)
    await update.message.reply_text("Cancelled")
    return ConversationHandler.END


async def start_addcheck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await ensure_user(update, context)
    context.user_data["check"] = {"base_weight": 1, "recurrence": "weekly"}
    await update.message.reply_text("Title for the check?")
    return ADD_CHECK_TITLE


async def addcheck_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["check"]["title"] = update.message.text.strip()
    domains = await run_db(db.list_domains)
    await update.message.reply_text(
        "Domain?", reply_markup=keyboards.domain_choice_keyboard([(d["id"], d["name"]) for d in domains])
    )
    return ADD_CHECK_DOMAIN


async def addcheck_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    domain_id = int(query.data.split(":")[1])
    context.user_data["check"]["domain_id"] = domain_id
    user = await ensure_user(update, context)
    task_data = context.user_data.pop("check", {})
    task_id = await run_db(db.create_task, user["id"], task_data)
    await query.edit_message_text(f"Check {task_id} saved")
    return ConversationHandler.END


async def cmd_addsub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user or not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addsub <task_id> <title>")
        return
    task_id = int(context.args[0])
    title = " ".join(context.args[1:]).strip()
    task = await run_db(db.get_task, task_id)
    if not task or task["user_id"] != user["id"]:
        await update.message.reply_text("Task not found")
        return
    await run_db(db.add_subtask, task_id, title)
    await update.message.reply_text("Subtask added")




async def xp_inputs(user_id: int) -> tuple[dict[int, float], float]:
    snapshot = await run_db(db.domain_xp_snapshot, user_id, 30)
    domains = await run_db(db.list_domains)
    average = db.domain_average(snapshot, len(domains))
    return snapshot, average
async def compute_projected(task: Dict[str, Any], user_id: int, snapshot: dict[int, float], average: float) -> float:
    domain_xp = snapshot.get(task.get("domain_id") or 0, 0.0)
    count = await run_db(db.completion_count, task["id"])
    streak_row = await run_db(db.get_streak, task["id"])
    streak = streak_row["current_streak"] if streak_row else 0
    due_at = task.get("due_at")
    days_overdue = 0.0
    if due_at:
        try:
            due_dt = datetime.fromisoformat(due_at)
            delta = (datetime.utcnow() - due_dt).total_seconds() / 86400
            days_overdue = max(0.0, delta)
        except ValueError:
            pass
    xp = scoring.calculate_xp(
        task.get("base_weight", 1) * (task.get("weight_bias") or 1.0),
        days_overdue=days_overdue,
        recurrence=task.get("recurrence"),
        energy=task.get("energy"),
        novelty_bonus=bool(task.get("novelty_bonus")),
        has_prior_completion=count > 0,
        streak=streak,
        priority=task.get("priority"),
        domain_xp=domain_xp,
        average_xp=average,
        weight_bias=1.0,
    )
    return xp


async def list_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    page = max(0, page)
    per_page = 5
    tasks = await run_db(db.list_tasks, user["id"], "active", per_page, page * per_page)
    count = await run_db(db.count_tasks, user["id"], "active")
    total_pages = max(1, (count + per_page - 1) // per_page)
    rendered = []
    snapshot, average = await xp_inputs(user["id"])
    for task in tasks:
        projected = await compute_projected(dict(task), user["id"], snapshot, average)
        streak_row = await run_db(db.get_streak, task["id"])
        streak = streak_row["current_streak"] if streak_row else None
        rendered.append(views.format_task_card(dict(task), projected_xp=projected, streak=streak))
    text = f"Tasks page {page + 1}/{total_pages}\n\n" + "\n\n".join(rendered) if rendered else "No active tasks"
    reply_markup = keyboards.pagination_keyboard(page, total_pages)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await list_page(update, context, 0)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    now = datetime.utcnow().isoformat()
    overdue = await run_db(db.overdue_tasks, user["id"], now)
    due = await run_db(db.due_today_tasks, user["id"], now)
    snapshot = await run_db(db.domain_xp_snapshot, user["id"], 30)
    domains = await run_db(db.list_domains)
    if snapshot:
        weakest_domain = min(domains, key=lambda d: snapshot.get(d["id"], 0.0))
        picks = await run_db(db.neglected_candidates, user["id"], weakest_domain["id"], 3)
    else:
        picks = await run_db(db.neglected_candidates, user["id"], None, 3)
    text = views.render_today([dict(r) for r in overdue][:5], [dict(r) for r in due][:5], [dict(r) for r in picks][:5])
    await update.message.reply_text(text)


async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user or not context.args:
        await update.message.reply_text("Usage: /task <id>")
        return
    task_id = int(context.args[0])
    task = await run_db(db.get_task, task_id)
    if not task or task["user_id"] != user["id"]:
        await update.message.reply_text("Task not found")
        return
    snapshot, average = await xp_inputs(user["id"])
    projected = await compute_projected(dict(task), user["id"], snapshot, average)
    streak_row = await run_db(db.get_streak, task_id)
    streak = streak_row["current_streak"] if streak_row else None
    card = views.format_task_card(dict(task), projected_xp=projected, streak=streak)
    subtasks = await run_db(db.get_subtasks, task_id)
    if subtasks:
        card += "\n\nSubtasks:\n" + "\n".join(
            f"- [{'x' if st['done'] else ' '}] {st['title']}" for st in subtasks
        )
    await update.message.reply_text(card, reply_markup=keyboards.task_actions_keyboard(task_id))


async def complete_task(task: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    snapshot, average = await xp_inputs(user["id"])
    domain_xp = snapshot.get(task.get("domain_id") or 0, 0.0)
    count = await run_db(db.completion_count, task["id"])
    streak_row = await run_db(db.get_streak, task["id"])
    streak = streak_row["current_streak"] if streak_row else 0
    last_completed = streak_row["last_completed_at"] if streak_row else None
    due_at = task.get("due_at")
    days_overdue = 0.0
    if due_at:
        try:
            due_dt = datetime.fromisoformat(due_at)
            delta = (datetime.utcnow() - due_dt).total_seconds() / 86400
            days_overdue = max(0.0, delta)
        except ValueError:
            pass
    xp = scoring.calculate_xp(
        task.get("base_weight", 1) * (task.get("weight_bias") or 1.0),
        days_overdue=days_overdue,
        recurrence=task.get("recurrence"),
        energy=task.get("energy"),
        novelty_bonus=bool(task.get("novelty_bonus")),
        has_prior_completion=count > 0,
        streak=streak,
        priority=task.get("priority"),
        domain_xp=domain_xp,
        average_xp=average,
        weight_bias=1.0,
    )
    now = datetime.utcnow()
    if count:
        last = await run_db(db.last_completion, task["id"])
        if last:
            last_dt = datetime.fromisoformat(last["completed_at"])
            if last_dt.date() == now.date():
                return {"xp": 0.0, "level_up": False, "message": "Already completed today."}
    current = streak_row["current_streak"] if streak_row else 0
    longest = streak_row["longest_streak"] if streak_row else 0
    new_current, new_longest = scoring.update_streak(current, longest, last_completed, task.get("recurrence"), now)
    await run_db(db.save_streak, task["id"], new_current, new_longest, now.isoformat())
    await run_db(db.log_completion, task["id"], xp, now.isoformat(), new_current)
    total_xp = float(user.get("xp_total", 0.0)) + xp
    state = scoring.resolve_level(total_xp, int(user.get("level", 1)))
    update_fields = {"xp_total": total_xp}
    level_up = False
    if state.level != user.get("level"):
        level_up = True
        update_fields["level"] = state.level
    await run_db(db.update_user, user["id"], **update_fields)
    if task.get("recurrence"):
        next_due = scoring.next_due(task, now)
        if next_due:
            await run_db(db.update_task, task["id"], due_at=next_due)
    else:
        await run_db(db.update_task, task["id"], status="archived")
    return {"xp": xp, "level_up": level_up, "state": state}


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user or not context.args:
        await update.message.reply_text("Usage: /done <id>")
        return
    task_id = int(context.args[0])
    task = await run_db(db.get_task, task_id)
    if not task or task["user_id"] != user["id"]:
        await update.message.reply_text("Task not found")
        return
    result = await complete_task(dict(task), user)
    if result["xp"] == 0:
        await update.message.reply_text(result.get("message", "Already counted"))
        return
    msg = f"Gained {result['xp']:.2f} XP."
    if result.get("level_up"):
        state = result["state"]
        msg += f" Level up! Now level {state.level}."
    await update.message.reply_text(msg)


async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user or not context.args:
        await update.message.reply_text("Usage: /skip <id>")
        return
    task_id = int(context.args[0])
    task = await run_db(db.get_task, task_id)
    if not task or task["user_id"] != user["id"]:
        await update.message.reply_text("Task not found")
        return
    await run_db(db.update_task, task_id, due_at=None)
    streak_row = await run_db(db.get_streak, task_id)
    longest = streak_row["longest_streak"] if streak_row else 0
    await run_db(db.save_streak, task_id, 0, longest, None)
    await update.message.reply_text("Skipped for now")


async def cmd_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user or len(context.args) < 2:
        await update.message.reply_text("Usage: /snooze <id> <days>")
        return
    task_id = int(context.args[0])
    days = int(context.args[1])
    task = await run_db(db.get_task, task_id)
    if not task or task["user_id"] != user["id"]:
        await update.message.reply_text("Task not found")
        return
    due = task.get("due_at")
    base = datetime.utcnow()
    if due:
        try:
            base = datetime.fromisoformat(due)
        except ValueError:
            pass
    new_due = (base + timedelta(days=days)).isoformat()
    await run_db(db.update_task, task_id, due_at=new_due)
    await update.message.reply_text(f"Snoozed to {new_due}")


async def cmd_streaks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    best, weak, risk = await run_db(db.streak_overview, user["id"])
    text = views.render_streaks([dict(r) for r in best], [dict(r) for r in weak], [dict(r) for r in risk])
    await update.message.reply_text(text)


async def send_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    snapshot = await run_db(db.stats_snapshot, user["id"], days)
    text = views.render_stats(snapshot, days)
    markup = keyboards.stats_range_keyboard(days)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_stats(update, context, 7)


async def cmd_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    state = scoring.resolve_level(float(user.get("xp_total", 0.0)), int(user.get("level", 1)))
    text = views.render_level(state, float(user.get("xp_total", 0.0)))
    await update.message.reply_text(text)


async def cmd_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    if context.args and context.args[0] == "add":
        payload = " ".join(context.args[1:])
        parts = [p.strip() for p in payload.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Use: /rewards add title | xp | level")
            return
        title, xp_str, level_str = parts
        await run_db(db.create_reward, user["id"], title, float(xp_str), int(level_str))
        await update.message.reply_text("Reward stored")
        return
    if context.args and context.args[0] == "claim" and len(context.args) >= 2:
        reward_id = int(context.args[1])
        rewards = await run_db(db.list_rewards, user["id"])
        reward = next((r for r in rewards if r["id"] == reward_id), None)
        if not reward:
            await update.message.reply_text("Reward not found")
            return
        if reward["claimed_at"]:
            await update.message.reply_text("Already claimed")
            return
        if user["level"] < reward["level_req"] or user["xp_total"] < reward["xp_cost"]:
            await update.message.reply_text("Requirements not met")
            return
        await run_db(db.mark_reward_claimed, reward_id)
        await update.message.reply_text("Reward claimed")
        return
    rewards = await run_db(db.list_rewards, user["id"])
    text = views.render_rewards([dict(r) for r in rewards])
    await update.message.reply_text(text)


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await ensure_user(update, context)
    if not user:
        return
    if not context.args:
        await update.message.reply_text(
            f"Timezone: {user['tz']}\nDigest hour: {user['digest_hour']}\nNotifications: {'on' if user['notifications_enabled'] else 'off'}\n"
            "Set with /settings tz <name>, /settings hour <0-23>, /settings notify <on|off>"
        )
        return
    sub = context.args[0]
    if sub == "tz" and len(context.args) >= 2:
        tz = context.args[1]
        await run_db(db.update_user, user["id"], tz=tz)
        await update.message.reply_text(f"Timezone set to {tz}")
        return
    if sub == "hour" and len(context.args) >= 2:
        hour = max(0, min(23, int(context.args[1])))
        await run_db(db.update_user, user["id"], digest_hour=hour)
        await update.message.reply_text(f"Digest hour set to {hour}")
        return
    if sub == "notify" and len(context.args) >= 2:
        flag = context.args[1].lower() == "on"
        await run_db(db.update_user, user["id"], notifications_enabled=1 if flag else 0)
        await update.message.reply_text(f"Notifications {'enabled' if flag else 'disabled'}")
        return
    await update.message.reply_text("Unrecognised settings command")


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, _, value = query.data.split(":")
    await send_stats(update, context, int(value))


async def pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[2])
    await list_page(update, context, page)


async def task_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action = parts[1]
    task_id = int(parts[2])
    user = await ensure_user(update, context)
    if not user:
        return
    task = await run_db(db.get_task, task_id)
    if not task or task["user_id"] != user["id"]:
        await query.edit_message_text("Task not available")
        return
    if action == "done":
        result = await complete_task(dict(task), user)
        if result["xp"] == 0:
            await query.edit_message_text(result.get("message", "Already counted"))
            return
        msg = f"Gained {result['xp']:.2f} XP."
        if result.get("level_up"):
            state = result["state"]
            msg += f" Level up! Now level {state.level}."
        await query.edit_message_text(msg)
        return
    if action == "skip":
        await run_db(db.update_task, task_id, due_at=None)
        streak_row = await run_db(db.get_streak, task_id)
        longest = streak_row["longest_streak"] if streak_row else 0
        await run_db(db.save_streak, task_id, 0, longest, None)
        await query.edit_message_text("Skipped")
        return
    if action == "snooze":
        days = int(parts[3])
        due = task.get("due_at")
        base = datetime.utcnow()
        if due:
            try:
                base = datetime.fromisoformat(due)
            except ValueError:
                pass
        new_due = (base + timedelta(days=days)).isoformat()
        await run_db(db.update_task, task_id, due_at=new_due)
        await query.edit_message_text(f"Snoozed to {new_due}")
        return
    if action == "archive":
        await run_db(db.update_task, task_id, status="archived")
        await query.edit_message_text("Archived")
        return
    if action == "details":
        snapshot, average = await xp_inputs(user["id"])
        projected = await compute_projected(dict(task), user["id"], snapshot, average)
        streak_row = await run_db(db.get_streak, task_id)
        streak = streak_row["current_streak"] if streak_row else None
        card = views.format_task_card(dict(task), projected_xp=projected, streak=streak)
        subtasks = await run_db(db.get_subtasks, task_id)
        if subtasks:
            card += "\n\nSubtasks:\n" + "\n".join(
                f"- [{'x' if st['done'] else ' '}] {st['title']}" for st in subtasks
            )
        await query.edit_message_text(card)
        return
    if action == "sub":
        if parts[3] == "list":
            subtasks = await run_db(db.get_subtasks, task_id)
            if not subtasks:
                await query.edit_message_text("No subtasks yet")
                return
            data = [(st["id"], st["title"], bool(st["done"])) for st in subtasks]
            await query.edit_message_text(
                "Toggle subtasks:", reply_markup=keyboards.subtasks_keyboard(task_id, data)
            )
            return
        sub_id = int(parts[3])
        await run_db(db.toggle_subtask, sub_id)
        await query.edit_message_text("Toggled")
        return


async def digest_tick(bot: Bot) -> None:
    users = await run_db(db.list_users)
    now_utc = datetime.utcnow()
    for user in users:
        if not user["notifications_enabled"]:
            continue
        tz = scoring.ensure_tz(user["tz"])
        local_now = now_utc.astimezone(tz)
        if local_now.hour == user["digest_hour"] and local_now.minute < 5:
            last = user.get("last_daily_digest")
            if last == local_now.date().isoformat():
                continue
            chat_id = user["telegram_id"]
            overdue = await run_db(db.overdue_tasks, user["id"], now_utc.isoformat())
            due = await run_db(db.due_today_tasks, user["id"], now_utc.isoformat())
            picks = await run_db(db.neglected_candidates, user["id"], None, 3)
            text = views.render_today([dict(r) for r in overdue][:5], [dict(r) for r in due][:5], [dict(r) for r in picks][:5])
            await bot.send_message(chat_id, text)
            await run_db(db.update_user, user["id"], last_daily_digest=local_now.date().isoformat())
        if local_now.weekday() == 6 and local_now.hour == 18 and local_now.minute < 5:
            week_ref = f"{local_now.isocalendar()[0]}-{local_now.isocalendar()[1]}"
            if user.get("last_weekly_digest") == week_ref:
                continue
            chat_id = user["telegram_id"]
            snapshot = await run_db(db.stats_snapshot, user["id"], 7)
            text = "Weekly recap\n" + views.render_stats(snapshot, 7)
            await bot.send_message(chat_id, text)
            await run_db(db.update_user, user["id"], last_weekly_digest=week_ref)


async def digest_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await digest_tick(context.bot)
    except Exception as exc:
        log.exception("digest tick failed: %s", exc)


def build_application(token: str) -> Application:
    application = (
        Application.builder()
        .token(token)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", start_add)],
        states={
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_DOMAIN: [CallbackQueryHandler(add_domain, pattern="^domain:")],
            ADD_HORIZON: [CallbackQueryHandler(add_horizon, pattern="^horizon:")],
            ADD_ENERGY: [CallbackQueryHandler(add_energy, pattern="^energy:")],
            ADD_PRIORITY: [CallbackQueryHandler(add_priority, pattern="^priority:")],
            ADD_WEIGHT: [CallbackQueryHandler(add_weight, pattern="^weight:")],
            ADD_RECURRENCE: [CallbackQueryHandler(add_recurrence, pattern="^recur:")],
            ADD_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_custom)],
            ADD_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_due)],
            ADD_CONFIRM: [CallbackQueryHandler(add_confirm, pattern="^add:")],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
        allow_reentry=True,
    )
    check_conv = ConversationHandler(
        entry_points=[CommandHandler("addcheck", start_addcheck)],
        states={
            ADD_CHECK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcheck_title)],
            ADD_CHECK_DOMAIN: [CallbackQueryHandler(addcheck_domain, pattern="^domain:")],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )
    application.add_handler(add_conv)
    application.add_handler(check_conv)
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("addsub", cmd_addsub))
    application.add_handler(CommandHandler("list", cmd_list))
    application.add_handler(CommandHandler("today", cmd_today))
    application.add_handler(CommandHandler("task", cmd_task))
    application.add_handler(CommandHandler("done", cmd_done))
    application.add_handler(CommandHandler("skip", cmd_skip))
    application.add_handler(CommandHandler("snooze", cmd_snooze))
    application.add_handler(CommandHandler("streaks", cmd_streaks))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("level", cmd_level))
    application.add_handler(CommandHandler("rewards", cmd_rewards))
    application.add_handler(CommandHandler("settings", cmd_settings))
    application.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats:range:"))
    application.add_handler(CallbackQueryHandler(pagination_callback, pattern="^task:page:"))
    application.add_handler(CallbackQueryHandler(task_action_callback, pattern="^task:(done|skip|snooze|archive|details|sub)"))
    return application


def main() -> None:
    token = load_env()
    db.init_db()
    application = build_application(token)
    application.job_queue.run_repeating(digest_job, interval=300, first=0)
    application.run_polling()


if __name__ == "__main__":
    main()
