#!/usr/bin/env bash
# 在本机（与 Temi 同一局域网）启动 temi-sidecar。
# 必须通过 adb 预启动 WOZ 后再连 WebSocket；本脚本固定开启预启动，不设关闭项。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/temi-sidecar"
export TEMI_IP="${TEMI_IP:-192.168.31.121}"
export TEMI_MOCK="${TEMI_MOCK:-0}"
export TEMI_IDLE_TIMEOUT_S="${TEMI_IDLE_TIMEOUT_S:-0}"
export TEMI_WOZ_PRELAUNCH=1
exec uv run uvicorn server:app --host 127.0.0.1 --port "${SIDECAR_PORT:-8091}"
