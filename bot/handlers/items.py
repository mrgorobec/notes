from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import keyboards as kb
from bot import views
from bot.api import UserApi
from bot.callbacks import (
    CREATE_ANYWAY,
    CREATE_FROM_SEARCH,
    SKIP_FIELDS,
    FieldCb,
    FolderCb,
    ItemCb,
    MoveCb,
    PickFolderCb,
)
from bot.parsing import parse_fields
from bot.states import AddFields, EditField, NewItem, RenameItem

router = Router()

TITLE_PROMPT = (
    "Як назвати запис? Напр. <i>Дія</i>\n\n"
    "Можна одразу з полями — перший рядок назва, далі поля:\n"
    "<code>Дія\nлогін: 0501234567\nпароль: qwerty</code>"
)
FIELDS_PROMPT = (
    "Тепер поля — кожне з нового рядка у форматі <code>назва: значення</code>:\n\n"
    "<code>логін: sasha@gmail.com\nпароль: qwerty123\nпосилання: https://diia.gov.ua</code>\n\n"
    "🔒 Паролі, PIN, токени автоматично ховаються під спойлер.\n"
    "🧹 Твоє повідомлення я одразу приберу з чату."
)


# --- new item: folder → title (→ duplicates?) → fields ---

async def ask_folder_for_new_item(
    target: views.Target, state: FSMContext, api: UserApi, title: str | None = None
) -> None:
    folders = await api.folders()
    if not folders:
        await views.respond(target, "Спочатку створи папку 👇", kb.folders([]))
        return
    await state.set_state(NewItem.folder)
    await state.update_data(title=title, fields=None)
    await views.respond(target, "Куди зберегти запис?", kb.pick_folder(folders))


@router.callback_query(NewItem.folder, PickFolderCb.filter())
async def new_item_folder(
    cb: CallbackQuery, callback_data: PickFolderCb, state: FSMContext, api: UserApi
):
    await state.update_data(folder_id=callback_data.id)
    if (await state.get_data()).get("title"):
        await _ask_fields(cb, state)  # title came from search, already known to be new
    else:
        await state.set_state(NewItem.title)
        await views.respond(cb, TITLE_PROMPT, kb.cancel())


@router.callback_query(FolderCb.filter(F.action == "add_item"))
async def new_item_in_folder(cb: CallbackQuery, callback_data: FolderCb, state: FSMContext):
    await state.clear()
    await state.set_state(NewItem.title)
    await state.update_data(folder_id=callback_data.id, fields=None)
    await cb.message.answer(TITLE_PROMPT, reply_markup=kb.cancel())
    await cb.answer()


@router.callback_query(F.data == CREATE_FROM_SEARCH)
async def new_item_from_search(cb: CallbackQuery, state: FSMContext, api: UserApi):
    title = (await state.get_data()).get("last_search")
    await ask_folder_for_new_item(cb, state, api, title=title)


@router.message(NewItem.title, F.text)
async def new_item_title(message: Message, state: FSMContext, api: UserApi):
    first, _, rest = message.text.strip().partition("\n")
    title = first.strip()[:128]
    fields = parse_fields(rest) or None
    if fields:
        await views.delete_quietly(message)
    await state.update_data(title=title, fields=fields)

    similar = await api.search(title)
    if similar:
        await state.set_state(NewItem.confirm)
        await message.answer(
            f"⚠️ Схожі записи на «{views.esc(title)}» вже є:", reply_markup=kb.duplicates(similar[:5])
        )
        return
    await _continue(message, state, api)


@router.callback_query(NewItem.confirm, F.data == CREATE_ANYWAY)
async def new_item_confirmed(cb: CallbackQuery, state: FSMContext, api: UserApi):
    await _continue(cb, state, api)


async def _continue(target: views.Target, state: FSMContext, api: UserApi) -> None:
    if (await state.get_data()).get("fields"):
        await _create(target, state, api)
    else:
        await _ask_fields(target, state)


async def _ask_fields(target: views.Target, state: FSMContext) -> None:
    await state.set_state(NewItem.fields)
    await views.respond(target, FIELDS_PROMPT, kb.skip_fields())


@router.message(NewItem.fields, F.text)
async def new_item_fields(message: Message, state: FSMContext, api: UserApi):
    await state.update_data(fields=parse_fields(message.text))
    await views.delete_quietly(message)
    await _create(message, state, api)


@router.callback_query(NewItem.fields, F.data == SKIP_FIELDS)
async def new_item_no_fields(cb: CallbackQuery, state: FSMContext, api: UserApi):
    await state.update_data(fields=[])
    await _create(cb, state, api)


async def _create(target: views.Target, state: FSMContext, api: UserApi) -> None:
    data = await state.get_data()
    item = await api.create_item(data["folder_id"], data["title"], data.get("fields") or [])
    await state.clear()
    await views.show_item(target, api, item=item, notice="Збережено ✅")


