#!/usr/bin/env bash
# NAMLink PBPK mAb Tutorial: HTTP MCP Server launcher (Linux / macOS)
#
# Usage:
#   bash mcp/start_server.sh
#
# The server starts on http://localhost:8000 and the browser opens automatically.
# Press Ctrl+C to stop.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PBPK_REPO_PATH="${REPO_ROOT}"
export PORT="${PORT:-8000}"
export HOST="${HOST:-127.0.0.1}"

echo ""
echo " NAMLink PBPK mAb Tutorial -- HTTP MCP Server"
echo " ============================================="
echo " Repository : ${REPO_ROOT}"
echo ""

# Check Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo " ERROR: Python not found on PATH."
    echo " Install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON=$(command -v python3 2>/dev/null || command -v python)

# Check dependencies
if ! "${PYTHON}" -c "import fastmcp, fastapi, uvicorn, httpx2, mcp_types" &>/dev/null; then
    echo " Installing server dependencies..."
    echo ""
    "${PYTHON}" -m pip install -r "${SCRIPT_DIR}/requirements_http.txt"
fi

echo "  Swagger UI  : http://localhost:${PORT}/docs"
echo "  MCP endpoint: http://localhost:${PORT}/mcp"
echo ""

# Open the browser once the server answers (up to 30 s)
(
    for _ in $(seq 60); do
        if "${PYTHON}" -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:${PORT}/openapi.json', timeout=1)" &>/dev/null; then
            if command -v xdg-open &>/dev/null; then
                xdg-open "http://localhost:${PORT}/docs" &>/dev/null
            elif command -v open &>/dev/null; then
                open "http://localhost:${PORT}/docs"
            fi
            break
        fi
        sleep 0.5
    done
) &

# Start server (blocks until Ctrl+C)
"${PYTHON}" "${SCRIPT_DIR}/server_http.py"
