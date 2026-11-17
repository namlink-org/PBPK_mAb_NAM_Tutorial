#!/usr/bin/env python3
"""
NAMLink PBPK mAb Tutorial - HTTP API + MCP Server
==================================================

Runs the 7 pipeline tools over HTTP with a Swagger UI, and exposes an MCP
endpoint for AI clients, all on one port. The tool logic lives in server.py;
this file only adds the HTTP, REST and OAuth layers.

Architecture
------------
- FastAPI serves REST + Swagger UI (/docs, /redoc, /openapi.json, /api/*)
- FastMCP serves the MCP endpoint at /mcp and the OAuth routes at the root
  (/.well-known/*, /register, /authorize, /token, /revoke), where standard
  clients look for them (RFC 8414, RFC 9728)
- LocalOAuthProvider implements OAuth 2.1 with PKCE and approves every local
  client automatically
- Both handshake-era protocol versions (2024-11-05 to 2025-11-25) and the
  stateless 2026-07-28 revision are served; MCP_MODERN_ONLY=true accepts only
  2026-07-28
- Only localhost Host headers are accepted, which blocks DNS-rebinding attacks

Access points
-------------
  GET  /docs                                     Swagger UI
  GET  /redoc                                    ReDoc reference
  GET  /openapi.json                             OpenAPI spec
  POST /api/*                                    REST endpoints
  POST /mcp                                      MCP endpoint (configured by .mcp.json)
  GET  /.well-known/oauth-authorization-server   OAuth discovery

Quickstart
----------
    pip install -r mcp/requirements_http.txt
    python mcp/server_http.py

Environment variables
---------------------
  PBPK_REPO_PATH     Path to repo root (default: one level above this file)
  HOST               Bind address (default: 127.0.0.1)
  PORT               Port (default: 8000)
  MCP_BASE_URL       Public base URL, used as the OAuth issuer (default: http://localhost:PORT)
  MCP_ALLOWED_HOSTS  Extra comma-separated Host names to accept (default: none)
  MCP_TEST_TOKEN     Pre-authorised static bearer token for CI/automated tests
  MCP_MODERN_ONLY    "true" to accept only MCP protocol 2026-07-28 clients
  LOG_LEVEL          Logging verbosity (default: INFO)
"""

import logging
import os
import secrets
import socket
import sys
import time
from pathlib import Path
from typing import Any, Literal, Optional
from urllib.parse import urlparse

os.environ.setdefault("FASTMCP_CHECK_FOR_UPDATES", "off")
os.environ.setdefault("FASTMCP_SHOW_SERVER_BANNER", "false")

import anyio
import fastmcp
import uvicorn
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastmcp.server.auth import AccessToken, OAuthProvider
from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp_types import UNSUPPORTED_PROTOCOL_VERSION
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_PROTOCOL_VERSION
from pydantic import AnyHttpUrl, BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse as StarletteJSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import server as core  # noqa: E402  (single source of the tool logic)

# ---------------------------------------------------------------------------
# Structured logging: silence noisy third-party loggers
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("namlink.server")
for name, level in [("httpx", logging.WARNING), ("httpcore", logging.WARNING), ("uvicorn", logging.WARNING),
                    ("uvicorn.access", logging.WARNING), ("uvicorn.error", logging.INFO),
                    ("starlette", logging.WARNING), ("fastmcp", logging.INFO), ("sse_starlette", logging.WARNING)]:
    logging.getLogger(name).setLevel(level)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
REPO_ROOT = core.REPO_ROOT
_HOST = os.environ.get("HOST", "127.0.0.1")
_PORT = int(os.environ.get("PORT", "8000"))

_MCP_PATH = "/mcp"
_MCP_BASE_URL = os.environ.get("MCP_BASE_URL", f"http://localhost:{_PORT}").rstrip("/")
_MCP_TEST_TOKEN = os.environ.get("MCP_TEST_TOKEN", "")
_MODERN_ONLY = os.environ.get("MCP_MODERN_ONLY", "").strip().lower() in ("1", "true", "yes")

