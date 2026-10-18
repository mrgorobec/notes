from tests.conftest import ADMIN, invite_user, tg


async def test_bad_api_key(client, admin):
    r = await client.get("/auth/me", headers={**ADMIN, "X-API-Key": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "bad_api_key"


async def test_admin_registers_without_invite(client, admin):
    me = (await client.get("/auth/me", headers=ADMIN)).json()
    assert me["is_admin"] is True
    # idempotent
    again = await client.post("/auth/register", json={"name": "Other"}, headers=ADMIN)
    assert again.json()["name"] == "Sasha"


async def test_unregistered_user(client, admin):
    r = await client.get("/folders", headers=tg(2))
    assert r.status_code == 401
    assert r.json()["detail"] == "not_registered"


async def test_register_requires_valid_invite(client, admin):
    r = await client.post("/auth/register", json={"name": "Wife"}, headers=tg(2))
    assert r.json()["detail"] == "invite_required"
    r = await client.post(
        "/auth/register", json={"name": "Wife", "invite_code": "nope"}, headers=tg(2)
    )
    assert r.json()["detail"] == "invite_invalid"


async def test_invite_is_single_use(client, admin):
    code = (await client.post("/invites", headers=ADMIN)).json()["code"]
    ok = await client.post(
        "/auth/register", json={"name": "Wife", "invite_code": code}, headers=tg(2)
    )
    assert ok.status_code == 200
    assert ok.json()["is_admin"] is False
    reused = await client.post(
        "/auth/register", json={"name": "Stranger", "invite_code": code}, headers=tg(3)
    )
    assert reused.status_code == 403


async def test_only_admin_creates_invites(client, admin):
    wife = await invite_user(client, 2, "Wife")
    r = await client.post("/invites", headers=wife)
    assert r.status_code == 403
