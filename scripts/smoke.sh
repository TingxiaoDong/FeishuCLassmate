#!/usr/bin/env bash
# feishu-classmate smoke test.
#
# Verifies that the operator's machine has the required toolchain, that
# OpenClaw is installed at a supported version, that optional services
# (MetaClaw, Temi sidecar) are reachable when expected, and that the plugin
# itself is registered and enabled.
#
# Exit code:
#   0 = all REQUIRED checks passed (optional warnings are allowed)
#   1 = at least one REQUIRED check failed
#
# The script is idempotent and safe to re-run. It does not mutate OpenClaw
# state; it only reads.

set -euo pipefail

# ---------------------------------------------------------------------------
# Pretty output. Use tput when available; fall back to raw ANSI otherwise.
# ---------------------------------------------------------------------------

if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  C_RED="$(tput setaf 1)"
  C_GREEN="$(tput setaf 2)"
  C_YELLOW="$(tput setaf 3)"
  C_BOLD="$(tput bold)"
  C_RESET="$(tput sgr0)"
else
  C_RED=""
  C_GREEN=""
  C_YELLOW=""
  C_BOLD=""
  C_RESET=""
fi

MARK_OK="[OK]"
MARK_FAIL="[FAIL]"
MARK_WARN="[WARN]"

REQUIRED_FAILURES=0
WARNINGS=0

pass() {
  printf '%s%s%s %s\n' "${C_GREEN}" "${MARK_OK}" "${C_RESET}" "$1"
}

fail() {
  printf '%s%s%s %s\n' "${C_RED}" "${MARK_FAIL}" "${C_RESET}" "$1"
  REQUIRED_FAILURES=$((REQUIRED_FAILURES + 1))
}

warn() {
  printf '%s%s%s %s\n' "${C_YELLOW}" "${MARK_WARN}" "${C_RESET}" "$1"
  WARNINGS=$((WARNINGS + 1))
}

