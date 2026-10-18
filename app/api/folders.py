from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, accessible_folder_ids, get_folder
from app.models import Folder, FolderMember, Item, User
from app.schemas import FolderIn, FolderOut, UserBrief

router = APIRouter(prefix="/folders", tags=["folders"])


async def _folder_rows(
    session: AsyncSession, user: User, folder_id: int | None = None
) -> list[FolderOut]:
    item_counts = (
        select(Item.folder_id, func.count(Item.id).label("n")).group_by(Item.folder_id).subquery()
    )
    member_counts = (
        select(FolderMember.folder_id, func.count().label("n"))
        .group_by(FolderMember.folder_id)
        .subquery()
    )
    stmt = (
        select(
            Folder,
            User.name,
            func.coalesce(item_counts.c.n, 0),
            func.coalesce(member_counts.c.n, 0),
        )
        .join(User, User.id == Folder.owner_id)
        .outerjoin(item_counts, item_counts.c.folder_id == Folder.id)
        .outerjoin(member_counts, member_counts.c.folder_id == Folder.id)
        .where(Folder.id.in_(accessible_folder_ids(user)))
        # own folders first, then the ones shared with me
        .order_by(case((Folder.owner_id == user.id, 0), else_=1), func.lower(Folder.name))
    )
    if folder_id is not None:
        stmt = stmt.where(Folder.id == folder_id)
    rows = await session.execute(stmt)
    return [
        FolderOut(
            id=folder.id,
            name=folder.name,
            owner_name=owner_name,
            is_owner=folder.owner_id == user.id,
            is_shared=members > 0,
            item_count=items,
        )
        for folder, owner_name, items, members in rows
    ]


async def _ensure_unique_name(session: AsyncSession, owner_id: int, name: str) -> None:
    exists = await session.scalar(
        select(Folder.id).where(Folder.owner_id == owner_id, Folder.name == name)
    )
    if exists:
        raise HTTPException(409, "folder_exists")


@router.get("", response_model=list[FolderOut])
async def list_folders(session: SessionDep, user: CurrentUser):
    return await _folder_rows(session, user)


@router.post("", response_model=FolderOut, status_code=201)
async def create_folder(body: FolderIn, session: SessionDep, user: CurrentUser):
    await _ensure_unique_name(session, user.id, body.name)
    folder = Folder(owner_id=user.id, name=body.name)
    session.add(folder)
    await session.commit()
    return FolderOut(
        id=folder.id,
        name=folder.name,
        owner_name=user.name,
        is_owner=True,
        is_shared=False,
        item_count=0,
    )


@router.get("/{folder_id}", response_model=FolderOut)
async def read_folder(folder_id: int, session: SessionDep, user: CurrentUser):
    rows = await _folder_rows(session, user, folder_id)
    if not rows:
        raise HTTPException(404, "not_found")
    return rows[0]


@router.patch("/{folder_id}", response_model=FolderOut)
async def rename_folder(folder_id: int, body: FolderIn, session: SessionDep, user: CurrentUser):
    folder = await get_folder(session, folder_id, user, owner_only=True)
    if folder.name != body.name:
        await _ensure_unique_name(session, user.id, body.name)
        folder.name = body.name
        await session.commit()
    return (await _folder_rows(session, user, folder_id))[0]


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(folder_id: int, session: SessionDep, user: CurrentUser):
    """Deletes the folder with all its items (DB cascade)."""
    folder = await get_folder(session, folder_id, user, owner_only=True)
    await session.delete(folder)
    await session.commit()
    return Response(status_code=204)


# --- sharing ---

@router.get("/{folder_id}/members", response_model=list[UserBrief])
async def list_members(folder_id: int, session: SessionDep, user: CurrentUser):
    await get_folder(session, folder_id, user, owner_only=True)
    users = await session.scalars(
        select(User)
        .join(FolderMember, FolderMember.user_id == User.id)
        .where(FolderMember.folder_id == folder_id)
        .order_by(User.name)
    )
    return users.all()


@router.put("/{folder_id}/members/{user_id}", status_code=204)
async def add_member(folder_id: int, user_id: int, session: SessionDep, user: CurrentUser):
    folder = await get_folder(session, folder_id, user, owner_only=True)
    if user_id == folder.owner_id or await session.get(User, user_id) is None:
        raise HTTPException(404, "not_found")
    if await session.get(FolderMember, (folder_id, user_id)) is None:
        session.add(FolderMember(folder_id=folder_id, user_id=user_id))
        await session.commit()
    return Response(status_code=204)


@router.delete("/{folder_id}/members/{user_id}", status_code=204)
async def remove_member(folder_id: int, user_id: int, session: SessionDep, user: CurrentUser):
    """The owner can remove anyone; a member can remove themselves (leave the folder)."""
    await get_folder(session, folder_id, user, owner_only=user_id != user.id)
    member = await session.get(FolderMember, (folder_id, user_id))
    if member:
        await session.delete(member)
        await session.commit()
    return Response(status_code=204)
