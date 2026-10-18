"""/start, main menu and cancel. Registered first, so menu buttons work from any state."""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import keyboards as kb
from bot import views
from bot.api import ApiError, UserApi
from bot.callbacks import CANCEL, NEW_FOLDER, NOOP
from bot.handlers.items import ask_folder_for_new_item
from bot.states import NewFolder

router = Router()

HELP = (
    "<b>Як користуватись</b>\n\n"
    "📁 <b>Папки</b> — переглянути все, що збережено\n"
    "➕ <b>Запис</b> — зберегти новий (акаунт, посилання, покупку…)\n"
    "🔍 <b>Пошук</b> — просто напиши назву або її частину в чат\n\n"
    "Поля записуй так, кожне з нового рядка:\n"
    "<code>логін: sasha@gmail.com\nпароль: qwerty</code>\n\n"
    "🔒 Паролі, PIN, токени автоматично ховаються під спойлер.\n"
    "/cancel — скасувати поточну дію"
)


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext, api: UserApi):
    await state.clear()
    try:
        user = await api.me()
        greeting = f"З поверненням, {views.esc(user['name'])} 👋"
    except ApiError as e:
        if e.code != "not_registered":
            raise
        try:
            user = await api.register(message.from_user.full_name, command.args)
        except ApiError as e:
            if e.status != 403:
                raise
            await message.answer(
                "🔒 Це приватний бот — потрібне посилання-запрошення від власника.\n\n"
                f"Твій Telegram ID: <code>{message.from_user.id}</code>"
            )
            return
        greeting = f"Вітаю, {views.esc(user['name'])}! 🎉 Тебе зареєстровано."
    await message.answer(f"{greeting}\n\n{HELP}", reply_markup=kb.main_menu(user["is_admin"]))


@router.message(Command("help"))
async def help_(message: Message):
    await message.answer(HELP)


@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.")


@router.callback_query(F.data == CANCEL)
async def cancel_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Скасовано.")
    await cb.answer()


@router.callback_query(F.data == NOOP)
async def noop(cb: CallbackQuery):
    await cb.answer()


# --- main menu ---

@router.message(F.text == kb.MENU_FOLDERS)
async def menu_folders(message: Message, state: FSMContext, api: UserApi):
    await state.clear()
    await views.show_folders(message, api)


@router.message(F.text == kb.MENU_NEW_ITEM)
async def menu_new_item(message: Message, state: FSMContext, api: UserApi):
    await state.clear()
    await ask_folder_for_new_item(message, state, api)


@router.message(F.text == kb.MENU_NEW_FOLDER)
async def menu_new_folder(message: Message, state: FSMContext):
    await state.set_state(NewFolder.name)
    await message.answer("Назва нової папки? Напр. <i>Акаунти</i>", reply_markup=kb.cancel())


@router.callback_query(F.data == NEW_FOLDER)
async def new_folder_cb(cb: CallbackQuery, state: FSMContext):
    await state.set_state(NewFolder.name)
    await cb.message.answer("Назва нової папки? Напр. <i>Акаунти</i>", reply_markup=kb.cancel())
    await cb.answer()


@router.message(F.text == kb.MENU_SEARCH)
async def menu_search(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Просто напиши в чат назву або її частину — я знайду 🔍")


@router.message(F.text == kb.MENU_INVITE)
async def menu_invite(message: Message, state: FSMContext, api: UserApi):
    await state.clear()
    invite = await api.create_invite()
    me = await message.bot.me()
    expires = datetime.fromisoformat(invite["expires_at"])
    await message.answer(
        f"🎟 Посилання-запрошення (одноразове, діє до {expires:%d.%m.%Y}):\n\n"
        f"https://t.me/{me.username}?start={invite['code']}\n\n"
        "Перешли його людині — вона натисне Start і отримає доступ.\n"
        "Її записи будуть окремо від твоїх; спільні папки налаштовуються в ⚙️ Папка → 👥 Доступ."
    )
