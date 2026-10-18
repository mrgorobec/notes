import secrets
from datetime import timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, SessionDep, SettingsDep, TelegramId
from app.models import Invite, User
from app.schemas import InviteOut, RegisterIn, UserBrief, UserOut
from app.text import as_utc, utcnow

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserOut)
async def register(
    body: RegisterIn, session: SessionDep, settings: SettingsDep, telegram_id: TelegramId
):
    """Idempotent: an existing user is returned as is."""
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        return user

    is_admin = telegram_id == settings.admin_telegram_id
    invite = None
    if not is_admin:
        if not body.invite_code:
            raise HTTPException(403, "invite_required")
        invite = await session.scalar(
            select(Invite).where(Invite.code == body.invite_code, Invite.used_by_id.is_(None))
        )
        if invite is None or as_utc(invite.expires_at) < utcnow():
            raise HTTPException(403, "invite_invalid")

    user = User(telegram_id=telegram_id, name=body.name, is_admin=is_admin)
    session.add(user)
    await session.flush()
    if invite:
        invite.used_by_id = user.id
    await session.commit()
    return user


@router.get("/auth/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.post("/invites", response_model=InviteOut, status_code=201)
async def create_invite(session: SessionDep, settings: SettingsDep, user: AdminUser):
    invite = Invite(
        code=secrets.token_urlsafe(12),
        created_by_id=user.id,
        expires_at=utcnow() + timedelta(hours=settings.invite_ttl_hours),
    )
    session.add(invite)
    await session.commit()
    return invite


@router.get("/users", response_model=list[UserBrief])
async def list_users(session: SessionDep, user: CurrentUser):
    """Everyone except the caller, to pick whom to share a folder with."""
    users = await session.scalars(select(User).where(User.id != user.id).order_by(User.name))
    return users.all()
