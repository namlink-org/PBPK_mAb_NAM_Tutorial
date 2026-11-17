# PBPK mAb NAM Tutorial: MCP Server

This folder contains two complementary ways to interact with the a priori PBPK
workflow programmatically:

| Mode | File | What it gives you |
|---|---|---|
| **HTTP + Swagger UI** | `server_http.py` | Browser interface at `localhost:8000/docs` + REST API + MCP over HTTP |
| **stdio MCP** | `server.py` | Lightweight MCP server launched by the AI client itself |

Both expose the same 7 tools and read the same repository data.

Unlike `skills/pbpk-apriori/SKILL.md`, which provides written instructions the assistant
reads and follows, the MCP server exposes **executable tools**: the assistant calls them
directly and receives structured, typed JSON back.

---

## Quick start: browser interface (recommended for most users)

```bash
pip install -r mcp/requirements_http.txt
python mcp/server_http.py
```

Then open **http://localhost:8000/docs** in your browser.

**Or use the one-click launchers:**

| Platform | Script |
|---|---|
| Windows | Double-click `mcp/start_server.bat` |
| Linux / macOS | `bash mcp/start_server.sh` |

Both launchers install `mcp/requirements_http.txt` if anything is missing, start the
server, and open the Swagger UI once it answers.

### What opens in the browser

- **Swagger UI** at `/docs` - try every tool interactively, fill in parameters, see responses
- **ReDoc** at `/redoc` - clean reference documentation
- **OpenAPI spec** at `/openapi.json`
- **MCP endpoint** at `/mcp` - for AI clients (configured by `.mcp.json`)

---

## Quick start: stdio MCP (for AI assistants only)

```bash
pip install -r mcp/requirements.txt
```