_ALLOWED_HOSTS = sorted({"localhost", "127.0.0.1", "[::1]", urlparse(_MCP_BASE_URL).hostname or "localhost"}
                        | {h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()})

# Cache hint for cacheable MCP results (tools/list, server/discover). The tool
# catalogue is static; "private" because responses sit behind per-client tokens.
_CACHE_TTL_SECONDS = 300
_CACHE_SCOPE = "private"


# ---------------------------------------------------------------------------
# OAuth 2.1 provider: in-memory, auto-approving, local use only
# ---------------------------------------------------------------------------

class LocalOAuthProvider(OAuthProvider):
    """
    In-memory OAuth 2.1 authorization server that approves every request.

    Serves dynamic client registration (RFC 7591), the authorization and
    token endpoints with PKCE, refresh tokens, revocation (RFC 7009) and the
    discovery documents (RFC 8414, RFC 9728). Tokens live in memory and are
    lost on restart; clients then re-authorise automatically.

    If MCP_TEST_TOKEN is set, that token is pre-authorised so automated tests
    can skip the browser flow.
    """

    def __init__(self, base_url: str) -> None:
        super().__init__(
            base_url=base_url,
            client_registration_options=ClientRegistrationOptions(
                enabled=True, valid_scopes=["mcp"], default_scopes=["mcp"],
            ),
            revocation_options=RevocationOptions(enabled=True),
        )
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._access: dict[str, AccessToken] = {}
        self._refresh: dict[str, RefreshToken] = {}

        if _MCP_TEST_TOKEN:
            client_id = "test-ci-client"
            self._clients[client_id] = OAuthClientInformationFull(
                client_id=client_id,
                redirect_uris=[AnyHttpUrl("http://localhost")],
                client_name="NAMLink CI Test Client",
            )
            self._access[_MCP_TEST_TOKEN] = AccessToken(
                token=_MCP_TEST_TOKEN, client_id=client_id, scopes=["mcp"], expires_at=None,
            )
            log.info("Pre-authorized static test token for CI/testing")

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info
        log.debug("Registered OAuth client: %s (%s)", client_info.client_id, client_info.client_name)

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Auto-approve: issue a code and redirect straight back to the client."""
        code = secrets.token_urlsafe(32)
        self._codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or ["mcp"],
            expires_at=time.time() + 600,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
        )
        # iss per RFC 9207 must equal the metadata issuer exactly (including its trailing slash).
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state, iss=str(self.issuer_url))

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        entry = self._codes.get(authorization_code)
        if entry and time.time() > entry.expires_at:
            del self._codes[authorization_code]
            return None
        return entry

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        scopes = authorization_code.scopes
        self._access[access] = AccessToken(
            token=access, client_id=client.client_id, scopes=scopes, expires_at=int(time.time()) + 3600,
        )
        self._refresh[refresh] = RefreshToken(
            token=refresh, client_id=client.client_id, scopes=scopes, expires_at=int(time.time()) + 86400 * 30,
        )
        del self._codes[authorization_code.code]
        return OAuthToken(access_token=access, token_type="bearer", expires_in=3600,
                          refresh_token=refresh, scope=" ".join(scopes))

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        entry = self._refresh.get(refresh_token)
        if entry and entry.expires_at and time.time() > entry.expires_at:
            del self._refresh[refresh_token]
            return None
        return entry

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str],
    ) -> OAuthToken:
        access = secrets.token_urlsafe(32)
        effective = scopes or refresh_token.scopes
        self._access[access] = AccessToken(
            token=access, client_id=client.client_id, scopes=effective, expires_at=int(time.time()) + 3600,
        )
        return OAuthToken(access_token=access, token_type="bearer", expires_in=3600,
                          refresh_token=refresh_token.token, scope=" ".join(effective))

    async def load_access_token(self, token: str) -> AccessToken | None:
        entry = self._access.get(token)
        if entry is None:
            return None
        if entry.expires_at is not None and time.time() > entry.expires_at:
            del self._access[token]
            return None
        return entry

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self._access.pop(token.token, None)
        else:
            self._refresh.pop(token.token, None)


# ---------------------------------------------------------------------------
# Optional strict protocol gate
# ---------------------------------------------------------------------------

class ModernProtocolOnlyMiddleware:
    """With MCP_MODERN_ONLY=true, reject /mcp requests that are not MCP 2026-07-28.

    Handshake-era clients send no MCP-Protocol-Version header on their first
    request, or a version from HANDSHAKE_PROTOCOL_VERSIONS afterwards; both get
    JSON-RPC error -32022 listing the supported version.
    """

    def __init__(self, app, mcp_path: str = _MCP_PATH) -> None:
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == self.mcp_path or path.startswith(self.mcp_path + "/")):
            await self.app(scope, receive, send)
            return
        version = next((v.decode("latin-1") for k, v in scope["headers"] if k.lower() == b"mcp-protocol-version"), None)
        if version is None or version in HANDSHAKE_PROTOCOL_VERSIONS:
            log.warning("Rejected MCP request with protocol version %s (MCP_MODERN_ONLY is set).", version or "(absent)")
            await StarletteJSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": UNSUPPORTED_PROTOCOL_VERSION,
                        "message": (f"This server requires MCP protocol {LATEST_PROTOCOL_VERSION}. "
                                    f"Received: {version or 'no MCP-Protocol-Version header'}."),
                        "data": {"supportedVersions": [LATEST_PROTOCOL_VERSION]},
                    },
                },
                status_code=400,
            )(scope, receive, send)
            return
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# FastAPI app: REST + Swagger UI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NAMLink PBPK mAb Tutorial",
    description=(
        "REST API for the NAMLink a priori PBPK mAb workflow "
        "([namlink-org/PBPK_mAb_NAM_Tutorial](https://github.com/namlink-org/PBPK_mAb_NAM_Tutorial)).\n\n"
        "Run the a priori PBPK pipeline, query fold-error results, look up study-design "
        "performance, and inspect the 8 reference mAb molecules.\n\n"
        "> **Note**: `run-pipeline` executes Docker and runs one command at a time. "
        "All other endpoints read pre-computed CSVs and do not require Docker.\n\n"
        "> **MCP endpoint** for AI clients (configured by `.mcp.json`): `POST /mcp`\n\n"
        "> **Authentication**: MCP clients authenticate with OAuth 2.1 + PKCE. "
        "Every local client is approved automatically."
    ),
    version="1.0.0",
    contact={"name": "NAMLink", "url": "https://namlink.org"},
    license_info={"name": "Code: MIT · Data: CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
    docs_url="/docs",
    redoc_url="/redoc",
)


class FoldErrorsRequest(BaseModel):
    species: Optional[Literal["Monkey", "Human"]] = Field(default=None, description="Filter by species. Omit for both.")
    metric: Optional[Literal["AUC0-tlast", "Cmax", "Clearance"]] = Field(
        default=None, description="Filter by PK endpoint. Omit for all three.")
    molecule: Optional[str] = Field(
        default=None, examples=["Nivolumab"],
        description="Filter by mAb name (e.g. 'Tocilizumab'). Case is ignored. Omit for all 8.")
    evaluation_status: Optional[Literal["Evaluated", "Not evaluable"]] = Field(
        default=None,
        description="'Not evaluable' = clearance rows with >20% AUCinf extrapolation, excluded from counts.")


class StudyDesignRequest(BaseModel):
    molecule: Literal["Golimumab", "Nivolumab"] = Field(
        description="Only Golimumab and Nivolumab have Stages 6-8 results.")
    design: Optional[Literal["2 dose groups", "3 dose groups", "5 dose groups"]] = Field(
        default=None, description="Number of dose groups. Omit for all.")
    n_per_group: Optional[Literal[2, 3, 6]] = Field(default=None, description="Animals per dose group. Omit for all.")
    variability_cv: Optional[Literal[0.3, 0.6]] = Field(
        default=None, description="CV on five shared mechanistic inputs. 0.3 = 30%, 0.6 = 60%.")
    dose_mg_kg: Optional[Literal[0.1, 1.0, 3.0, 10.0, 30.0]] = Field(
        default=None, examples=[10.0], description="Dose in mg/kg. Returns fold_error_detail.")
    endpoint: Optional[Literal["AUC0-28d", "Cmax", "Terminal clearance"]] = Field(
        default=None, description="PK endpoint. Returns fold_error_detail.")


class MoleculeInfoRequest(BaseModel):
    molecule: Optional[str] = Field(
        default=None, examples=["Nivolumab"],
        description="One of Adalimumab, Atezolizumab, Avelumab, Bevacizumab, Golimumab, Nivolumab, "
                    "Pembrolizumab, Tocilizumab. Case is ignored. Omit to return all 8.")


class RunPipelineRequest(BaseModel):
    command: Literal["apriori", "sensitivity", "summary", "compare", "versions", "help"] = Field(
        description=(
            "Pipeline command to run inside Docker.\n"
            "- **apriori**: Stages 1-2-3-5, then compare fold errors. ~6 min.\n"
            "- **sensitivity**: Stage 4 one-way sensitivity analysis. ~15 min.\n"
            "- **summary**: Print within-2-fold counts. Seconds.\n"
            "- **compare**: Compare the fold-error table against the committed one. Seconds.\n"
            "- **versions**: Report software versions inside the Docker image. Seconds.\n"
            "- **help**: List all commands. Seconds."
        ),
    )


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({
        "service": "NAMLink PBPK mAb Tutorial API",
        "docs": f"{_MCP_BASE_URL}/docs",
        "redoc": f"{_MCP_BASE_URL}/redoc",
        "mcp": f"{_MCP_BASE_URL}{_MCP_PATH}",
        "website": "https://namlink.org",
        "repo": "https://github.com/namlink-org/PBPK_mAb_NAM_Tutorial",
    })


@app.post("/api/check-prerequisites", summary="Check prerequisites", tags=["Pipeline"])
def check_prerequisites():
    """Verify the git clone, the checkout version, the required input files, and Docker."""
    return core.check_prerequisites()


@app.post("/api/pipeline-status", summary="Get pipeline status", tags=["Pipeline"])
def get_pipeline_status():
    """Report the workflow state from files on disk. Does not run Docker."""
    return core.get_pipeline_status()


@app.post("/api/fold-errors", summary="Query fold-error table", tags=["Results"])
def get_fold_errors(body: Optional[FoldErrorsRequest] = None):
    """
    Query the a priori fold-error table produced by Stage 3. All filters are optional.
    Fold error = Predicted / Observed; within 2-fold = 0.5 to 2.0.

    **Published result**: 132 rows, 109 evaluated, 96 (88%) within 2-fold.
    """
    b = body or FoldErrorsRequest()
    return _rest(core.get_fold_errors(b.species, b.metric, b.molecule, b.evaluation_status))


@app.post("/api/accuracy-summary", summary="Get accuracy summary", tags=["Results"])
def get_accuracy_summary():
    """Within-2-fold accuracy by species and PK endpoint (mirrors the Docker `summary` command)."""
    return core.get_accuracy_summary()


@app.post("/api/study-design", summary="Query study-design results", tags=["Results"])
def query_study_design(body: StudyDesignRequest):
    """
    Pre-computed monkey PK study-design performance (Stages 6-8) for Golimumab
    (uncalibrated) and Nivolumab (FcRn Kd = 0.39 µmol/L). Read-only: Stages 6-8 are never re-run.
    """
    return _rest(core.query_study_design(body.molecule, body.design, body.n_per_group,
                                         body.variability_cv, body.dose_mg_kg, body.endpoint))


@app.post("/api/molecule-info", summary="Get mAb molecule details", tags=["Reference"])
def get_molecule_info(body: Optional[MoleculeInfoRequest] = None):
    """Target, IgG subclass, species and pipeline notes for the 8 reference mAbs. Omit `molecule` for all 8."""
    return _rest(core.get_molecule_info((body or MoleculeInfoRequest()).molecule))


@app.post("/api/run-pipeline", summary="Run pipeline command", tags=["Pipeline"])
def run_pipeline(body: RunPipelineRequest):
    """
    Run a pipeline command in Docker. **Requires Docker Desktop.** Blocks until the command
    finishes (30-minute ceiling). Only one command runs at a time; a second request gets HTTP 409.
    """
    result = core.run_docker_command(body.command)
    return JSONResponse(result, status_code=409 if result.get("status") == "BUSY" else 200)


def _rest(result: dict) -> Any:
    """Turn the tools' invalid-argument errors into HTTP 422; pass everything else through."""
    if "error" in result and ("allowed_values" in result or "available_molecules" in result):
        return JSONResponse(result, status_code=422)
    return result


