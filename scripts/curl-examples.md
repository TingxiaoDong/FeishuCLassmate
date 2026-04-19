# Temi Sidecar — curl examples

This document is a debugging companion: curl one-liners for every endpoint
exposed by `temi-sidecar/server.py`. Use these when you want to poke the
sidecar directly without going through OpenClaw, the plugin, or the LLM.

All examples assume the sidecar is reachable at `http://127.0.0.1:8091`.
Override with an environment variable if yours runs elsewhere:

```bash
export SIDECAR=http://127.0.0.1:8091
```

Then substitute `${SIDECAR}` in the commands below.

Every response contains a `"mock"` boolean indicating whether the answer
was synthesized (no robot talking) or came from the real Temi. In mock
mode all writes are silently dropped and reads return plausible canned
data; in real mode the sidecar relays JSON messages over
`ws://TEMI_IP:8175`.

If the `jq` binary is available, pipe responses through `| jq` for
pretty-printing. The examples below omit the pipe so they work on hosts
that do not have jq installed — `jq` is **not** required to hit the
sidecar, only to format its output.

---

## 1. `GET /` — liveness probe

The cheapest "is the process up?" check. Returns `status: "ok"` whether
or not the robot is actually connected.

```bash
curl -sS "${SIDECAR}/"
```

Expected response (mock mode, no robot):

```json
{"status":"ok","mock":true,"connected":false}
```

Expected response (real mode with a reachable robot):

```json
{"status":"ok","mock":false,"connected":true}
```

Use cases:

- Kubernetes / systemd liveness probe.
- The required-only leg of `scripts/smoke.sh`.
- Determining from CI whether the sidecar came up at all before running
  integration tests.

---

## 2. `GET /status` — battery, pose, motion

Reads the robot's live state: battery percentage, current pose in the
local map frame, and whether the base is currently moving. In mock mode
returns a fixed snapshot so that higher-level tools have something
structurally valid to parse.

```bash
curl -sS "${SIDECAR}/status"
```

Expected response (mock):

```json
{"connected":false,"battery":87,"position":{"x":1.2,"y":0.5},"is_moving":false,"mock":true}
```

Expected response (real):

```json
{"connected":true,"battery":64,"position":{"x":3.14,"y":-0.82},"is_moving":true,"mock":false}
```

Troubleshooting:

- `connected: false` with `mock: false` means the sidecar started but
  has not (yet) established a WebSocket handshake with the robot. Check
  `TEMI_IP` env var and LAN reachability.
- `battery` below 15 is a hard constraint for several skills; the
  plugin refuses to dispatch long patrol routes in that range.

---

## 3. `POST /goto` — navigate to a named location

The robot moves to a saved location by its Chinese name. The sidecar
also accepts a handful of English aliases (e.g. `entrance` is mapped to
`入口`, `kitchen` to `厨房`, `charging station` to `充电桩`).

```bash
curl -sS -X POST "${SIDECAR}/goto" \
  -H "Content-Type: application/json" \
  -d '{"location":"入口"}'
```

Expected response (mock):

```json
{"ok":true,"message":"(mock) Temi 已导航到 入口","mock":true}
```

English-alias example:

```bash
curl -sS -X POST "${SIDECAR}/goto" \
  -H "Content-Type: application/json" \
  -d '{"location":"charging station"}'
```

Unknown location example — the sidecar returns a structured error, not
an HTTP 500:

```bash
curl -sS -X POST "${SIDECAR}/goto" \
  -H "Content-Type: application/json" \
  -d '{"location":"magic room"}'
```

Response:

```json
{"ok":false,"error":"unknown_location","known":["入口","厨房","充电桩","..."],"mock":false}
```

Notes:

- The call returns as soon as the robot *accepts* the goal, not when it
  arrives. For arrival confirmation, poll `/status` until
  `is_moving: false`.
- In real mode, a navigation timeout (default 120 s) returns
  `ok: false, error: "timeout"`.

---

## 4. `POST /speak` — text-to-speech

The robot speaks a UTF-8 string in one of two voices. Keep strings
under 200 characters for natural cadence; the plugin chunks longer
narration into multiple calls.

```bash
curl -sS -X POST "${SIDECAR}/speak" \
  -H "Content-Type: application/json" \
  -d '{"text":"你好同学！欢迎来到我们的实验室。","voice":"friendly"}'
```

Expected response:

```json
{"ok":true,"mock":true}
```

Professional-voice example (used by the lab-tour skill for the
supervisor-greeting stage):

```bash
curl -sS -X POST "${SIDECAR}/speak" \
  -H "Content-Type: application/json" \
  -d '{"text":"各位访客,接下来由我为大家介绍实验室。","voice":"professional"}'
```

Validation rules enforced by the sidecar:

- `text` required, 1 to 500 characters.
- `voice` optional, one of `"friendly"` (default) or `"professional"`.

---

## 5. `POST /stop` — emergency stop

Cancels the current navigation goal and any in-flight speech. Safe to
call even if the robot is idle.

```bash
curl -sS -X POST "${SIDECAR}/stop" \
  -H "Content-Type: application/json" \
  -d '{"immediate":true}'
```

Expected response:

```json
{"ok":true,"mock":true}
```

`immediate: false` performs a decelerating stop (smoother, safer near
people); `immediate: true` applies the emergency brake. The Feishu
`supervise-student` skill uses `true` when a student texts
`飞书同学停`.

