#!/usr/bin/env bash
# pbpk.sh - one-word launcher for the Docker workflow (macOS and Linux).
#
# From the repository root:
#   bash docker/pbpk.sh apriori
# Commands: build, apriori, sensitivity, compare, summary, versions, help
#
# 'build' (or the first run) creates the image 'pbpk-mab-nam' from docker/Dockerfile.
# The image is always built for linux/amd64, which works on Intel, AMD,
# and Apple Silicon Macs (via Rosetta 2 / QEMU emulation).

set -uo pipefail

image="pbpk-mab-nam"
repo="$(cd "$(dirname "$0")/.." && pwd)"
cmd="${1:-help}"

fail() { printf '\nSTOPPED: %s\n' "$*" >&2; exit 1; }

if ! command -v docker &>/dev/null; then
    fail "Docker is not installed. Install Docker Desktop and try again."
fi
if ! docker info &>/dev/null 2>&1; then
    fail "Docker is not running. Start Docker Desktop, wait for 'Engine running', and try again."
fi

have_image() { docker image inspect "$image" &>/dev/null; }

if ! have_image || [ "$cmd" = "build" ]; then
    echo ""
    echo "==> Building the '$image' image (first time: 15 to 30 minutes, about 1 GB download)"
    docker build --platform linux/amd64 -t "$image" "$repo/docker"
    [ $? -ne 0 ] && fail "Image build failed. Check the output above."
    [ "$cmd" = "build" ] && exit 0
fi

docker run --rm --platform linux/amd64 -v "$repo:/work" "$image" "$cmd"
exit $?