# ---------------------------------------------------------------------------
# MCP endpoint: OAuth 2.1, stateless, both protocol generations
# ---------------------------------------------------------------------------

log.info("Initializing NAMLink MCP server (MCP %s, handshake clients %s)...",
         LATEST_PROTOCOL_VERSION, "rejected" if _MODERN_ONLY else "accepted")

oauth_provider = LocalOAuthProvider(base_url=_MCP_BASE_URL)

_mcp = fastmcp.FastMCP(
    name="NAMLink PBPK mAb Tutorial",
    instructions=core.INSTRUCTIONS,
    version="1.0.0",
    auth=oauth_provider,
    cache_ttl=_CACHE_TTL_SECONDS,
    cache_scope=_CACHE_SCOPE,
)


@_mcp.tool(name="check_prerequisites",
           description="Verify prerequisites before running the workflow: git clone, checkout version, input files, Docker.")
async def _t_check_prerequisites() -> dict[str, Any]:
    return await anyio.to_thread.run_sync(core.check_prerequisites)


@_mcp.tool(name="get_pipeline_status",
           description="Report the workflow state from files on disk: fold-error table presence and summary counts.")
def _t_get_pipeline_status() -> dict[str, Any]:
    return core.get_pipeline_status()


@_mcp.tool(name="get_fold_errors",
           description="Query the a priori fold-error table (Predicted/Observed). Optional filters, case ignored: "
                       "species (Monkey|Human), metric (AUC0-tlast|Cmax|Clearance), molecule, "
                       "evaluation_status (Evaluated|Not evaluable).")