# --- view & edit ---

@router.callback_query(ItemCb.filter(F.action == "open"))
async def item_open(cb: CallbackQuery, callback_data: ItemCb, state: FSMContext, api: UserApi):
    await state.clear()
    await views.show_item(cb, api, callback_data.id)


@router.callback_query(ItemCb.filter(F.action == "add_field"))
async def field_add(cb: CallbackQuery, callback_data: ItemCb, state: FSMContext):
    await state.set_state(AddFields.fields)
    await state.update_data(item_id=callback_data.id)
    await cb.message.answer(FIELDS_PROMPT, reply_markup=kb.cancel())
    await cb.answer()


@router.message(AddFields.fields, F.text)
async def field_add_done(message: Message, state: FSMContext, api: UserApi):
    item_id = (await state.get_data())["item_id"]
    item = await api.add_fields(item_id, parse_fields(message.text))
    await views.delete_quietly(message)
    await state.clear()
    await views.show_item(message, api, item=item)


@router.callback_query(ItemCb.filter(F.action.in_({"edit_field", "del_field"})))
async def field_pick(cb: CallbackQuery, callback_data: ItemCb, api: UserApi):
    item = await api.item(callback_data.id)
    action = "edit" if callback_data.action == "edit_field" else "del"
    await cb.message.edit_reply_markup(reply_markup=kb.pick_field(item, action))
    await cb.answer("Яке поле змінити?" if action == "edit" else "Яке поле видалити?")


@router.callback_query(FieldCb.filter(F.action == "edit"))
async def field_edit(cb: CallbackQuery, callback_data: FieldCb, state: FSMContext, api: UserApi):
    item = await api.item(callback_data.item_id)
    field = next((f for f in item["fields"] if f["id"] == callback_data.field_id), None)
    if field is None:
        await cb.answer("Поле вже видалено", show_alert=True)
        return
    await state.set_state(EditField.value)
    await state.update_data(item_id=callback_data.item_id, field_id=callback_data.field_id)
    await cb.message.answer(
        f"Нове значення для «{views.esc(field['key'])}»:", reply_markup=kb.cancel()
    )
    await cb.answer()


@router.message(EditField.value, F.text)
async def field_edit_done(message: Message, state: FSMContext, api: UserApi):
    data = await state.get_data()
    item = await api.update_field(data["item_id"], data["field_id"], value=message.text.strip())
    await views.delete_quietly(message)
    await state.clear()
    await views.show_item(message, api, item=item)


@router.callback_query(FieldCb.filter(F.action == "del"))
async def field_delete(cb: CallbackQuery, callback_data: FieldCb, api: UserApi):
    item = await api.delete_field(callback_data.item_id, callback_data.field_id)
    await views.show_item(cb, api, item=item, notice="Поле видалено")


@router.callback_query(ItemCb.filter(F.action == "rename"))
async def item_rename(cb: CallbackQuery, callback_data: ItemCb, state: FSMContext):
    await state.set_state(RenameItem.title)
    await state.update_data(item_id=callback_data.id)
    await cb.message.answer("Нова назва запису?", reply_markup=kb.cancel())
    await cb.answer()


@router.message(RenameItem.title, F.text)
async def item_rename_done(message: Message, state: FSMContext, api: UserApi):
    item_id = (await state.get_data())["item_id"]
    item = await api.update_item(item_id, title=message.text.strip()[:128])
    await state.clear()
    await views.show_item(message, api, item=item)


@router.callback_query(ItemCb.filter(F.action == "move"))
async def item_move(cb: CallbackQuery, callback_data: ItemCb, api: UserApi):
    item = await api.item(callback_data.id)
    targets = [f for f in await api.folders() if f["id"] != item["folder_id"]]
    if not targets:
        await cb.answer("Немає інших папок", show_alert=True)
        return
    await cb.message.edit_reply_markup(reply_markup=kb.move(item, targets))
    await cb.answer("Куди перемістити?")


@router.callback_query(MoveCb.filter())
async def item_move_done(cb: CallbackQuery, callback_data: MoveCb, api: UserApi):
    item = await api.update_item(callback_data.item_id, folder_id=callback_data.folder_id)
    await views.show_item(cb, api, item=item, notice=f"Переміщено в «{item['folder_name']}»")


@router.callback_query(ItemCb.filter(F.action == "delete"))
async def item_delete(cb: CallbackQuery, callback_data: ItemCb):
    await cb.message.edit_reply_markup(reply_markup=kb.confirm_delete_item(callback_data.id))
    await cb.answer("Точно видалити?")


@router.callback_query(ItemCb.filter(F.action == "delete_ok"))
async def item_delete_ok(cb: CallbackQuery, callback_data: ItemCb, api: UserApi):
    item = await api.item(callback_data.id)
    await api.delete_item(item["id"])
    await views.show_folder(cb, api, item["folder_id"])
