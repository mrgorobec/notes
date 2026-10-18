from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot.callbacks import (
    CANCEL,
    CREATE_ANYWAY,
    CREATE_FROM_SEARCH,
    NEW_FOLDER,
    NOOP,
    SKIP_FIELDS,
    FieldCb,
    FolderCb,
    ItemCb,
    MoveCb,
    PickFolderCb,
    ShareCb,
)

MENU_FOLDERS = "📁 Папки"
MENU_NEW_ITEM = "➕ Запис"
MENU_NEW_FOLDER = "➕ Папка"
MENU_SEARCH = "🔍 Пошук"
MENU_INVITE = "🎟 Запросити"
MENU_BUTTONS = {MENU_FOLDERS, MENU_NEW_ITEM, MENU_NEW_FOLDER, MENU_SEARCH, MENU_INVITE}

PAGE_SIZE = 15


def main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text=MENU_FOLDERS)
    kb.button(text=MENU_NEW_ITEM)
    kb.button(text=MENU_SEARCH)
    kb.button(text=MENU_NEW_FOLDER)
    if is_admin:
        kb.button(text=MENU_INVITE)
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True, is_persistent=True)


def cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Скасувати", callback_data=CANCEL)]]
    )


def _folder_label(folder: dict) -> str:
    shared = " 👥" if folder["is_shared"] or not folder["is_owner"] else ""
    return f"📁 {folder['name']} · {folder['item_count']}{shared}"


def folders(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in items:
        kb.button(text=_folder_label(f), callback_data=FolderCb(action="open", id=f["id"]))
    kb.button(text="➕ Нова папка", callback_data=NEW_FOLDER)
    kb.adjust(1)
    return kb.as_markup()


def folder(folder: dict, items: list[dict], page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    pages = max(1, -(-len(items) // PAGE_SIZE))
    page = min(page, pages - 1)
    for item in items[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]:
        kb.row(
            InlineKeyboardButton(
                text=f"📄 {item['title']}",
                callback_data=ItemCb(action="open", id=item["id"]).pack(),
            )
        )
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(
                text="◀️", callback_data=FolderCb(action="open", id=folder["id"], page=page - 1).pack()
            ))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data=NOOP))
        if page < pages - 1:
            nav.append(InlineKeyboardButton(
                text="▶️", callback_data=FolderCb(action="open", id=folder["id"], page=page + 1).pack()
            ))
        kb.row(*nav)
    actions = [InlineKeyboardButton(
        text="➕ Запис", callback_data=FolderCb(action="add_item", id=folder["id"]).pack()
    )]
    if folder["is_owner"]:
        actions.append(InlineKeyboardButton(
            text="⚙️ Папка", callback_data=FolderCb(action="settings", id=folder["id"]).pack()
        ))
    kb.row(*actions)
    kb.row(InlineKeyboardButton(text="⬅️ Папки", callback_data=FolderCb(action="list").pack()))
    return kb.as_markup()


def folder_settings(folder_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Перейменувати", callback_data=FolderCb(action="rename", id=folder_id))
    kb.button(text="👥 Доступ", callback_data=FolderCb(action="share", id=folder_id))
    kb.button(text="🗑 Видалити", callback_data=FolderCb(action="delete", id=folder_id))
    kb.button(text="⬅️ Назад", callback_data=FolderCb(action="open", id=folder_id))
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def confirm_delete_folder(folder_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Так, видалити", callback_data=FolderCb(action="delete_ok", id=folder_id))
    kb.button(text="⬅️ Ні", callback_data=FolderCb(action="settings", id=folder_id))
    return kb.as_markup()


def share(folder_id: int, users: list[dict], member_ids: set[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in users:
        mark = "✅" if u["id"] in member_ids else "▫️"
        kb.button(
            text=f"{mark} {u['name']}", callback_data=ShareCb(folder_id=folder_id, user_id=u["id"])
        )
    kb.button(text="⬅️ Назад", callback_data=FolderCb(action="settings", id=folder_id))
    kb.adjust(1)
    return kb.as_markup()


def pick_folder(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in items:
        kb.button(text=_folder_label(f), callback_data=PickFolderCb(id=f["id"]))
    kb.button(text="❌ Скасувати", callback_data=CANCEL)
    kb.adjust(1)
    return kb.as_markup()


def duplicates(similar: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in similar:
        kb.button(
            text=f"📄 {item['title']} · {item['folder_name']}",
            callback_data=ItemCb(action="open", id=item["id"]),
        )
    kb.button(text="✅ Все одно створити", callback_data=CREATE_ANYWAY)
    kb.button(text="❌ Скасувати", callback_data=CANCEL)
    kb.adjust(1)
    return kb.as_markup()


def skip_fields() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏭ Без полів", callback_data=SKIP_FIELDS)
    kb.button(text="❌ Скасувати", callback_data=CANCEL)
    return kb.as_markup()


def search_results(found: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in found:
        kb.button(
            text=f"📄 {item['title']} · {item['folder_name']}",
            callback_data=ItemCb(action="open", id=item["id"]),
        )
    kb.adjust(1)
    return kb.as_markup()


def create_from_search() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Створити такий запис", callback_data=CREATE_FROM_SEARCH)
    return kb.as_markup()


def item(item: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    i = item["id"]
    kb.button(text="➕ Поле", callback_data=ItemCb(action="add_field", id=i))
    if item["fields"]:
        kb.button(text="✏️ Змінити поле", callback_data=ItemCb(action="edit_field", id=i))
        kb.button(text="➖ Видалити поле", callback_data=ItemCb(action="del_field", id=i))
    kb.button(text="🏷 Назва", callback_data=ItemCb(action="rename", id=i))
    kb.button(text="📂 Перемістити", callback_data=ItemCb(action="move", id=i))
    kb.button(text="🗑 Видалити", callback_data=ItemCb(action="delete", id=i))
    kb.button(text="⬅️ До папки", callback_data=FolderCb(action="open", id=item["folder_id"]))
    kb.adjust(*([1, 2, 2, 1, 1] if item["fields"] else [2, 2, 1]))
    return kb.as_markup()


def pick_field(item: dict, action: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    icon = "✏️" if action == "edit" else "➖"
    for f in item["fields"]:
        kb.button(
            text=f"{icon} {f['key']}",
            callback_data=FieldCb(action=action, item_id=item["id"], field_id=f["id"]),
        )
    kb.button(text="⬅️ Назад", callback_data=ItemCb(action="open", id=item["id"]))
    kb.adjust(1)
    return kb.as_markup()


def move(item: dict, targets: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in targets:
        kb.button(text=_folder_label(f), callback_data=MoveCb(item_id=item["id"], folder_id=f["id"]))
    kb.button(text="⬅️ Назад", callback_data=ItemCb(action="open", id=item["id"]))
    kb.adjust(1)
    return kb.as_markup()


def confirm_delete_item(item_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Так, видалити", callback_data=ItemCb(action="delete_ok", id=item_id))
    kb.button(text="⬅️ Ні", callback_data=ItemCb(action="open", id=item_id))
    return kb.as_markup()