def _t_get_fold_errors(species: Optional[str] = None, metric: Optional[str] = None,
                       molecule: Optional[str] = None, evaluation_status: Optional[str] = None) -> dict[str, Any]:
    return core.get_fold_errors(species, metric, molecule, evaluation_status)


@_mcp.tool(name="get_accuracy_summary",
           description="Within-2-fold accuracy by species and PK endpoint. Published: 96/109 (88%) within 2-fold.")
def _t_get_accuracy_summary() -> dict[str, Any]:
    return core.get_accuracy_summary()


@_mcp.tool(name="query_study_design",
           description="Read pre-computed monkey study-design results (Stages 6-8; never re-run them). "
                       "molecule: Golimumab|Nivolumab. Optional: design ('2 dose groups'|'3 dose groups'|'5 dose groups'), "
                       "n_per_group (2|3|6), variability_cv (0.3|0.6), dose_mg_kg (0.1|1|3|10|30), "
                       "endpoint (AUC0-28d|Cmax|Terminal clearance).")
def _t_query_study_design(molecule: str, design: Optional[str] = None, n_per_group: Optional[int] = None,
                          variability_cv: Optional[float] = None, dose_mg_kg: Optional[float] = None,
                          endpoint: Optional[str] = None) -> dict[str, Any]:
    return core.query_study_design(molecule, design, n_per_group, variability_cv, dose_mg_kg, endpoint)


