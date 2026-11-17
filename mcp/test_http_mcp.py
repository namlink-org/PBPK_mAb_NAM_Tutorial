#!/usr/bin/env python3
"""End-to-end checks of the HTTP server on a real port.

Covers OAuth discovery and login with the MCP SDK's own client, both protocol
generations, the bearer-token requirement, the Host allow-list, REST input
handling, one-run-at-a-time with the server staying responsive, and the
optional MCP_MODERN_ONLY gate.

Run from the repository root:
    python mcp/test_http_mcp.py
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = free_port()
BASE = f"http://localhost:{PORT}"
os.environ.update({"PBPK_REPO_PATH": str(HERE.parent), "PORT": str(PORT), "MCP_BASE_URL": BASE,
                   "MCP_TEST_TOKEN": "test-http-mcp"})
os.environ.pop("MCP_MODERN_ONLY", None)
sys.path.insert(0, str(HERE))

import httpx2 as httpx  # noqa: E402
import uvicorn  # noqa: E402
from mcp import ClientSession  # noqa: E402
from mcp.client.auth import OAuthClientProvider, TokenStorage  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata  # noqa: E402

import server as core  # noqa: E402
import server_http  # noqa: E402

EXPECTED_TOOLS = {"check_prerequisites", "get_pipeline_status", "get_fold_errors", "get_accuracy_summary",
                  "query_study_design", "get_molecule_info", "run_docker_command"}
FAILURES = 0


def check(cond, msg):
    global FAILURES
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILURES += 1


def rpc(method, params=None, token="test-http-mcp", version="2026-07-28", host=None, rid=1):
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if version == "2026-07-28":
        headers["Mcp-Method"] = method
        if method == "tools/call":
            headers["Mcp-Name"] = params["name"]
        params = {**(params or {}), "_meta": {
            "io.modelcontextprotocol/protocolVersion": version,
            "io.modelcontextprotocol/clientCapabilities": {},
            "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"}}}
    if version:
        headers["MCP-Protocol-Version"] = version
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if host:
        headers["Host"] = host
    body = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
    return httpx.post(BASE + "/mcp", headers=headers, json=body, timeout=30)


def sse_json(r):
    text = r.text
    if text.lstrip().startswith("{"):
        return json.loads(text)
    return json.loads(next(line[5:] for line in text.splitlines() if line.startswith("data:")))


class MemoryStorage(TokenStorage):
    def __init__(self):
        self.tokens = self.client = None

    async def get_tokens(self):
        return self.tokens

    async def set_tokens(self, tokens):
        self.tokens = tokens

    async def get_client_info(self):
        return self.client

    async def set_client_info(self, info):
        self.client = info


async def sdk_client_session():
    """Log in exactly as an MCP client does: discovery, registration, PKCE, then tool calls."""
    redirect = {}

    async def on_redirect(url: str) -> None:
        r = httpx.get(url, follow_redirects=False, timeout=30)
        redirect["location"] = r.headers["location"]

    async def on_callback() -> AuthorizationCodeResult:
        q = parse_qs(urlparse(redirect["location"]).query)
        return AuthorizationCodeResult(code=q["code"][0], state=q.get("state", [None])[0],
                                       iss=q.get("iss", [None])[0]) \
            if "iss" in AuthorizationCodeResult.model_fields else \
            AuthorizationCodeResult(code=q["code"][0], state=q.get("state", [None])[0])

    auth = OAuthClientProvider(
        server_url=BASE + "/mcp",
        client_metadata=OAuthClientMetadata(client_name="sdk-test", redirect_uris=["http://localhost:53682/callback"],
                                            token_endpoint_auth_method="none"),
        storage=MemoryStorage(), redirect_handler=on_redirect, callback_handler=on_callback)
    async with httpx.AsyncClient(auth=auth, timeout=60) as http:
        async with streamable_http_client(BASE + "/mcp", http_client=http) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as s:
                init = await s.initialize()
                tools = await s.list_tools()
                res = await s.call_tool("get_accuracy_summary", {})
                bad = await s.call_tool("get_fold_errors", {"species": "rat"})
                low = await s.call_tool("get_fold_errors", {"molecule": "nivolumab", "metric": "cmax"})
                return init, tools, res, bad, low


def payload(res):
    sc = res.structured_content
    if sc is None:
        sc = json.loads(res.content[0].text)
    return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc


def main():
    srv = uvicorn.Server(uvicorn.Config(server_http.app, log_level="error"))
    threading.Thread(target=srv.run, kwargs={"sockets": server_http.bind_sockets("127.0.0.1", PORT)},
                     daemon=True).start()
    while not srv.started:
        time.sleep(0.05)

    print("-- startup --")
    t0 = time.time()
    httpx.post(BASE + "/api/pipeline-status")
    check(time.time() - t0 < 1.0, f"new connection to localhost is fast ({time.time() - t0:.2f}s)")
    dup = subprocess.run([sys.executable, str(HERE / "server_http.py")], env={**os.environ, "PORT": str(PORT)},
                         capture_output=True, text=True, timeout=60)
    check(dup.returncode != 0 and "Is another server already using port" in dup.stderr,
          "second server on a busy port exits with a clear message")

    print("-- discovery --")
    r = httpx.post(BASE + "/mcp", json={}, headers={"Accept": "application/json, text/event-stream"})
    check(r.status_code == 401, "request without a token gets 401")
    meta_url = r.headers.get("www-authenticate", "").split('resource_metadata="')[-1].rstrip('"')
    prm = httpx.get(meta_url)
    check(prm.status_code == 200, f"advertised resource metadata resolves ({meta_url})")
    asm = httpx.get(BASE + "/.well-known/oauth-authorization-server")
    check(asm.status_code == 200, "authorization-server metadata at the RFC 8414 location")
    check(prm.json()["authorization_servers"][0] == asm.json()["issuer"], "issuer is identical in both documents")

    print("-- MCP SDK client: OAuth login, negotiation, tool calls --")
    init, tools, res, bad, low = asyncio.run(sdk_client_session())
    check(bool(init.instructions), "server instructions reach the client")
    check({t.name for t in tools.tools} == EXPECTED_TOOLS, "all 7 tools listed under the stdio names")
    overall = payload(res)["overall"]
    check((overall["n_evaluated"], overall["n_within_2fold"]) == (109, 96), "get_accuracy_summary returns 96 of 109")
    check("allowed_values" in payload(bad), "unknown species returns the allowed values, not an empty table")
    check(payload(low)["total_rows"] > 0, "lower-case molecule and metric still match")

    print("-- raw protocol requests --")
    r = rpc("tools/list")
    check(r.status_code == 200 and {t["name"] for t in sse_json(r)["result"]["tools"]} == EXPECTED_TOOLS,
          "2026-07-28 stateless tools/list")
    init_body = {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}
    r = rpc("initialize", init_body, version=None)
    check(r.status_code == 200, "handshake-era initialize (no version header) is accepted")
    check(rpc("tools/list", token="wrong").status_code == 401, "invalid token gets 401")
    check(rpc("tools/list", host="evil.example").status_code == 400, "foreign Host header is rejected")
    check(httpx.get(BASE + "/docs", headers={"Host": "evil.example"}).status_code == 400,
          "foreign Host header is rejected on REST")

    print("-- REST --")
    r = httpx.post(BASE + "/api/fold-errors", json={"molecule": "nivolumab"})
    check(r.status_code == 200 and r.json()["total_rows"] > 0, "REST molecule filter ignores case")
    check(httpx.post(BASE + "/api/fold-errors", json={"molecule": "Foo"}).status_code == 422, "REST unknown molecule is 422")
    check(httpx.post(BASE + "/api/fold-errors").json()["total_rows"] == 132, "REST fold-errors without a body returns 132 rows")
    check(httpx.post(BASE + "/api/run-pipeline", json={"command": "rm"}).status_code == 422, "REST rejects unknown commands")

    print("-- one pipeline run at a time, server stays responsive --")
    original = core._launcher_args
    core._launcher_args = lambda command: [sys.executable, "-c", "import time; time.sleep(4); print('done')"]
    results = {}

    def run(tag):
        results[tag] = httpx.post(BASE + "/api/run-pipeline", json={"command": "summary"}, timeout=60)

    httpx.get(BASE + "/openapi.json")  # built on first request; warm it so only blocking is measured
    t1 = threading.Thread(target=run, args=("first",))
    t1.start()
    time.sleep(1)
    t0 = time.time()
    httpx.post(BASE + "/api/pipeline-status")
    latency = time.time() - t0
    second = rpc("tools/call", {"name": "run_docker_command", "arguments": {"command": "summary"}})
    t1.join()
    core._launcher_args = original
    check(latency < 1.0, f"REST answers during a pipeline run ({latency:.2f}s)")
    check(results["first"].status_code == 200 and results["first"].json()["status"] == "OK", "first run completes")
    second_status = json.loads(sse_json(second)["result"]["content"][0]["text"])["status"]
    check(second_status == "BUSY", "a second run over MCP is refused with BUSY")

    print("-- MCP_MODERN_ONLY gate --")
    port2 = free_port()
    env = {**os.environ, "PORT": str(port2), "MCP_BASE_URL": f"http://localhost:{port2}", "MCP_MODERN_ONLY": "true"}
    proc = subprocess.Popen([sys.executable, str(HERE / "server_http.py")], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                httpx.get(f"http://localhost:{port2}/openapi.json", timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        r = httpx.post(f"http://localhost:{port2}/mcp", headers={"Accept": "application/json, text/event-stream"},
                       json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": init_body})
        check(r.status_code == 400 and r.json()["error"]["code"] == -32022, "strict mode rejects handshake clients with -32022")
    finally:
        proc.terminate()

    srv.should_exit = True
    print("All HTTP MCP checks passed" if not FAILURES else f"{FAILURES} HTTP MCP check(s) FAILED")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
