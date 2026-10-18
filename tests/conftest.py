import os

os.environ.update(API_KEY="test-key", ADMIN_TELEGRAM_ID="1", DATABASE_URL="sqlite+aiosqlite://")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

ADMIN = {"X-Telegram-Id": "1"}


def tg(telegram_id: int) -> dict:
    return {"X-Telegram-Id": str(telegram_id)}


@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)

    @event.listens_for(engine.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-API-Key": "test-key"}
    ) as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def admin(client):
    r = await client.post("/auth/register", json={"name": "Sasha"}, headers=ADMIN)
    assert r.status_code == 200
    return ADMIN


async def invite_user(client, telegram_id: int, name: str) -> dict:
    code = (await client.post("/invites", headers=ADMIN)).json()["code"]
    r = await client.post(
        "/auth/register", json={"name": name, "invite_code": code}, headers=tg(telegram_id)
    )
    assert r.status_code == 200, r.text
    return tg(telegram_id)
