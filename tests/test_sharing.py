from tests.conftest import ADMIN, invite_user
from tests.test_items import make_folder, make_item


async def test_folders_are_private_until_shared(client, admin):
    wife = await invite_user(client, 2, "Wife")
    fid = await make_folder(client, "Сім'я")
    item = await make_item(client, fid, "Wi-Fi", [{"key": "пароль", "value": "home123"}])

    assert (await client.get("/folders", headers=wife)).json() == []
    assert (await client.get(f"/items/{item['id']}", headers=wife)).status_code == 404
    assert (await client.get("/items/search", params={"q": "wi"}, headers=wife)).json() == []

    users = (await client.get("/users", headers=ADMIN)).json()
    wife_id = users[0]["id"]
    assert (await client.put(f"/folders/{fid}/members/{wife_id}", headers=ADMIN)).status_code == 204

    folders = (await client.get("/folders", headers=wife)).json()
    assert folders[0]["owner_name"] == "Sasha"
    assert folders[0]["is_owner"] is False
    assert (await client.get(f"/items/{item['id']}", headers=wife)).status_code == 200

    # members can add items, but can't manage the folder
    r = await client.post(f"/folders/{fid}/items", json={"title": "Netflix"}, headers=wife)
    assert r.status_code == 201
    assert (await client.delete(f"/folders/{fid}", headers=wife)).status_code == 403
    assert (await client.get(f"/folders/{fid}/members", headers=wife)).status_code == 403

    # a member can leave
    assert (await client.delete(f"/folders/{fid}/members/{wife_id}", headers=wife)).status_code == 204
    assert (await client.get("/folders", headers=wife)).json() == []


async def test_cannot_move_item_into_foreign_folder(client, admin):
    wife = await invite_user(client, 2, "Wife")
    mine = await make_folder(client, "Mine")
    r = await client.post("/folders", json={"name": "Hers"}, headers=wife)
    hers = r.json()["id"]
    item = await make_item(client, mine, "Secret")
    r = await client.patch(f"/items/{item['id']}", json={"folder_id": hers}, headers=ADMIN)
    assert r.status_code == 404
