from aiogram.filters.callback_data import CallbackData

# Plain-string callbacks
CANCEL = "cancel"
NOOP = "noop"
NEW_FOLDER = "new_folder"
CREATE_ANYWAY = "new_item:create"
SKIP_FIELDS = "new_item:skip"
CREATE_FROM_SEARCH = "new_item:from_search"


class FolderCb(CallbackData, prefix="f"):
    # list | open | add_item | settings | rename | delete | delete_ok | share
    action: str
    id: int = 0
    page: int = 0


class ShareCb(CallbackData, prefix="sh"):
    folder_id: int
    user_id: int


class PickFolderCb(CallbackData, prefix="pf"):
    """Folder chosen for a new item."""

    id: int


class ItemCb(CallbackData, prefix="i"):
    # open | add_field | edit_field | del_field | rename | move | delete | delete_ok
    action: str
    id: int


class FieldCb(CallbackData, prefix="fl"):
    action: str  # edit | del
    item_id: int
    field_id: int


class MoveCb(CallbackData, prefix="mv"):
    item_id: int
    folder_id: int
