import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "TEST_TOKEN")
os.environ.setdefault("OWNER_TELEGRAM_ID", "1")
os.environ.setdefault("TZ", "Europe/Zurich")

import pytest

from bot.db import Base, engine


@pytest.fixture(autouse=True, scope="session")
def telegram_token_env():
    Base.metadata.create_all(bind=engine)
