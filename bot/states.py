from aiogram.fsm.state import State, StatesGroup


class NewFolder(StatesGroup):
    name = State()


class RenameFolder(StatesGroup):
    name = State()  # data: folder_id


class NewItem(StatesGroup):
    # data: folder_id, title, fields (None until known)
    folder = State()
    title = State()
    confirm = State()
    fields = State()


class AddFields(StatesGroup):
    fields = State()  # data: item_id


class EditField(StatesGroup):
    value = State()  # data: item_id, field_id


class RenameItem(StatesGroup):
    title = State()  # data: item_id
