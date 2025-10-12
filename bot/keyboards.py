from __future__ import annotations

from typing import Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def chunked(iterable: Iterable, size: int) -> list[list]:
    row: list = []
    result: list[list] = []
    for item in iterable:
        row.append(item)
        if len(row) == size:
            result.append(row)
            row = []
    if row:
        result.append(row)
    return result


def task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton("Done", callback_data=f"task:done:{task_id}"),
        InlineKeyboardButton("Skip", callback_data=f"task:skip:{task_id}"),
        InlineKeyboardButton("Snooze +1d", callback_data=f"task:snooze:{task_id}:1d"),
        InlineKeyboardButton("Subtasks", callback_data=f"task:sub:{task_id}:list"),
        InlineKeyboardButton("Details", callback_data=f"task:detail:{task_id}"),
    ]
    return InlineKeyboardMarkup(chunked(buttons, 2))


def pagination_keyboard(prefix: str, page: int, has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("Prev", callback_data=f"{prefix}:{page-1}"))
    if has_more:
        buttons.append(InlineKeyboardButton("Next", callback_data=f"{prefix}:{page+1}"))
    return InlineKeyboardMarkup([buttons]) if buttons else InlineKeyboardMarkup([])


def stats_range_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton("7d", callback_data="stats:range:7d"),
        InlineKeyboardButton("30d", callback_data="stats:range:30d"),
        InlineKeyboardButton("90d", callback_data="stats:range:90d"),
    ]
    return InlineKeyboardMarkup([buttons])
