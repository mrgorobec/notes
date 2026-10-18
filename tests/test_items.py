from tests.conftest import ADMIN


async def make_folder(client, name="Акаунти") -> int:
    r = await client.post("/folders", json={"name": name}, headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def make_item(client, folder_id, title, fields=()) -> dict:
    r = await client.post(
        f"/folders/{folder_id}/items",
        json={"title": title, "fields": list(fields)},
        headers=ADMIN,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_folder_crud(client, admin):
    fid = await make_folder(client)
    assert (await client.post("/folders", json={"name": "Акаунти"}, headers=ADMIN)).status_code == 409

    await make_item(client, fid, "Дія")
    folders = (await client.get("/folders", headers=ADMIN)).json()
    assert folders == [
        {"id": fid, "name": "Акаунти", "owner_name": "Sasha", "is_owner": True,
         "is_shared": False, "item_count": 1}
    ]

    r = await client.patch(f"/folders/{fid}", json={"name": "Логіни"}, headers=ADMIN)
    assert r.json()["name"] == "Логіни"

    assert (await client.delete(f"/folders/{fid}", headers=ADMIN)).status_code == 204
    assert (await client.get("/folders", headers=ADMIN)).json() == []
    assert (await client.get("/items/search", params={"q": "Дія"}, headers=ADMIN)).json() == []


async def test_item_fields_and_secrets(client, admin):
    fid = await make_folder(client)
    item = await make_item(client, fid, "Дія", [
        {"key": "логін", "value": "0501234567"},
        {"key": "Пароль", "value": "qwerty"},
        {"key": "PIN-код", "value": "1234"},
        {"key": "shipping", "value": "Nova Poshta"},
    ])
    secrets = {f["key"]: f["is_secret"] for f in item["fields"]}
    assert secrets == {"логін": False, "Пароль": True, "PIN-код": True, "shipping": False}
    assert [f["key"] for f in item["fields"]] == ["логін", "Пароль", "PIN-код", "shipping"]

    login_id = item["fields"][0]["id"]
    item = (await client.patch(
        f"/items/{item['id']}/fields/{login_id}", json={"value": "0679999999"}, headers=ADMIN
    )).json()
    assert item["fields"][0]["value"] == "0679999999"

    item = (await client.post(
        f"/items/{item['id']}/fields", json=[{"key": "email", "value": "a@b.c"}], headers=ADMIN
    )).json()
    assert item["fields"][-1]["key"] == "email"

    item = (await client.delete(f"/items/{item['id']}/fields/{login_id}", headers=ADMIN)).json()
    assert "логін" not in [f["key"] for f in item["fields"]]


async def test_search_ranking_and_case(client, admin):
    fid = await make_folder(client)
    for title in ["Дія для бізнесу", "Дія", "Нова Дія", "Gmail"]:
        await make_item(client, fid, title)
    found = (await client.get("/items/search", params={"q": "  ДІЯ "}, headers=ADMIN)).json()
    assert [i["title"] for i in found] == ["Дія", "Дія для бізнесу", "Нова Дія"]
    assert found[0]["folder_name"] == "Акаунти"

    # LIKE wildcards are literal
    assert (await client.get("/items/search", params={"q": "%"}, headers=ADMIN)).json() == []


async def test_rename_move_delete_item(client, admin):
    a, b = await make_folder(client, "A"), await make_folder(client, "B")
    item = await make_item(client, a, "Nike")
    item = (await client.patch(
        f"/items/{item['id']}", json={"title": "Nike Air", "folder_id": b}, headers=ADMIN
    )).json()
    assert (item["title"], item["folder_name"]) == ("Nike Air", "B")

    assert (await client.delete(f"/items/{item['id']}", headers=ADMIN)).status_code == 204
    assert (await client.get(f"/items/{item['id']}", headers=ADMIN)).status_code == 404
