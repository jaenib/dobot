import asyncio

from bot.handlers.start import start


class DummyMessage:
    def __init__(self):
        self.texts = []

    async def reply_text(self, text: str) -> None:
        self.texts.append(text)


class DummyUser:
    def __init__(self):
        self.id = 1
        self.first_name = "Tester"
        self.full_name = "Tester"
        self.username = "tester"


class DummyUpdate:
    def __init__(self):
        self.update_id = 1
        self._effective_user = DummyUser()
        self.message = DummyMessage()

    @property
    def effective_user(self):
        return self._effective_user


class DummyContext:
    application = None


def test_start_handler():
    update = DummyUpdate()
    context = DummyContext()
    asyncio.run(start(update, context))
    assert update.message.texts
