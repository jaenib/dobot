from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DOMAIN_ICONS = {
    'coding': '[code]',
    'research': '[read]',
    'admin': '[admin]',
    'creative': '[art]',
    'health': '[fit]',
    'recreation': '[play]',
}

ENERGY_ICONS = {'low': 'low', 'medium': 'mid', 'high': 'high'}
PRIORITY_ICONS = {'must': 'must', 'should': 'should', 'nice': 'nice'}


def build_keyboard(rows: Sequence[Sequence[Tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in rows]
    )


def domain_choice_keyboard(domains: Iterable[Tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: List[List[Tuple[str, str]]] = []
    for domain_id, name in domains:
        icon = DOMAIN_ICONS.get(name, "")
        rows.append([(f"{icon} {name}", f"domain:{domain_id}")])
    return build_keyboard(rows)


def time_horizon_keyboard() -> InlineKeyboardMarkup:
    return build_keyboard(
        [
            [("now", "horizon:now"), ("short", "horizon:short")],
            [("mid", "horizon:mid"), ("long", "horizon:long")],
        ]
    )


def energy_keyboard() -> InlineKeyboardMarkup:
    return build_keyboard(
        [[("low", "energy:low"), ("medium", "energy:medium"), ("high", "energy:high")]]
    )


def priority_keyboard() -> InlineKeyboardMarkup:
    return build_keyboard(
        [[("must", "priority:must"), ("should", "priority:should"), ("nice", "priority:nice")]]
    )


def weight_keyboard() -> InlineKeyboardMarkup:
    return build_keyboard(
        [[("1", "weight:1"), ("2", "weight:2"), ("3", "weight:3"), ("5", "weight:5")]]
    )


def recurrence_keyboard() -> InlineKeyboardMarkup:
    return build_keyboard(
        [
            [("none", "recur:none"), ("daily", "recur:daily"), ("weekly", "recur:weekly")],
            [("custom", "recur:custom")],
        ]
    )


def confirmation_keyboard() -> InlineKeyboardMarkup:
    return build_keyboard(
        [[("Save", "add:save"), ("Cancel", "add:cancel")]]
    )


def task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return build_keyboard(
        [
            [("Done", f"task:done:{task_id}"), ("Snooze +1d", f"task:snooze:{task_id}:1")],
            [("Subtasks", f"task:sub:{task_id}:list"), ("Details", f"task:details:{task_id}")],
            [("Archive", f"task:archive:{task_id}"), ("Skip", f"task:skip:{task_id}")],
        ]
    )


def pagination_keyboard(page: int, total: int) -> InlineKeyboardMarkup:
    buttons: List[Tuple[str, str]] = []
    if page > 0:
        buttons.append(("Prev", f"task:page:{page - 1}"))
    if page < total - 1:
        buttons.append(("Next", f"task:page:{page + 1}"))
    if not buttons:
        return InlineKeyboardMarkup([])
    return build_keyboard([buttons])


def stats_range_keyboard(active: int) -> InlineKeyboardMarkup:
    rows = [[
        ("7d" + (" •" if active == 7 else ""), "stats:range:7"),
        ("30d" + (" •" if active == 30 else ""), "stats:range:30"),
        ("90d" + (" •" if active == 90 else ""), "stats:range:90"),
    ]]
    return build_keyboard(rows)


def subtasks_keyboard(task_id: int, subtasks: Sequence[Tuple[int, str, bool]]) -> InlineKeyboardMarkup:
    rows: List[List[Tuple[str, str]]] = []
    for sub_id, title, done in subtasks:
        prefix = '[x]' if done else '[ ]'
        rows.append([(f"{prefix} {title[:20]}", f"task:sub:{task_id}:{sub_id}:toggle")])
    return build_keyboard(rows)
