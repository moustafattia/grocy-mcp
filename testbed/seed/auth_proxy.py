"""HTTP auth shim that turns a disposable fixed key into a Grocy web session."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import httpx

from testbed.seed.session import GrocySessionClient


class _ProxyServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_cls, proxy):  # type: ignore[no-untyped-def]
        super().__init__(server_address, handler_cls)
        self.proxy = proxy


class _ProxyHandler(BaseHTTPRequestHandler):
    server: _ProxyServer

    def _handle(self) -> None:
        proxy = self.server.proxy
        provided_key = self.headers.get("GROCY-API-KEY") or ""
        if provided_key != proxy.api_key:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized testbed key")
            return

        body = None
        if self.command in {"POST", "PUT", "PATCH"}:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""

        headers = {
            key: value
            for key, value in self.headers.items()
            if key.casefold() not in {"host", "content-length", "grocy-api-key"}
        }
        request_url = f"{proxy.backend_base}{self.path}"
        with httpx.Client(
            follow_redirects=False,
            timeout=60.0,
            cookies=proxy.session.client.cookies,
        ) as client:
            response = client.request(self.command, request_url, content=body, headers=headers)

        self.send_response(response.status_code)
        for key, value in response.headers.items():
            if key.casefold() in {"content-length", "connection", "transfer-encoding"}:
                continue
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.content)

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle()

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def do_PUT(self) -> None:  # noqa: N802
        self._handle()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class GrocyAuthProxy:
    """Expose a fixed testbed key by proxying to a logged-in Grocy web session."""

    def __init__(
        self,
        proxy_url: str,
        backend_base: str,
        api_key: str,
        username: str,
        password: str,
    ) -> None:
        self.proxy_url = proxy_url
        self.backend_base = backend_base.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self._server: _ProxyServer | None = None
        self._thread: threading.Thread | None = None
        self.session = GrocySessionClient(self.backend_base, self.username, self.password)

    def __enter__(self) -> GrocyAuthProxy:
        self.session.login()
        parsed = urlparse(self.proxy_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9284
        self._server = _ProxyServer((host, port), _ProxyHandler, self)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.session.close()
