import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, TelegramObject

from bot.api import ApiClient
from bot.config import BotSettings
from bot.errors import on_error
from bot.handlers import common, folders, items, search


class ApiMiddleware(BaseMiddleware):
    """Gives every handler an `api` client bound to the Telegram user who sent the update."""

    def __init__(self, client: ApiClient):
        self.client = client

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if user := data.get("event_from_user"):
            data["api"] = self.client.for_user(user.id)
        return await handler(event, data)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = BotSettings()
    api = ApiClient(settings.api_url, settings.api_key)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.filter(F.chat.type == "private")
    dp.callback_query.filter(F.message.chat.type == "private")
    dp.update.outer_middleware(ApiMiddleware(api))
    dp.errors.register(on_error)
    # order matters: menu buttons first, free-text search last
    dp.include_routers(common.router, folders.router, items.router, search.router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Головне меню"),
        BotCommand(command="help", description="Як користуватись"),
        BotCommand(command="cancel", description="Скасувати дію"),
    ])
    try:
        await dp.start_polling(bot)
    finally:
        await api.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
