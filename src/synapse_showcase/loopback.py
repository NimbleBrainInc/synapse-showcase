"""Loopback HTTP for the guide: `/mcp` for native clients and `/agent/mcp` for an external agent."""

import contextlib

import uvicorn
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Mount
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from synapse_showcase.guide import Guide

DEFAULT_PORT = 27249
MAX_BODY = 64 * 1024
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})
# Marks an intended local client. It is not authentication against other local processes.
CLIENT_HEADER = ("x-showcase-client", "local")


def create_http_app(guide: Guide) -> ASGIApp:
    native = guide.make_server().http_app(path="/mcp")
    agent = guide.make_server(external=True).http_app(path="/mcp")

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette):
        async with native.lifespan(native), agent.lifespan(agent):
            yield

    routes = Starlette(
        routes=[Mount("/agent", app=agent), Mount("", app=native)], lifespan=lifespan
    )
    return LocalOnly(routes)


def run_http(guide: Guide, port: int = DEFAULT_PORT) -> None:
    """Serve on 127.0.0.1 only. A managed deployment supplies its own authenticated transport."""
    if not 0 <= port <= 65535:
        raise ValueError("Choose a valid local port.")
    uvicorn.run(
        create_http_app(guide),
        host="127.0.0.1",
        port=port,
        access_log=False,
        timeout_graceful_shutdown=5,
    )


class LocalOnly:
    """Admit only local MCP clients: a loopback Host, no browser Origin, the client header and a
    body of at most 64 KiB. Anything else is answered here and never reaches MCP."""

    def __init__(self, app: ASGIApp, client_header: tuple[str, str] = CLIENT_HEADER):
        self.app = app
        self.client_header = client_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body += message.get("body", b"")
            if len(body) > MAX_BODY:
                await PlainTextResponse("Request too large\n", 413)(scope, receive, send)
                return
            if not message.get("more_body"):
                break
        answer = self._answer(scope)
        if answer is not None:
            await answer(scope, receive, send)
            return
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)

    def _answer(self, scope: Scope) -> Response | None:
        headers = Headers(scope=scope)
        if _hostname(headers.get("host", "")) not in LOCAL_HOSTS:
            return PlainTextResponse("Invalid Host header\n", 403)
        if "origin" in headers:
            return PlainTextResponse("Use the MCP app bridge.\n", 403)
        path = scope["path"]
        if path == "/health":
            return JSONResponse({"ok": True, "app": "synapse-showcase"})
        if path not in ("/mcp", "/agent/mcp"):
            return PlainTextResponse("Not found\n", 404)
        name, value = self.client_header
        if headers.get(name) != value:
            return PlainTextResponse("Local MCP client header required\n", 403)
        return None


def _hostname(host: str) -> str:
    host = host.strip().lower()
    if host.startswith("["):
        return host.partition("]")[0] + "]"
    return host.partition(":")[0]