@_mcp.tool(name="get_molecule_info",
           description="Target, IgG subclass, species and pipeline notes for the 8 reference mAbs. Omit molecule for all 8.")
def _t_get_molecule_info(molecule: Optional[str] = None) -> dict[str, Any]:
    return core.get_molecule_info(molecule)


@_mcp.tool(name="run_docker_command",
           description="Run a Docker pipeline command: apriori (~6 min), sensitivity (~15 min), summary, compare, "
                       "versions, help. Only when the user asks to run the workflow; one command at a time.")
async def _t_run_docker_command(command: str) -> dict[str, Any]:
    return await anyio.to_thread.run_sync(core.run_docker_command, command)


# The MCP app owns /mcp and the OAuth routes at the root. FastAPI's own routes are
# matched first, so mounting it at "/" last only catches the remaining paths.
_mcp_asgi = _mcp.http_app(path=_MCP_PATH, stateless_http=True)
app.mount("/", _mcp_asgi)
# Mounted apps get no lifespan events of their own; without this the MCP session
# manager never starts and every /mcp call fails with HTTP 500.
app.router.lifespan_context = _mcp_asgi.lifespan

if _MODERN_ONLY:
    app.add_middleware(ModernProtocolOnlyMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_ALLOWED_HOSTS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def bind_sockets(host: str, port: int) -> list[socket.socket]:
    """Bind the listening sockets. A loopback host binds both 127.0.0.1 and ::1,
    because "localhost" resolves to ::1 first on Windows and an IPv4-only listener
    makes every new connection wait about 2 seconds."""
    if host in ("127.0.0.1", "localhost"):
        targets = [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")]
    else:
        targets = [(socket.AF_INET6 if ":" in host else socket.AF_INET, host)]
    sockets = []
    for i, (family, address) in enumerate(targets):
        try:
            s = socket.socket(family, socket.SOCK_STREAM)
            if family == socket.AF_INET6:
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s.bind((address, port))
        except OSError as exc:
            s.close()
            if i == 0:
                raise SystemExit(f"Cannot listen on {address}:{port} ({exc.strerror}). "
                                 f"Is another server already using port {port}? Set PORT to use another port.")
            continue  # IPv6 loopback unavailable: IPv4 alone still works
        s.set_inheritable(True)
        sockets.append(s)
    return sockets


if __name__ == "__main__":
    print()
    print("  NAMLink PBPK mAb Tutorial -- HTTP API + MCP Server")
    print("  ====================================================")
    print(f"  Repository  : {REPO_ROOT}")
    print(f"  MCP protocol: {LATEST_PROTOCOL_VERSION}"
          f"{' only' if _MODERN_ONLY else ' and handshake versions ' + ', '.join(sorted(HANDSHAKE_PROTOCOL_VERSIONS))}")
    print()
    print(f"  Swagger UI  : {_MCP_BASE_URL}/docs")
    print(f"  MCP endpoint: {_MCP_BASE_URL}{_MCP_PATH}")
    print(f"  OAuth       : {_MCP_BASE_URL}/.well-known/oauth-authorization-server")
    print(f"  Hosts       : {', '.join(_ALLOWED_HOSTS)}")
    if _HOST not in ("127.0.0.1", "localhost", "::1"):
        print(f"  WARNING     : bound to {_HOST}. The REST API (including run-pipeline) has no authentication.")
    print()
    print("  Press Ctrl+C to stop.")
    print()
    uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=bind_sockets(_HOST, _PORT))
