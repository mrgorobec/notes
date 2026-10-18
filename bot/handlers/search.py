"""Any plain text outside of a dialog is a search query. Registered last."""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import keyboards as kb
from bot import views
from bot.api import UserApi

router = Router()


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def search(message: Message, state: FSMContext, api: UserApi):
    query = message.text.strip().splitlines()[0][:128]
    found = await api.search(query)
    if not found:
        await state.update_data(last_search=query)
        await message.answer(
            f"Нічого не знайдено за «{views.esc(query)}».", reply_markup=kb.create_from_search()
        )
        return
    await message.answer(f"🔍 Знайдено: {len(found)}", reply_markup=kb.search_results(found))