section() {
  printf '\n%s== %s ==%s\n' "${C_BOLD}" "$1" "${C_RESET}"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Compare two dotted version strings. Returns 0 when $1 >= $2, else 1.
version_ge() {
  # shellcheck disable=SC2046
  [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

# Strip the leading "v" some tools emit.
strip_v() {
  printf '%s' "$1" | sed -e 's/^v//'
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

have_jq=0
if have_cmd jq; then
  have_jq=1
fi

# Safe HTTP HEAD that works on both macOS and Linux curl. Prints the status
# code to stdout; prints nothing on network failure and returns 1.
http_status() {
  local url="$1"
  local timeout="${2:-3}"
  if ! have_cmd curl; then
    return 1
  fi
  # -o /dev/null discards the body, -s silences progress, -w prints status.
  # --max-time caps total request time.
  local code
  code="$(curl -o /dev/null -s -w '%{http_code}' --max-time "${timeout}" "${url}" 2>/dev/null || true)"
  if [ -z "${code}" ] || [ "${code}" = "000" ]; then
    return 1
  fi
  printf '%s' "${code}"
}

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

section "Toolchain"

# --- Node ---
if have_cmd node; then
  node_ver_raw="$(node --version 2>/dev/null || echo 'v0.0.0')"
  node_ver="$(strip_v "${node_ver_raw}")"
  if version_ge "${node_ver}" "22.0.0"; then
    pass "node ${node_ver} (>= 22.0.0)"
  else
    fail "node ${node_ver} is older than required 22.0.0"
  fi
else
  fail "node not found on PATH — install Node.js 22+ (see DEPLOYMENT.md Day 0)"
fi

# --- pnpm (informational; OpenClaw itself does not require pnpm at runtime) ---
if have_cmd pnpm; then
  pnpm_ver="$(pnpm --version 2>/dev/null || echo 'unknown')"
  pass "pnpm ${pnpm_ver}"
else
  warn "pnpm not found — only needed when building from source"
fi

# --- Python (optional; only needed for Temi sidecar) ---
python_bin=""
for candidate in python3 python; do
  if have_cmd "${candidate}"; then
    python_bin="${candidate}"
    break
  fi
done
if [ -n "${python_bin}" ]; then
  py_ver="$("${python_bin}" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || echo '0.0.0')"
  if version_ge "${py_ver}" "3.10.0"; then
    pass "${python_bin} ${py_ver} (>= 3.10.0)"
  else
    warn "${python_bin} ${py_ver} is older than 3.10.0 — Temi sidecar will not run"
  fi
else
  warn "python3 not found — Temi sidecar will not run (fine for Phase 1 only)"
fi

# --- jq (informational; helpers degrade gracefully without it) ---
if [ "${have_jq}" -eq 1 ]; then
  pass "jq available — richer OpenClaw output parsing"
else
  warn "jq not found — OpenClaw output parsing uses grep fallback"
fi

section "OpenClaw"

# --- openclaw binary + version ---
if have_cmd openclaw; then
  oc_ver_raw="$(openclaw --version 2>/dev/null | head -n1 || echo '')"
  # openclaw --version may print either "openclaw 2026.4.10" or "2026.4.10".
  # Pull out the first dotted version-like token.
  oc_ver="$(printf '%s' "${oc_ver_raw}" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || true)"
  if [ -z "${oc_ver}" ]; then
    fail "openclaw installed but --version produced no parseable version: ${oc_ver_raw}"
  elif version_ge "${oc_ver}" "2026.4.10"; then
    pass "openclaw ${oc_ver} (>= 2026.4.10)"
  else
    fail "openclaw ${oc_ver} is older than required 2026.4.10"
  fi
else
  fail "openclaw not found on PATH — run: npm install -g openclaw@latest"
fi

# --- plugin registered and enabled ---
if have_cmd openclaw; then
  plugins_out="$(openclaw plugins list 2>/dev/null || true)"
  if [ -z "${plugins_out}" ]; then
    fail "openclaw plugins list returned no output — is the gateway installed?"
  elif printf '%s' "${plugins_out}" | grep -Fq "feishu-classmate"; then
    # Try to infer enabled/disabled state from the row text.
    plugin_line="$(printf '%s' "${plugins_out}" | grep -F "feishu-classmate" | head -n1)"
    if printf '%s' "${plugin_line}" | grep -qiE 'enabled|active'; then
      pass "plugin feishu-classmate is enabled"
    elif printf '%s' "${plugin_line}" | grep -qiE 'disabled|inactive'; then
      fail "plugin feishu-classmate is registered but DISABLED — run: openclaw plugins enable feishu-classmate"
    else
      # Row found but no state keyword — treat as pass since `plugins list`
      # formats vary across OpenClaw releases.
      pass "plugin feishu-classmate is registered"
    fi
  else
    fail "plugin feishu-classmate not found in 'openclaw plugins list' — run: openclaw plugins add-local ./ && openclaw plugins enable feishu-classmate"
  fi
fi

section "Optional services"

# --- MetaClaw proxy ---
METACLAW_URL="${METACLAW_URL:-http://127.0.0.1:30000/v1/models}"
mc_status="$(http_status "${METACLAW_URL}" 3 || true)"
if [ -n "${mc_status}" ] && [ "${mc_status}" = "200" ]; then
  pass "MetaClaw proxy reachable at ${METACLAW_URL} (HTTP ${mc_status})"
elif [ -n "${mc_status}" ]; then
  warn "MetaClaw proxy returned HTTP ${mc_status} at ${METACLAW_URL} — plugin will fall back to direct LLM"
else
  warn "MetaClaw proxy not reachable at ${METACLAW_URL} — plugin will fall back to direct LLM (fine for Phase 1)"
fi

# --- Temi sidecar ---
TEMI_SIDECAR_URL="${TEMI_SIDECAR_URL:-http://127.0.0.1:8091}"
# Ensure no trailing slash duplication when composing the health URL.
temi_root="${TEMI_SIDECAR_URL%/}/"
temi_status="$(http_status "${temi_root}" 3 || true)"
if [ -n "${temi_status}" ] && [ "${temi_status}" = "200" ]; then
  pass "Temi sidecar reachable at ${temi_root} (HTTP ${temi_status})"
elif [ -n "${temi_status}" ]; then
  warn "Temi sidecar returned HTTP ${temi_status} at ${temi_root} — expected 200"
else
  warn "Temi sidecar not reachable at ${temi_root} — expected in Phase 1 with mockMode=true"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

section "Summary"

if [ "${REQUIRED_FAILURES}" -eq 0 ]; then
  printf '%s%s All required checks passed%s' "${C_GREEN}" "${MARK_OK}" "${C_RESET}"
  if [ "${WARNINGS}" -gt 0 ]; then
    printf ' (with %d warning%s)\n' "${WARNINGS}" "$( [ "${WARNINGS}" -eq 1 ] || printf 's' )"
  else
    printf '\n'
  fi
  exit 0
else
  printf '%s%s %d required check%s failed%s\n' \
    "${C_RED}" "${MARK_FAIL}" \
    "${REQUIRED_FAILURES}" \
    "$( [ "${REQUIRED_FAILURES}" -eq 1 ] || printf 's' )" \
    "${C_RESET}"
  exit 1
fi
