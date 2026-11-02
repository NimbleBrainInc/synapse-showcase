"""The HTTP entry point keeps to loopback, local clients and small bodies, and serves real MCP."""

import os
import re
import subprocess
import sys

import httpx

from tests.conftest import over_http, tool_names


def start_http(data_file) -> tuple[subprocess.Popen, str]:
    """Start `python -m synapse_showcase.server --http --port 0` and return it with its URL."""
    process = subprocess.Popen(
        [sys.executable, "-m", "synapse_showcase.server", "--http", "--port", "0"]
        + ["--data-file", str(data_file)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    assert process.stderr is not None
    for line in process.stderr:
        if found := re.search(r"running on (http://127\.0\.0\.1:\d+)", line):
            return process, found.group(1)
    process.kill()
    raise AssertionError("The HTTP entry point never reported its address.")


async def test_http_entry_point_enforces_local_request_boundaries_and_serves_mcp(data_file):
    process, base = start_http(data_file)
    try:
        async with httpx.AsyncClient(base_url=base) as http:
            health = await http.get("/health")
            assert health.status_code == 200
            assert health.json() == {"ok": True, "app": "synapse-showcase"}
            assert (await http.post("/mcp")).status_code == 403
            browser = {"origin": "https://foreign.invalid", "x-showcase-client": "local"}
            assert (await http.post("/mcp", headers=browser)).status_code == 403
            assert (
                await http.get("/health", headers={"host": "foreign.invalid"})
            ).status_code == 403
            assert (await http.post("/mcp", content=b"x" * 65537)).status_code == 413
            assert (await http.get("/elsewhere")).status_code == 404
        async with over_http(base) as client:
            assert "guide_status" in await tool_names(client)
    finally:
        process.terminate()
        process.wait(timeout=10)
