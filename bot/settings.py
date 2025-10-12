import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    owner_telegram_id: Optional[int]
    database_url: str = f"sqlite:///{BASE_DIR.parent / 'bot.sqlite'}"
    timezone: str = os.getenv("TZ", "Europe/Zurich")


def get_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    owner_raw = os.getenv("OWNER_TELEGRAM_ID")
    owner_id = int(owner_raw) if owner_raw else None
    db_url = os.getenv("DATABASE_URL") or Settings.database_url
    return Settings(telegram_token=token, owner_telegram_id=owner_id, database_url=db_url)
