from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, SessionDep, accessible_folder_ids, get_folder, get_item
from app.models import Folder, Item, ItemField, User
from app.schemas import FieldIn, FieldPatch, ItemIn, ItemOut, ItemPatch, ItemShort
from app.text import is_secret_key, normalize, utcnow

router = APIRouter(tags=["items"])


def _to_out(item: Item) -> ItemOut:
    return ItemOut(
        id=item.id,
        title=item.title,
        folder_id=item.folder_id,
        folder_name=item.folder.name,
        fields=item.fields,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _add_fields(session: AsyncSession, item_id: int, fields: list[FieldIn]) -> None:
    last = await session.scalar(
        select(func.max(ItemField.position)).where(ItemField.item_id == item_id)
    )
    start = 0 if last is None else last + 1
    for pos, f in enumerate(fields, start):
        secret = is_secret_key(f.key) if f.is_secret is None else f.is_secret
        session.add(
            ItemField(item_id=item_id, key=f.key, value=f.value, is_secret=secret, position=pos)
        )


async def _reload(session: AsyncSession, item_id: int, user: User) -> ItemOut:
    return _to_out(await get_item(session, item_id, user))


@router.get("/folders/{folder_id}/items", response_model=list[ItemShort])
async def list_items(folder_id: int, session: SessionDep, user: CurrentUser):
    folder = await get_folder(session, folder_id, user)
    rows = await session.execute(
        select(Item.id, Item.title).where(Item.folder_id == folder_id).order_by(Item.title_norm)
    )
    return [
        ItemShort(id=id_, title=title, folder_id=folder.id, folder_name=folder.name)
        for id_, title in rows
    ]


@router.post("/folders/{folder_id}/items", response_model=ItemOut, status_code=201)
async def create_item(folder_id: int, body: ItemIn, session: SessionDep, user: CurrentUser):
    await get_folder(session, folder_id, user)
    item = Item(
        folder_id=folder_id,
        title=body.title,
        title_norm=normalize(body.title),
        created_by_id=user.id,
    )
    session.add(item)
    await session.flush()
    await _add_fields(session, item.id, body.fields)
    await session.commit()
    return await _reload(session, item.id, user)


@router.get("/items/search", response_model=list[ItemShort])
async def search_items(
    session: SessionDep,
    user: CurrentUser,
    q: str = Query(min_length=1, max_length=128),
    limit: int = Query(30, ge=1, le=100),
):
    """Title search across every folder the user can see: exact match, then prefix, then rest."""
    needle = normalize(q)
    rank = case(
        (Item.title_norm == needle, 0),
        (Item.title_norm.startswith(needle, autoescape=True), 1),
        else_=2,
    )
    rows = await session.execute(
        select(Item.id, Item.title, Item.folder_id, Folder.name)
        .join(Folder, Folder.id == Item.folder_id)
        .where(
            Item.folder_id.in_(accessible_folder_ids(user)),
            Item.title_norm.contains(needle, autoescape=True),
        )
        .order_by(rank, Item.title_norm)
        .limit(limit)
    )
    return [
        ItemShort(id=id_, title=title, folder_id=folder_id, folder_name=folder_name)
        for id_, title, folder_id, folder_name in rows
    ]


@router.get("/items/{item_id}", response_model=ItemOut)
async def read_item(item_id: int, session: SessionDep, user: CurrentUser):
    return await _reload(session, item_id, user)


@router.patch("/items/{item_id}", response_model=ItemOut)
async def update_item(item_id: int, body: ItemPatch, session: SessionDep, user: CurrentUser):
    item = await get_item(session, item_id, user)
    if body.title is not None:
        item.title = body.title
        item.title_norm = normalize(body.title)
    if body.folder_id is not None and body.folder_id != item.folder_id:
        await get_folder(session, body.folder_id, user)
        item.folder_id = body.folder_id
    item.updated_at = utcnow()
    await session.commit()
    return await _reload(session, item_id, user)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, session: SessionDep, user: CurrentUser):
    item = await get_item(session, item_id, user)
    await session.delete(item)
    await session.commit()
    return Response(status_code=204)


# --- fields ---

@router.post("/items/{item_id}/fields", response_model=ItemOut)
async def add_fields(item_id: int, body: list[FieldIn], session: SessionDep, user: CurrentUser):
    item = await get_item(session, item_id, user)
    await _add_fields(session, item_id, body)
    item.updated_at = utcnow()
    await session.commit()
    return await _reload(session, item_id, user)


def _get_field(item: Item, field_id: int) -> ItemField:
    field = next((f for f in item.fields if f.id == field_id), None)
    if field is None:
        raise HTTPException(404, "not_found")
    return field


@router.patch("/items/{item_id}/fields/{field_id}", response_model=ItemOut)
async def update_field(
    item_id: int, field_id: int, body: FieldPatch, session: SessionDep, user: CurrentUser
):
    item = await get_item(session, item_id, user)
    field = _get_field(item, field_id)
    for name, value in body.model_dump(exclude_none=True).items():
        setattr(field, name, value)
    item.updated_at = utcnow()
    await session.commit()
    return await _reload(session, item_id, user)


@router.delete("/items/{item_id}/fields/{field_id}", response_model=ItemOut)
async def delete_field(item_id: int, field_id: int, session: SessionDep, user: CurrentUser):
    item = await get_item(session, item_id, user)
    field = _get_field(item, field_id)
    await session.delete(field)
    item.updated_at = utcnow()
    await session.commit()
    return await _reload(session, item_id, user)
