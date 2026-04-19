#!/usr/bin/env bash
# feishu-classmate developer quick-start.
#
# Brings the full local stack up:
#   1. MetaClaw proxy (optional; skipped if the 'metaclaw' binary is absent)
#   2. Temi sidecar (FastAPI, mock mode by default)
#   3. OpenClaw gateway (restart to pick up any config changes)
#
# Logs are written to ./logs/ with one file per component. A trap installs
# a clean-shutdown handler so Ctrl+C tears everything down.
#
# The script is intentionally conservative: it does not rebuild the plugin,
# it does not install dependencies, and it does not touch config. Run
# `pnpm install && pnpm build` separately before invoking this.

set -euo pipefail

# Resolve the repo root from the script's own location so the script works
# regardless of the caller's cwd.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

LOG_DIR="./logs"
mkdir -p "${LOG_DIR}"

METACLAW_LOG="${LOG_DIR}/metaclaw.log"
SIDECAR_LOG="${LOG_DIR}/temi-sidecar.log"
GATEWAY_LOG="${LOG_DIR}/gateway-restart.log"

METACLAW_PID=""
SIDECAR_PID=""

# ---------------------------------------------------------------------------
# Clean shutdown
# ---------------------------------------------------------------------------

cleanup() {
  local exit_code=$?
  printf '\n[dev.sh] shutting down background services...\n' >&2

  if [ -n "${SIDECAR_PID}" ] && kill -0 "${SIDECAR_PID}" 2>/dev/null; then
    kill "${SIDECAR_PID}" 2>/dev/null || true
    # Give it a moment, then force if still alive.
    sleep 1
    if kill -0 "${SIDECAR_PID}" 2>/dev/null; then
      kill -9 "${SIDECAR_PID}" 2>/dev/null || true
    fi
    printf '[dev.sh] stopped temi-sidecar (pid %s)\n' "${SIDECAR_PID}" >&2
  fi

  if [ -n "${METACLAW_PID}" ] && kill -0 "${METACLAW_PID}" 2>/dev/null; then
    kill "${METACLAW_PID}" 2>/dev/null || true
    sleep 1
    if kill -0 "${METACLAW_PID}" 2>/dev/null; then
      kill -9 "${METACLAW_PID}" 2>/dev/null || true
    fi
    printf '[dev.sh] stopped metaclaw (pid %s)\n' "${METACLAW_PID}" >&2
  fi

  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# 1. MetaClaw (optional)
# ---------------------------------------------------------------------------

if command -v metaclaw >/dev/null 2>&1; then
  printf '[dev.sh] starting metaclaw -> %s\n' "${METACLAW_LOG}"
  # `metaclaw start` is the supported entry point; it binds :30000.
  metaclaw start >"${METACLAW_LOG}" 2>&1 &
  METACLAW_PID=$!
  printf '[dev.sh] metaclaw pid=%s\n' "${METACLAW_PID}"
else
  printf '[dev.sh] metaclaw not installed, skipping (plugin will fall back to direct LLM)\n'
fi

# ---------------------------------------------------------------------------
# 2. Temi sidecar
# ---------------------------------------------------------------------------

SIDECAR_DIR="./temi-sidecar"
if [ ! -d "${SIDECAR_DIR}" ]; then
  printf '[dev.sh] %s not found, skipping sidecar\n' "${SIDECAR_DIR}" >&2
else
  # Pick the runner: prefer uv (fast, reproducible), fall back to python -m.
  sidecar_cmd=""
  if command -v uv >/dev/null 2>&1; then
    sidecar_cmd="uv run uvicorn server:app --host 127.0.0.1 --port 8091 --reload"
  elif command -v uvicorn >/dev/null 2>&1; then
    sidecar_cmd="uvicorn server:app --host 127.0.0.1 --port 8091 --reload"
  else
    # Last resort: invoke uvicorn through python -m. Assumes it is installed
    # in the default python environment.
    python_bin="python3"
    command -v "${python_bin}" >/dev/null 2>&1 || python_bin="python"
    sidecar_cmd="${python_bin} -m uvicorn server:app --host 127.0.0.1 --port 8091 --reload"
  fi

  printf '[dev.sh] starting temi-sidecar in mock mode -> %s\n' "${SIDECAR_LOG}"
  (
    cd "${SIDECAR_DIR}"
    # Force mock mode for the dev stack — the robot is not expected to be on
    # the dev LAN. Override by exporting TEMI_MOCK=0 before invoking dev.sh.
    TEMI_MOCK="${TEMI_MOCK:-1}" exec ${sidecar_cmd}
  ) >"${SIDECAR_LOG}" 2>&1 &
  SIDECAR_PID=$!
  printf '[dev.sh] temi-sidecar pid=%s\n' "${SIDECAR_PID}"
fi

# ---------------------------------------------------------------------------
# 3. OpenClaw gateway restart
# ---------------------------------------------------------------------------

if command -v openclaw >/dev/null 2>&1; then
  printf '[dev.sh] restarting openclaw gateway (log: %s)\n' "${GATEWAY_LOG}"
  # The gateway already runs as its own daemon; `restart` is a short,
  # synchronous command so there is no PID to track here.
  if ! openclaw gateway restart >"${GATEWAY_LOG}" 2>&1; then
    printf '[dev.sh] WARNING: openclaw gateway restart failed — see %s\n' "${GATEWAY_LOG}" >&2
  fi
else
  printf '[dev.sh] openclaw not installed, skipping gateway restart\n' >&2
fi

# ---------------------------------------------------------------------------
# Wait
# ---------------------------------------------------------------------------

printf '\n[dev.sh] stack is up.\n'
printf '    metaclaw log     : %s\n' "${METACLAW_LOG}"
printf '    temi-sidecar log : %s\n' "${SIDECAR_LOG}"
printf '    gateway log      : %s\n' "${GATEWAY_LOG}"
printf '\n[dev.sh] Press Ctrl+C to stop.\n\n'

# If we started nothing, exit immediately.
if [ -z "${METACLAW_PID}" ] && [ -z "${SIDECAR_PID}" ]; then
  printf '[dev.sh] nothing to wait on, exiting.\n'
  exit 0
fi

# Block until any tracked child exits (or Ctrl+C triggers the trap).
# `wait -n` is bash 4.3+. macOS /bin/bash is 3.2, but /usr/bin/env bash
# plus modern Homebrew bash covers most dev machines; fall back to a
# polling wait otherwise.
if wait -n 2>/dev/null; then
  :
else
  while true; do
    if [ -n "${SIDECAR_PID}" ] && ! kill -0 "${SIDECAR_PID}" 2>/dev/null; then
      break
    fi
    if [ -n "${METACLAW_PID}" ] && ! kill -0 "${METACLAW_PID}" 2>/dev/null; then
      break
    fi
    sleep 2
  done
fi
