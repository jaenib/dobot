# Dobot

A compact Telegram bot that turns your tasks into a lightweight RPG-style tracker. It helps you juggle domains, energy levels, streaks, and rewards without leaving chat.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill BOT_TOKEN
python -m dobot.app
```

* Requires Python 3.9+.
* SQLite database file is created automatically in the project directory.
* Default timezone is Europe/Zurich.

## Commands

| Command | Description |
| --- | --- |
| /start | Register and get a quick intro. |
| /help | Show the command cheat sheet. |
| /add | Guided creation of a task with priorities and recurrence. |
| /addcheck | Fast track recurring checklist items. |
| /addsub `<task_id>` | Append a subtask. |
| /list | Paginated view of open tasks with inline actions. |
| /today | Highlights overdue, due, and balance picks for today. |
| /task `<id>` | Show a task card with subtasks. |
| /done `<id>` | Mark a task complete and earn XP. |
| /skip `<id>` | Skip a task without XP. |
| /snooze `<id>` `<days>` | Push a due date forward. |
| /streaks | Inspect best, weakest, and at-risk streaks. |
| /stats | Analytics for the last 7/30/90 days. |
| /level | Display your level progression. |
| /rewards | Review and claim rewards. |
| /settings | Tune timezone, digest hour, and notifications. |

Daily digests arrive at your configured hour, weekly reviews on Sundays at 18:00.
