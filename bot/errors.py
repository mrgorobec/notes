import logging
from contextlib import suppress

import httpx
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

from bot.api import ApiError

log = logging.getLogger(__name__)

MESSAGES = {
    "not_registered": "🔒 Немає доступу. Натисни /start або попроси запрошення.",
    "forbidden": "⛔ Недостатньо прав.",
    "not_found": "🤷 Не знайдено — можливо, вже видалено.",
    "folder_exists": "Папка з такою назвою вже є. Напиши іншу назву.",
}


async def on_error(event: ErrorEvent) -> bool:
    exc = event.exception
    if isinstance(exc, ApiError):
        log.warning("API error: %s", exc)
        text = MESSAGES.get(exc.code, f"⚠️ Помилка сервера ({exc.status}).")
    elif isinstance(exc, httpx.TransportError):
        log.error("API unreachable: %r", exc)
        text = "⚠️ Сервер недоступний. Спробуй за хвилину."
    else:
        log.exception("Unhandled error", exc_info=exc)
        text = "⚠️ Щось пішло не так."

    update = event.update
    with suppress(TelegramAPIError):
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
        elif update.message:
            await update.message.answer(text)
    return True
