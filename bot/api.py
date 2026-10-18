"""Thin HTTP client for the Note API. Every call is made on behalf of one Telegram user."""

from typing import Any

import httpx


class ApiError(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(f"{status}: {code}")
        self.status = status
        self.code = code


class ApiClient:
    def __init__(self, base_url: str, api_key: str):
        self._http = httpx.AsyncClient(
            base_url=base_url, headers={"X-API-Key": api_key}, timeout=10
        )

    def for_user(self, telegram_id: int) -> "UserApi":
        return UserApi(self._http, telegram_id)

    async def close(self) -> None:
        await self._http.aclose()


class UserApi:
    def __init__(self, http: httpx.AsyncClient, telegram_id: int):
        self._http = http
        self._headers = {"X-Telegram-Id": str(telegram_id)}

    async def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        r = await self._http.request(method, path, headers=self._headers, **kwargs)
        if r.is_error:
            try:
                detail = r.json().get("detail")
            except ValueError:
                detail = None
            raise ApiError(r.status_code, detail if isinstance(detail, str) else "error")
        return r.json() if r.content else None

    # --- users ---
    async def register(self, name: str, invite_code: str | None) -> dict:
        return await self._call(
            "POST", "/auth/register", json={"name": name, "invite_code": invite_code}
        )

    async def me(self) -> dict:
        return await self._call("GET", "/auth/me")

    async def create_invite(self) -> dict:
        return await self._call("POST", "/invites")

    async def users(self) -> list[dict]:
        return await self._call("GET", "/users")

    # --- folders ---
    async def folders(self) -> list[dict]:
        return await self._call("GET", "/folders")

    async def folder(self, folder_id: int) -> dict:
        return await self._call("GET", f"/folders/{folder_id}")

    async def create_folder(self, name: str) -> dict:
        return await self._call("POST", "/folders", json={"name": name})

    async def rename_folder(self, folder_id: int, name: str) -> dict:
        return await self._call("PATCH", f"/folders/{folder_id}", json={"name": name})

    async def delete_folder(self, folder_id: int) -> None:
        await self._call("DELETE", f"/folders/{folder_id}")

    async def members(self, folder_id: int) -> list[dict]:
        return await self._call("GET", f"/folders/{folder_id}/members")

    async def add_member(self, folder_id: int, user_id: int) -> None:
        await self._call("PUT", f"/folders/{folder_id}/members/{user_id}")

    async def remove_member(self, folder_id: int, user_id: int) -> None:
        await self._call("DELETE", f"/folders/{folder_id}/members/{user_id}")

    # --- items ---
    async def folder_items(self, folder_id: int) -> list[dict]:
        return await self._call("GET", f"/folders/{folder_id}/items")

    async def create_item(self, folder_id: int, title: str, fields: list[dict]) -> dict:
        return await self._call(
            "POST", f"/folders/{folder_id}/items", json={"title": title, "fields": fields}
        )

    async def search(self, q: str) -> list[dict]:
        return await self._call("GET", "/items/search", params={"q": q})

    async def item(self, item_id: int) -> dict:
        return await self._call("GET", f"/items/{item_id}")

    async def update_item(self, item_id: int, **changes: Any) -> dict:
        return await self._call("PATCH", f"/items/{item_id}", json=changes)

    async def delete_item(self, item_id: int) -> None:
        await self._call("DELETE", f"/items/{item_id}")

    async def add_fields(self, item_id: int, fields: list[dict]) -> dict:
        return await self._call("POST", f"/items/{item_id}/fields", json=fields)

    async def update_field(self, item_id: int, field_id: int, **changes: Any) -> dict:
        return await self._call("PATCH", f"/items/{item_id}/fields/{field_id}", json=changes)

    async def delete_field(self, item_id: int, field_id: int) -> dict:
        return await self._call("DELETE", f"/items/{item_id}/fields/{field_id}")