Then configure your AI client (see [Integration](#integration) below).

---

## Prerequisites

- Python 3.10 or later
- Docker Desktop (required only when `run_pipeline` / `run_docker_command` is called;
  all read-only tools work without Docker)
- Repository cloned with `git clone` (not downloaded as a ZIP)

---

## Installation

### HTTP server (browser UI + MCP)
```bash
pip install -r mcp/requirements_http.txt
```

### stdio MCP server (AI clients only)
```bash
pip install -r mcp/requirements.txt
```

---

## Available tools

| Tool | Description |
|---|---|
| `check_prerequisites` | Verify git clone, checkout version (v0.2.1 or later), required files, and Docker status |
| `run_docker_command` | Execute `apriori`, `sensitivity`, `summary`, `compare`, `versions`, or `help` |
| `get_pipeline_status` | Report current workflow state without running Docker |
| `get_fold_errors` | Query the fold-error table with optional filters (species, metric, molecule) |
| `get_accuracy_summary` | Within-2-fold counts by species and endpoint |
| `query_study_design` | Filter pre-computed study-design results by molecule, design, and dose |
| `get_molecule_info` | Pharmacological and repository details for the 8 reference mAbs |

### Tool behaviour

- `run_docker_command` **executes Docker** and takes minutes. Call it only when the
  user explicitly requests a run. Use `get_fold_errors`, `get_accuracy_summary`, and
  `get_pipeline_status` to read already-generated results instantly. Only one command
  runs at a time; a second request returns status `BUSY` (HTTP 409 on the REST API).
- Text arguments ignore case and surrounding spaces (`"nivolumab"` matches
  `Nivolumab`), and `variability_cv` accepts `30` as 30%. An unknown value returns an
  error with `allowed_values` instead of an empty result.
- `query_study_design` reads pre-computed CSVs from Stages 6-8. **Never attempt to
  re-run Stages 6-8** - Stage 7 takes several hours and is not a Docker command.
- All tools return structured JSON with typed numeric fields. None of them produce
  raw CSV text.

---

## Integration

### HTTP mode: `.mcp.json` (recommended)

The repository root contains `.mcp.json`, which points MCP clients at the
running HTTP server:

```json
{
  "mcpServers": {
    "pbpk-namlink": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

1. Start the server: `python mcp/server_http.py`.
2. Open your MCP client from the repository root. Clients that read a
   project-level `.mcp.json` pick it up automatically; for others, copy the
   same `mcpServers` block into that client's MCP configuration.

The server accepts both the stateless MCP protocol `2026-07-28` and the
earlier handshake versions (`2024-11-05` to `2025-11-25`), which most clients
still use. Set `MCP_MODERN_ONLY=true` to accept only `2026-07-28`; other
clients then get JSON-RPC error `-32022`.

**Authentication.** The MCP endpoint uses OAuth 2.1 with PKCE, discovered the
standard way (`/.well-known/oauth-protected-resource/mcp` and
`/.well-known/oauth-authorization-server`). Every local client is approved
automatically: on the first connection your client opens a browser tab that
redirects straight back, with nothing to type. If the client shows the server
as needing authentication, use its "authenticate" action once. Tokens are kept
in memory, so a server restart triggers the same automatic login again.

**Security.** The server listens on the loopback addresses only and rejects
requests whose `Host` header is not `localhost`, `127.0.0.1` or `[::1]`, which
blocks DNS-rebinding attacks from web pages. The REST API has no
authentication; if you set `HOST` to a network address, anyone who can reach
the port can run pipeline commands. Add extra host names with
`MCP_ALLOWED_HOSTS`.

### stdio mode: any MCP client

For clients that launch the server themselves instead of connecting over
HTTP, use the same `mcpServers` block with a command:

```json
{
  "mcpServers": {
    "pbpk-namlink": {
      "command": "python",
      "args": ["/absolute/path/to/PBPK_mAb_NAM_Tutorial/mcp/server.py"],
      "env": {
        "PBPK_REPO_PATH": "/absolute/path/to/PBPK_mAb_NAM_Tutorial"
      }
    }
  }
}
```

Restart the client after editing its configuration.

---

## Configuration

### Repository path

The server resolves the repository root in this order:

1. `PBPK_REPO_PATH` environment variable
2. The directory one level above `server.py` (i.e. `mcp/../` = repo root)

If you run the server from outside the repository, set `PBPK_REPO_PATH`.

### Python environment

Use the same Python that has `mcp` installed. With a virtual environment:

```json
{
  "mcpServers": {
    "pbpk-namlink": {
      "command": "/path/to/venv/bin/python",
      "args": ["mcp/server.py"]
    }
  }
}
```

On Windows with a venv:

```json
{
  "mcpServers": {
    "pbpk-namlink": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["mcp\\server.py"]
    }
  }
}
```

---

## Testing

From the repository root, after installing both requirements files:

```bash
python mcp/test_tools.py        # tool logic against the committed result tables
python mcp/test_stdio_mcp.py    # stdio server over the MCP protocol, including bad inputs
python mcp/test_http_mcp.py     # HTTP server: OAuth login, both protocol generations, REST, concurrency
```

`test_tools.py` also runs the Docker `help` and `versions` commands; set
`PBPK_SKIP_DOCKER=1` to skip them. Pass `--full` to also run `apriori` (~6 min).
CI runs all three on Linux and Windows.

Known limitation: the MCP SDK's token revocation endpoint requires a
`client_secret` field even for public clients, so a revocation request must
send `client_secret=` (empty). Tokens expire after one hour regardless.

---

## Relationship to SKILL.md

Both files cover the same repository. They are designed to be used together or
independently depending on which AI assistant is in use.

| | `skills/pbpk-apriori/SKILL.md` | `mcp/server.py` |
|---|---|---|
| Mechanism | Instruction file read by the assistant | Executable tools called by the assistant |
| Integration | Read by clients that support agent skills | `.mcp.json` (see above) |
| Run workflow | Assistant runs a shell command manually | `run_docker_command("apriori")` |
| Query results | Assistant reads and parses CSV text | `get_fold_errors()` returns typed JSON |
| Study design | Assistant reads raw CSV text | `query_study_design()` with filters |
| Compatibility | See `skills/pbpk-apriori/README.md` | Any MCP-compatible assistant |

---

## Licence

This MCP server is part of the PBPK mAb NAM Tutorial repository and is released
under the MIT licence. See the root `LICENSE` file.
