from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from dateutil import rrule

DAILY = "DAILY"
WEEKLY = "WEEKLY"


class RecurrenceError(ValueError):
    pass


def parse_recurrence(value: str | None) -> dict:
    if not value:
        return {"type": None}
    upper = value.upper()
    if upper == DAILY:
        return {"type": DAILY}
    if upper.startswith(WEEKLY):
        parts = upper.split(":", 1)
        byweekday = parts[1].split(",") if len(parts) == 2 else ["MO"]
        return {"type": WEEKLY, "byweekday": byweekday}
    try:
        rrule.rrulestr(value)
    except Exception as exc:  # pragma: no cover - delegated to dateutil
        raise RecurrenceError(str(exc)) from exc
    return {"type": "CUSTOM", "value": value}


def next_occurrence(value: str | None, start: datetime) -> Optional[datetime]:
    if not value:
        return None
    info = parse_recurrence(value)
    if info["type"] == DAILY:
        return start + timedelta(days=1)
    if info["type"] == WEEKLY:
        return start + timedelta(weeks=1)
    if info["type"] == "CUSTOM":
        rule = rrule.rrulestr(info["value"], dtstart=start)
        return rule.after(start)
    return None


def is_due_today(value: str | None, due_at: datetime | None, reference: datetime) -> bool:
    if due_at:
        return due_at.date() == reference.date()
    info = parse_recurrence(value)
    if info["type"] == DAILY:
        return True
    if info["type"] == WEEKLY:
        weekdays = info.get("byweekday", ["MO"])
        weekday_map = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
        return reference.weekday() in {weekday_map.get(w, -1) for w in weekdays}
    if info["type"] == "CUSTOM":
        rule = rrule.rrulestr(info["value"], dtstart=reference)
        previous = rule.before(reference, inc=True)
        return previous is not None and previous.date() == reference.date()
    return False
