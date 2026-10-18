from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- users & invites ---

class RegisterIn(In):
    name: str = Field(min_length=1, max_length=128)
    invite_code: str | None = None


class UserOut(Out):
    id: int
    telegram_id: int
    name: str
    is_admin: bool


class UserBrief(Out):
    id: int
    name: str


class InviteOut(Out):
    code: str
    expires_at: datetime


# --- folders ---

class FolderIn(In):
    name: str = Field(min_length=1, max_length=64)


class FolderOut(Out):
    id: int
    name: str
    owner_name: str
    is_owner: bool
    is_shared: bool
    item_count: int


# --- items ---

class FieldIn(In):
    key: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=4000)
    # None = guess from the key ("пароль", "PIN", "token" … → secret)
    is_secret: bool | None = None


class FieldPatch(In):
    key: str | None = Field(None, min_length=1, max_length=64)
    value: str | None = Field(None, min_length=1, max_length=4000)
    is_secret: bool | None = None


class FieldOut(Out):
    id: int
    key: str
    value: str
    is_secret: bool


class ItemIn(In):
    title: str = Field(min_length=1, max_length=128)
    fields: list[FieldIn] = []


class ItemPatch(In):
    title: str | None = Field(None, min_length=1, max_length=128)
    folder_id: int | None = None


class ItemShort(Out):
    id: int
    title: str
    folder_id: int
    folder_name: str


class ItemOut(Out):
    id: int
    title: str
    folder_id: int
    folder_name: str
    fields: list[FieldOut]
    created_at: datetime
    updated_at: datetime
