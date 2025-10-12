from __future__ import annotations

from dataclasses import dataclass

from typing import Callable, Dict, List

from telegram import Update
from telegram.ext import ContextTypes


@dataclass
class CallbackRoute:
    prefix: str
    handler: Callable[[Update, ContextTypes.DEFAULT_TYPE, List[str]], object]


class CallbackRouter:
    def __init__(self) -> None:
        self.routes: Dict[str, CallbackRoute] = {}

    def register(
        self, prefix: str, handler: Callable[[Update, ContextTypes.DEFAULT_TYPE, List[str]], object]
    ) -> None:
        self.routes[prefix] = CallbackRoute(prefix=prefix, handler=handler)

    async def dispatch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.callback_query or not update.callback_query.data:
            return
        parts = update.callback_query.data.split(":")
        prefix = ":".join(parts[:2]) if len(parts) > 2 else parts[0]
        route = self.routes.get(prefix)
        if not route:
            return
        await route.handler(update, context, parts)


callback_router = CallbackRouter()
