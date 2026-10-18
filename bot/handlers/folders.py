from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import keyboards as kb
from bot import views
from bot.api import UserApi
from bot.callbacks import FolderCb, ShareCb
from bot.states import NewFolder, RenameFolder

router = Router()


@router.callback_query(FolderCb.filter(F.action == "list"))
async def folders_list(cb: CallbackQuery, state: FSMContext, api: UserApi):
    await state.clear()
    await views.show_folders(cb, api)


@router.callback_query(FolderCb.filter(F.action == "open"))
async def folder_open(cb: CallbackQuery, callback_data: FolderCb, state: FSMContext, api: UserApi):
    await state.clear()
    await views.show_folder(cb, api, callback_data.id, callback_data.page)


@router.message(NewFolder.name, F.text)
async def new_folder_name(message: Message, state: FSMContext, api: UserApi):
    folder = await api.create_folder(message.text.strip()[:64])
    await state.clear()
    await views.show_folder(message, api, folder["id"])


@router.callback_query(FolderCb.filter(F.action == "settings"))
async def folder_settings(cb: CallbackQuery, callback_data: FolderCb, api: UserApi):
    await views.show_folder_settings(cb, api, callback_data.id)


@router.callback_query(FolderCb.filter(F.action == "rename"))
async def folder_rename(cb: CallbackQuery, callback_data: FolderCb, state: FSMContext):
    await state.set_state(RenameFolder.name)
    await state.update_data(folder_id=callback_data.id)
    await cb.message.answer("Нова назва папки?", reply_markup=kb.cancel())
    await cb.answer()


@router.message(RenameFolder.name, F.text)
async def folder_rename_done(message: Message, state: FSMContext, api: UserApi):
    folder_id = (await state.get_data())["folder_id"]
    await api.rename_folder(folder_id, message.text.strip()[:64])
    await state.clear()
    await views.show_folder(message, api, folder_id)


@router.callback_query(FolderCb.filter(F.action == "delete"))
async def folder_delete(cb: CallbackQuery, callback_data: FolderCb, api: UserApi):
    folder = await api.folder(callback_data.id)
    await views.respond(
        cb,
        f"Видалити папку «{views.esc(folder['name'])}» разом з усіма записами "
        f"({folder['item_count']})? Це не можна скасувати.",
        kb.confirm_delete_folder(callback_data.id),
    )


@router.callback_query(FolderCb.filter(F.action == "delete_ok"))
async def folder_delete_ok(cb: CallbackQuery, callback_data: FolderCb, api: UserApi):
    await api.delete_folder(callback_data.id)
    folders = await api.folders()
    await views.respond(cb, "<b>📁 Папки</b>", kb.folders(folders), notice="Папку видалено")


@router.callback_query(FolderCb.filter(F.action == "share"))
async def folder_share(cb: CallbackQuery, callback_data: FolderCb, api: UserApi):
    await views.show_share(cb, api, callback_data.id)


@router.callback_query(ShareCb.filter())
async def folder_share_toggle(cb: CallbackQuery, callback_data: ShareCb, api: UserApi):
    member_ids = {m["id"] for m in await api.members(callback_data.folder_id)}
    if callback_data.user_id in member_ids:
        await api.remove_member(callback_data.folder_id, callback_data.user_id)
    else:
        await api.add_member(callback_data.folder_id, callback_data.user_id)
    await views.show_share(cb, api, callback_data.folder_id)
