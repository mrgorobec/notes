"""Auth and access helpers.

The bot is a trusted client: it proves itself with X-API-Key and says which Telegram user
it acts for with X-Telegram-Id. A future web client will get its own auth on top of this.
"""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Folder, FolderMember, Item, User

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
TelegramId = Annotated[int, Header(alias="X-Telegram-Id")]


async def require_api_key(
    settings: SettingsDep, x_api_key: Annotated[str, Header(alias="X-API-Key")]
) -> None:
    if not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(401, "bad_api_key")


async def current_user(session: SessionDep, telegram_id: TelegramId) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        raise HTTPException(401, "not_registered")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def admin_user(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(403, "forbidden")
    return user


AdminUser = Annotated[User, Depends(admin_user)]


def accessible_folder_ids(user: User) -> Select[tuple[int]]:
    shared = select(FolderMember.folder_id).where(FolderMember.user_id == user.id)
    return select(Folder.id).where(or_(Folder.owner_id == user.id, Folder.id.in_(shared)))


async def get_folder(
    session: AsyncSession, folder_id: int, user: User, *, owner_only: bool = False
) -> Folder:
    folder = await session.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(404, "not_found")
    if folder.owner_id == user.id:
        return folder
    if await session.get(FolderMember, (folder_id, user.id)) is None:
        raise HTTPException(404, "not_found")
    if owner_only:
        raise HTTPException(403, "forbidden")
    return folder


async def get_item(session: AsyncSession, item_id: int, user: User) -> Item:
    item = await session.scalar(
        select(Item)
        .options(selectinload(Item.fields), joinedload(Item.folder))
        .where(Item.id == item_id, Item.folder_id.in_(accessible_folder_ids(user)))
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise HTTPException(404, "not_found")
    return item
