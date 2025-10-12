# Dobot Gamified To-Do Telegram Bot

This repository contains a production-ready Telegram bot that implements a gamified task tracker with domains, streaks, scoring, and analytics. It is built with Python 3.11 and python-telegram-bot v20.

## Features
- Hierarchical tasks with subtasks and recurrence support
- Weighted XP scoring with streaks, domain balancing, and prioritization
- Daily and weekly digest scheduling via APScheduler
- Inline keyboards for rapid task updates and navigation
- SQLite persistence through SQLAlchemy ORM
- Modular services and handlers for maintainable logic
- pytest unit tests for scoring, streaks, recurrence, analytics, and handler smoke tests

## Project Structure
```
bot/
  app.py
  settings.py
  db.py
  models.py
  schemas.py
  scoring.py
  recurrence.py
  keyboards.py
  handlers/
    __init__.py
    start.py
    tasks.py
    checks.py
    stats.py
    rewards.py
    admin.py
    common.py
  services/
    __init__.py
    task_service.py
    user_service.py
    analytics_service.py
    reward_service.py
    reminder_service.py
  views/
    __init__.py
    messages.py
    formatting.py
  jobs/
    __init__.py
    scheduler.py
  tests/
    __init__.py
    test_scoring.py
    test_streaks.py
    test_recurrence.py
    test_analytics.py
    test_handlers.py
requirements.txt
README.md
```

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file:
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC
   OWNER_TELEGRAM_ID=123456
   TZ=Europe/Zurich
   ```

## Database
Tables are created automatically on startup. SQLite is stored in `bot.sqlite` by default. Seed domains are inserted if missing.

## Running
```bash
python -m bot.app
```

## Testing
```bash
pytest
```

## Docker (optional)
A Dockerfile is provided. Build and run with:
```bash
docker build -t dobot .
docker run --env-file .env dobot
```

## Example Workflow
- `/start` registers the user and seeds data
- `/add` launches a guided flow for new tasks
- `/today` summarises overdue, today, and balance tasks
- `/done` completes a task, awarding XP and streak progress
- `/stats 30d` shows 30-day analytics

## License
MIT
