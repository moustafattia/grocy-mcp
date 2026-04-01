"""Async HTTP client for the Grocy REST API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from grocy_mcp.exceptions import (
    GrocyAuthError,
    GrocyNotFoundError,
    GrocyServerError,
    GrocyValidationError,
)

_TRANSIENT_CODES = {502, 503, 504}
_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.0


class GrocyClient:
    """Thin async wrapper around the Grocy REST API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base = base_url.rstrip("/") + "/api"
        self._client = httpx.AsyncClient(
            base_url=self._base,
            headers={"GROCY-API-KEY": api_key, "Accept": "application/json"},
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0),
        )

    async def __aenter__(self) -> GrocyClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await self._client.request(method, path, **kwargs)
            except httpx.TransportError as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_BACKOFF)
                    continue
                raise GrocyServerError(f"Connection failed: {e}") from e

            if resp.status_code in _TRANSIENT_CODES and attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_BACKOFF)
                continue

            self._raise_for_status(resp)
            return resp

        raise GrocyServerError("Max retries exceeded") if last_exc is None else last_exc

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        body = resp.text
        match resp.status_code:
            case 401 | 403:
                raise GrocyAuthError(f"Auth failed ({resp.status_code}): {body}")
            case 400:
                raise GrocyValidationError(f"Validation error: {body}")
            case 404:
                raise GrocyNotFoundError(f"Not found: {body}")
            case code if code >= 500:
                raise GrocyServerError(f"Server error ({code}): {body}")
            case code:
                raise GrocyServerError(f"HTTP error ({code}): {body}")

    # --- Generic CRUD ---

    async def get_objects(self, entity: str, query: str | None = None) -> list[dict]:
        params = {"query[]": query} if query else None
        resp = await self._request("GET", f"/objects/{entity}", params=params)
        return resp.json()

    async def get_object(self, entity: str, obj_id: int) -> dict:
        resp = await self._request("GET", f"/objects/{entity}/{obj_id}")
        return resp.json()

    async def create_object(self, entity: str, data: dict) -> int:
        resp = await self._request("POST", f"/objects/{entity}", json=data)
        return resp.json()["created_object_id"]

    async def update_object(self, entity: str, obj_id: int, data: dict) -> None:
        await self._request("PUT", f"/objects/{entity}/{obj_id}", json=data)

    async def delete_object(self, entity: str, obj_id: int) -> None:
        await self._request("DELETE", f"/objects/{entity}/{obj_id}")

    # --- Stock ---

    async def get_stock(self) -> list[dict]:
        resp = await self._request("GET", "/stock")
        return resp.json()

    async def get_stock_product(self, product_id: int) -> dict:
        resp = await self._request("GET", f"/stock/products/{product_id}")
        return resp.json()

    async def add_stock(self, product_id: int, amount: float, **kwargs: Any) -> Any:
        data = {"amount": amount, **kwargs}
        resp = await self._request("POST", f"/stock/products/{product_id}/add", json=data)
        return resp.json()

    async def consume_stock(self, product_id: int, amount: float, **kwargs: Any) -> Any:
        data = {"amount": amount, **kwargs}
        resp = await self._request("POST", f"/stock/products/{product_id}/consume", json=data)
        return resp.json()

    async def transfer_stock(self, product_id: int, amount: float, to_location_id: int) -> Any:
        data = {"amount": amount, "location_id_to": to_location_id}
        resp = await self._request("POST", f"/stock/products/{product_id}/transfer", json=data)
        return resp.json()

    async def inventory_stock(self, product_id: int, new_amount: float) -> Any:
        data = {"new_amount": new_amount}
        resp = await self._request("POST", f"/stock/products/{product_id}/inventory", json=data)
        return resp.json()

    async def open_stock(self, product_id: int, amount: float = 1) -> Any:
        data = {"amount": amount}
        resp = await self._request("POST", f"/stock/products/{product_id}/open", json=data)
        return resp.json()

    async def get_volatile_stock(self) -> dict:
        resp = await self._request("GET", "/stock/volatile")
        return resp.json()

    async def get_stock_by_barcode(self, barcode: str) -> dict:
        resp = await self._request("GET", f"/stock/products/by-barcode/{barcode}")
        return resp.json()

    # --- Shopping Lists ---

    async def get_shopping_list(self, list_id: int = 1) -> list[dict]:
        items = await self.get_objects("shopping_list")
        return [i for i in items if i.get("shopping_list_id") == list_id]

    async def add_shopping_list_item(
        self, product_id: int, amount: float = 1, shopping_list_id: int = 1, note: str | None = None
    ) -> int:
        data = {"product_id": product_id, "amount": amount, "shopping_list_id": shopping_list_id}
        if note:
            data["note"] = note
        return await self.create_object("shopping_list", data)

    async def update_shopping_list_item(self, item_id: int, data: dict) -> None:
        await self.update_object("shopping_list", item_id, data)

    async def remove_shopping_list_item(self, item_id: int) -> None:
        await self.delete_object("shopping_list", item_id)

    async def clear_shopping_list(self, list_id: int = 1) -> None:
        await self._request("POST", "/stock/shoppinglist/clear", json={"list_id": list_id})

    async def add_missing_products_to_shopping_list(self, list_id: int = 1) -> None:
        await self._request(
            "POST", "/stock/shoppinglist/add-missing-products", json={"list_id": list_id}
        )

    # --- Recipes ---

    async def get_recipes(self) -> list[dict]:
        return await self.get_objects("recipes")

    async def get_recipe(self, recipe_id: int) -> dict:
        return await self.get_object("recipes", recipe_id)

    async def get_recipe_fulfillment(self, recipe_id: int) -> dict:
        resp = await self._request("GET", f"/recipes/{recipe_id}/fulfillment")
        return resp.json()

    async def consume_recipe(self, recipe_id: int) -> None:
        await self._request("POST", f"/recipes/{recipe_id}/consume")

    async def add_recipe_to_shopping_list(self, recipe_id: int) -> None:
        await self._request(
            "POST", f"/recipes/{recipe_id}/add-not-fulfilled-products-to-shoppinglist"
        )

    # --- Chores ---

    async def get_chores(self) -> list[dict]:
        resp = await self._request("GET", "/chores")
        return resp.json()

    async def get_chore(self, chore_id: int) -> dict:
        resp = await self._request("GET", f"/chores/{chore_id}")
        return resp.json()

    async def execute_chore(self, chore_id: int, done_by: int | None = None) -> None:
        data: dict[str, Any] = {}
        if done_by is not None:
            data["done_by"] = done_by
        await self._request("POST", f"/chores/{chore_id}/execute", json=data)

    async def get_chore_executions(self, chore_id: int) -> list[dict]:
        all_execs = await self.get_objects("chores_log")
        return [e for e in all_execs if e.get("chore_id") == chore_id]

    async def undo_chore_execution(self, execution_id: int) -> None:
        await self._request("POST", f"/chores/executions/{execution_id}/undo")

    async def print_chore_label(self, chore_id: int) -> dict:
        resp = await self._request("GET", f"/chores/{chore_id}/printlabel")
        return resp.json()

    # --- Batteries ---

    async def get_batteries(self) -> list[dict]:
        resp = await self._request("GET", "/batteries")
        return resp.json()

    async def get_battery(self, battery_id: int) -> dict:
        resp = await self._request("GET", f"/batteries/{battery_id}")
        return resp.json()

    async def charge_battery(self, battery_id: int, tracked_time: str | None = None) -> dict:
        data: dict[str, Any] = {}
        if tracked_time is not None:
            data["tracked_time"] = tracked_time
        resp = await self._request("POST", f"/batteries/{battery_id}/charge", json=data)
        return resp.json()

    async def undo_battery_charge_cycle(self, charge_cycle_id: int) -> None:
        await self._request("POST", f"/batteries/charge-cycles/{charge_cycle_id}/undo")

    async def print_battery_label(self, battery_id: int) -> dict:
        resp = await self._request("GET", f"/batteries/{battery_id}/printlabel")
        return resp.json()

    # --- Tasks ---

    async def get_tasks(self) -> list[dict]:
        resp = await self._request("GET", "/tasks")
        return resp.json()

    async def complete_task(self, task_id: int, done_time: str | None = None) -> dict:
        data: dict[str, Any] = {}
        if done_time is not None:
            data["done_time"] = done_time
        resp = await self._request("POST", f"/tasks/{task_id}/complete", json=data)
        return resp.json()

    async def undo_task(self, task_id: int) -> None:
        await self._request("POST", f"/tasks/{task_id}/undo")

    # --- Calendar ---

    async def get_calendar_ical(self) -> str:
        resp = await self._request("GET", "/calendar/ical")
        return resp.text

    async def get_calendar_sharing_link(self) -> dict:
        resp = await self._request("GET", "/calendar/ical/sharing-link")
        return resp.json()

    # --- Files ---

    async def download_file(
        self,
        group: str,
        file_name_b64: str,
        force_serve_as: str | None = None,
        best_fit_width: int | None = None,
        best_fit_height: int | None = None,
    ) -> tuple[bytes, str | None]:
        params: dict[str, Any] = {}
        if force_serve_as is not None:
            params["force_serve_as"] = force_serve_as
        if best_fit_width is not None:
            params["best_fit_width"] = best_fit_width
        if best_fit_height is not None:
            params["best_fit_height"] = best_fit_height

        resp = await self._request("GET", f"/files/{group}/{file_name_b64}", params=params or None)
        return resp.content, resp.headers.get("Content-Type")

    async def upload_file(self, group: str, file_name_b64: str, content: bytes) -> None:
        await self._request(
            "PUT",
            f"/files/{group}/{file_name_b64}",
            content=content,
            headers={"Content-Type": "application/octet-stream"},
        )

    async def delete_file(self, group: str, file_name_b64: str) -> None:
        await self._request("DELETE", f"/files/{group}/{file_name_b64}")

    # --- Print ---

    async def print_stock_entry_label(self, entry_id: int) -> dict:
        resp = await self._request("GET", f"/stock/entry/{entry_id}/printlabel")
        return resp.json()

    async def print_stock_product_label(self, product_id: int) -> dict:
        resp = await self._request("GET", f"/stock/products/{product_id}/printlabel")
        return resp.json()

    async def print_recipe_label(self, recipe_id: int) -> dict:
        resp = await self._request("GET", f"/recipes/{recipe_id}/printlabel")
        return resp.json()

    async def print_shopping_list_thermal(self) -> dict:
        resp = await self._request("GET", "/print/shoppinglist/thermal")
        return resp.json()

    # --- System ---

    async def get_system_info(self) -> dict:
        resp = await self._request("GET", "/system/info")
        return resp.json()
