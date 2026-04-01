"""Session-cookie bootstrap client for disposable Grocy testbed instances."""

from __future__ import annotations

from html.parser import HTMLParser
import time
from urllib.parse import urljoin

import httpx


class _LoginFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict] = []
        self._current: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if tag == "form":
            self._current = {
                "action": attr_map.get("action", ""),
                "method": attr_map.get("method", "post").casefold(),
                "inputs": [],
            }
            return
        if tag == "input" and self._current is not None:
            self._current["inputs"].append(attr_map)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._current is not None:
            self.forms.append(self._current)
            self._current = None


class GrocySessionClient:
    """Minimal web-session client for bootstrapping a disposable Grocy instance."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.client = httpx.Client(base_url=self.base_url, follow_redirects=True, timeout=30.0)

    def close(self) -> None:
        self.client.close()

    def _discover_login_form(self) -> tuple[str, dict[str, str]]:
        for candidate in (f"{self.base_url}/login", self.base_url):
            response = self.client.get(candidate)
            parser = _LoginFormParser()
            parser.feed(response.text)
            for form in parser.forms:
                inputs = form["inputs"]
                password_input = next(
                    (item for item in inputs if item.get("type", "").casefold() == "password"),
                    None,
                )
                if password_input is None:
                    continue
                username_input = next(
                    (
                        item
                        for item in inputs
                        if item.get("name")
                        and item.get("type", "text").casefold()
                        not in {"hidden", "password", "submit", "button"}
                    ),
                    None,
                )
                if username_input is None:
                    continue
                payload = {
                    item["name"]: item.get("value", "")
                    for item in inputs
                    if item.get("name") and item.get("type", "text").casefold() == "hidden"
                }
                payload[username_input["name"]] = self.username
                payload[password_input["name"]] = self.password
                return urljoin(str(response.url), form.get("action") or str(response.url)), payload
        raise RuntimeError("Could not discover a Grocy login form.")

    def login(self, retries: int = 20, retry_delay: float = 2.0) -> None:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                action, payload = self._discover_login_form()
                response = self.client.post(action, data=payload)
                response.raise_for_status()
                check = self.client.get(
                    f"{self.base_url}/api/system/info", headers={"Accept": "application/json"}
                )
                if check.status_code >= 400:
                    raise RuntimeError(
                        f"Grocy session login succeeded but API access failed ({check.status_code})."
                    )
                return
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt >= retries:
                    raise
                last_error = exc
            except httpx.HTTPError as exc:
                if attempt >= retries:
                    raise
                last_error = exc
            except RuntimeError as exc:
                if (
                    not str(exc).startswith("Could not discover a Grocy login form.")
                    or attempt >= retries
                ):
                    raise
                last_error = exc
            time.sleep(retry_delay)
        raise RuntimeError(
            "Grocy session login failed after transient startup retries."
        ) from last_error

    def api_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = {"Accept": "application/json", **kwargs.pop("headers", {})}
        response = self.client.request(
            method, f"{self.base_url}/api{path}", headers=headers, **kwargs
        )
        response.raise_for_status()
        return response

    def get_objects(self, entity: str) -> list[dict]:
        return self.api_request("GET", f"/objects/{entity}").json()

    def create_object(self, entity: str, data: dict) -> int:
        return self.api_request("POST", f"/objects/{entity}", json=data).json()["created_object_id"]

    def update_object(self, entity: str, obj_id: int, data: dict) -> None:
        self.api_request("PUT", f"/objects/{entity}/{obj_id}", json=data)

    def delete_object(self, entity: str, obj_id: int) -> None:
        self.api_request("DELETE", f"/objects/{entity}/{obj_id}")

    def add_stock(self, product_id: int, amount: float) -> None:
        self.api_request("POST", f"/stock/products/{product_id}/add", json={"amount": amount})

    def get_shopping_list(self, list_id: int) -> list[dict]:
        items = self.get_objects("shopping_list")
        return [item for item in items if int(item.get("shopping_list_id", 0)) == int(list_id)]
