from __future__ import annotations

import asyncio

from telegram.ext import Application, ApplicationBuilder, CommandHandler

from .db import Base, engine
from .handlers import admin as admin_handler
from .handlers import checks, rewards, start, stats, tasks
from .jobs.scheduler import create_scheduler
from .settings import get_settings


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def build_application(settings) -> Application:
    application = ApplicationBuilder().token(settings.telegram_token).build()

    application.add_handler(CommandHandler("start", start.start))
    application.add_handler(tasks.conversation_handler)
    application.add_handler(CommandHandler("today", tasks.today))
    application.add_handler(CommandHandler("done", tasks.done))
    application.add_handler(CommandHandler("backlog", tasks.backlog))
    application.add_handler(CommandHandler("stats", stats.stats))
    application.add_handler(CommandHandler("rewards", rewards.rewards))
    application.add_handler(CommandHandler("addcheck", checks.addcheck))
    application.add_handler(CommandHandler("admin", admin_handler.admin))

    scheduler = create_scheduler(settings.timezone)
    scheduler.start()
    scheduler.schedule_daily_digest(application)
    scheduler.schedule_weekly_review(application)
    application.bot_data["scheduler"] = scheduler

    return application


async def main() -> None:
    settings = get_settings()
    init_db()
    app = build_application(settings)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.wait()


if __name__ == "__main__":
    asyncio.run(main())