---

## 6. `POST /detect-person` — identify person in front of the robot

Phase 2 endpoint. In Phase 1 (and in mock mode) it always returns
`open_id: null` because the face/badge recognition pipeline is not yet
wired up.

```bash
curl -sS -X POST "${SIDECAR}/detect-person" \
  -H "Content-Type: application/json" \
  -d '{"timeout_ms":3000}'
```

Expected Phase 1 response (mock or real):

```json
{"open_id":null,"confidence":0.0,"mock":true}
```

Future Phase 2 response shape:

```json
{"open_id":"ou_abc123","confidence":0.92,"mock":false}
```

Validation:

- `timeout_ms` required, integer in `[500, 15000]`.
- Outside that range the sidecar returns HTTP 422 with a Pydantic
  validation error body.

---

## 7. `POST /rfid-scan` — RFID sweep of equipment tags

Phase 2 endpoint. Mock mode returns three plausible tags so the
`equipment_patrol` scene can be developed end-to-end without hardware.
Real mode currently returns `ok: false, error: "not_implemented"`
because the RFID reader SDK integration is pending.

Scan the default full route:

```bash
curl -sS -X POST "${SIDECAR}/rfid-scan" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected response (mock):

```json
{"tags":[{"tag_id":"TAG-001A","location_estimate":"工位区-A3","rssi":-62},{"tag_id":"TAG-002B","location_estimate":"硬件台","rssi":-58},{"tag_id":"TAG-009Z","location_estimate":"器材柜","rssi":-71}],"mock":true}
```

Scan a specific subset of waypoints:

```bash
curl -sS -X POST "${SIDECAR}/rfid-scan" \
  -H "Content-Type: application/json" \
  -d '{"route":["工位区-A3","硬件台"]}'
```

Notes:

- `route` is optional. Omit it to scan every saved waypoint.
- RSSI is in dBm; values closer to zero indicate stronger signal.
- In real mode, the response is:

  ```json
  {"ok":false,"error":"not_implemented","phase":2,"mock":false}
  ```

---

## 8. `POST /monitor-focus` — sample student focus over N seconds

Phase 2 endpoint. Intended to support the `supervise-student` skill's
offline mode, where Temi observes a student at their workstation and
samples a focus score roughly every 5 seconds. Mock mode returns a
cosine-shaped trace: high focus at the start and end of the window,
with a realistic dip in the middle.

```bash
curl -sS -X POST "${SIDECAR}/monitor-focus" \
  -H "Content-Type: application/json" \
  -d '{"student_open_id":"ou_abc123","duration_s":30}'
```

Expected response (mock, 30 s window → 6 samples):

```json
{"samples":[{"ts":1713340800.0,"focused":true,"score":0.95},{"ts":1713340805.0,"focused":true,"score":0.82},{"ts":1713340810.0,"focused":false,"score":0.48},{"ts":1713340815.0,"focused":false,"score":0.39},{"ts":1713340820.0,"focused":true,"score":0.71},{"ts":1713340825.0,"focused":true,"score":0.93}],"mock":true}
```

Validation:

- `student_open_id` required, Feishu open_id format (`ou_...`).
- `duration_s` required, integer in `[5, 600]`.
- Real mode returns `ok: false, error: "not_implemented"` pending the
  vision pipeline.

---

## 9. `POST /gesture` — physical gesture (encourage / poke / applause / nod)

Phase 2 endpoint. In mock mode the response is immediate; in real mode
it blocks until the gesture animation completes (typically 2 to 4 s).

```bash
curl -sS -X POST "${SIDECAR}/gesture" \
  -H "Content-Type: application/json" \
  -d '{"type":"encourage"}'
```

Expected response:

```json
{"ok":true,"mock":true}
```

Valid gesture types:

| `type` | Used by | Meaning |
|--------|---------|---------|
| `encourage` | `supervise-student` | Thumbs-up-style affirmation at milestone completion |
| `poke` | `supervise-student` | Light attention-getter when student is idle beyond threshold |
| `applause` | `conduct-lab-tour` | Session-wrap celebration when a visitor asks a final question |
| `nod` | `initiate-conversation` | Acknowledgement during ambient small-talk exchanges |

Any other string returns HTTP 422 with a validation error enumerating
the accepted values.

---

## Debugging tips

- Prefix any curl invocation with `-v` to see the request line and
  response headers; extremely useful when diagnosing HTTP 422 (missing
  or malformed JSON body) vs HTTP 500 (sidecar crashed).

  ```bash
  curl -v -X POST "${SIDECAR}/speak" \
    -H "Content-Type: application/json" \
    -d '{"text":"test"}'
  ```

- If a request hangs, the sidecar has either lost its WebSocket link
  to the robot or is waiting on an absent upstream. Tail the sidecar
  log:

  ```bash
  tail -f logs/temi-sidecar.log
  ```

- The sidecar accepts `application/json` only. A missing
  `Content-Type` header will surface as `{"detail":"..."}` with HTTP
  422, not 400. Always set the header explicitly.

- All POST bodies are validated by Pydantic. When in doubt about the
  expected shape, open the browser at `http://127.0.0.1:8091/docs` —
  FastAPI serves an interactive OpenAPI UI with every field, type,
  and constraint inlined.
