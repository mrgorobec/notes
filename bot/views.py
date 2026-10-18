"""Rendering of screens. A screen is sent as a new message, or edited in place for callbacks."""

from contextlib import suppress
from html import escape

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import keyboards as kb
from bot.api import UserApi
from bot.parsing import URL_RE

Target = Message | CallbackQuery


def esc(text: str) -> str:
    return escape(text, quote=False)


async def respond(
    target: Target, text: str, markup: InlineKeyboardMarkup | None = None, notice: str | None = None
) -> None:
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await target.answer(notice)
    else:
        await target.answer(text, reply_markup=markup)


async def delete_quietly(message: Message) -> None:
    """Remove the user's message (e.g. with a password) from the chat once it's saved."""
    with suppress(TelegramBadRequest):
        await message.delete()


# --- folders ---

async def show_folders(target: Target, api: UserApi) -> None:
    folders = await api.folders()
    text = "<b>📁 Папки</b>" if folders else "Поки немає жодної папки. Створи першу 👇"
    await respond(target, text, kb.folders(folders))


async def show_folder(target: Target, api: UserApi, folder_id: int, page: int = 0) -> None:
    folder = await api.folder(folder_id)
    items = await api.folder_items(folder_id)
    lines = [f"<b>📁 {esc(folder['name'])}</b>", f"Записів: {len(items)}"]
    if not folder["is_owner"]:
        lines.append(f"👥 Спільна · власник: {esc(folder['owner_name'])}")
    elif folder["is_shared"]:
        lines.append("👥 Спільна")
    if not items:
        lines.append("\nТут поки порожньо — додай перший запис 👇")
    await respond(target, "\n".join(lines), kb.folder(folder, items, page))


async def show_folder_settings(target: Target, api: UserApi, folder_id: int) -> None:
    folder = await api.folder(folder_id)
    await respond(
        target, f"<b>⚙️ Папка «{esc(folder['name'])}»</b>", kb.folder_settings(folder_id)
    )


async def show_share(target: Target, api: UserApi, folder_id: int) -> None:
    folder = await api.folder(folder_id)
    users = await api.users()
    if not users:
        text = (
            f"<b>👥 Доступ до «{esc(folder['name'])}»</b>\n\n"
            "Поки немає інших користувачів. Запроси когось кнопкою «🎟 Запросити»."
        )
    else:
        text = (
            f"<b>👥 Доступ до «{esc(folder['name'])}»</b>\n\n"
            "Натисни на людину, щоб дати або забрати доступ. "
            "З доступом можна переглядати, додавати й редагувати записи."
        )
    member_ids = {m["id"] for m in await api.members(folder_id)}
    await respond(target, text, kb.share(folder_id, users, member_ids))


# --- items ---

def _render_value(field: dict, limit: int) -> str:
    value = field["value"]
    if len(value) > limit:
        value = value[:limit] + "…"
    if field["is_secret"]:
        return f"<tg-spoiler><code>{esc(value)}</code></tg-spoiler>"
    if URL_RE.match(value):
        return esc(value)  # keep links clickable
    if "\n" in value:
        return f"\n<pre>{esc(value)}</pre>"
    return f"<code>{esc(value)}</code>"  # tap to copy


def render_item(item: dict) -> str:
    for limit in (4000, 300, 60):
        lines = [f"<b>📄 {esc(item['title'])}</b>", f"<i>📁 {esc(item['folder_name'])}</i>", ""]
        if not item["fields"]:
            lines.append("<i>Полів поки немає.</i>")
        for f in item["fields"]:
            lines.append(f"<b>{esc(f['key'])}:</b> {_render_value(f, limit)}")
        text = "\n".join(lines)
        if len(text) <= 4000:
            break
    return text


async def show_item(
    target: Target, api: UserApi, item_id: int | None = None, item: dict | None = None,
    notice: str | None = None,
) -> None:
    if item is None:
        item = await api.item(item_id)
    await respond(target, render_item(item), kb.item(item), notice)
