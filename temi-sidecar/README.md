# Temi Sidecar

HTTP bridge between the **feishu-classmate** OpenClaw plugin (TypeScript) and
the **Temi robot** WebSocket protocol.

The plugin calls this sidecar over HTTP; the sidecar translates the calls into
`ws://TEMI_IP:8175` JSON messages.  When `TEMI_MOCK=1` the sidecar runs
entirely without a real robot and returns plausible canned data.

---

## Prerequisites

- Python 3.10 or later
- [`uv`](https://docs.astral.sh/uv/) (recommended) **or** plain `pip`

---

## Install

### With uv (recommended)

```bash
cd temi-sidecar
uv sync
```

### With pip

```bash
cd temi-sidecar
pip install -e .
```

To install dev/test dependencies as well:

```bash
uv sync --extra dev
# or
pip install -e ".[dev]"
```

---

## Environment Variables

| Variable      | Default  | Description                                                       |
|---------------|----------|-------------------------------------------------------------------|
| `TEMI_IP`     | _(none)_ | IP address of the Temi robot, e.g. `192.168.1.100`               |
| `TEMI_PORT`   | `8175`   | Temi WebSocket port                                               |
| `SIDECAR_PORT`| `8091`   | Port this HTTP server binds to                                    |
| `TEMI_MOCK`   | _(none)_ | Set to any non-empty, non-`0` value to force mock mode            |
| `TEMI_WOZ_PRELAUNCH` | `1` | Prelaunch WOZ app via adb before each WS connect (`0` to disable) |
| `TEMI_ADB_COMMAND` | `adb` | adb executable path/name                                           |
| `TEMI_ADB_PORT` | `5555` | adb TCP port on Temi                                               |
| `TEMI_WOZ_PACKAGE` | `com.cdi.temiwoz.debug` | WOZ app package name                              |
| `TEMI_WOZ_ACTIVITY` | `com.cdi.temiwoz.MainActivity` | WOZ launcher activity                |
| `TEMI_WOZ_PRELAUNCH_WAIT_S` | `2.0` | Wait time (seconds) after `am start` before WS connect |
| `LOG_LEVEL`   | `INFO`   | Python logging level (`DEBUG` / `INFO` / `WARNING` / `ERROR`)    |

---

## Run

### Normal mode (real robot)

```bash
TEMI_IP=192.168.1.100 uvicorn server:app --host 0.0.0.0 --port 8091
```

If the robot is unreachable at startup, the sidecar logs a warning and
**automatically falls back to mock mode** so the plugin remains functional
during development.

In real mode startup, the sidecar now runs this prelaunch flow before opening
`ws://TEMI_IP:8175`:

1. `adb connect TEMI_IP:TEMI_ADB_PORT`
2. `adb shell am start -n TEMI_WOZ_PACKAGE/TEMI_WOZ_ACTIVITY`
3. sleep `TEMI_WOZ_PRELAUNCH_WAIT_S`
4. open WebSocket

### Mock mode (no robot needed)

```bash
TEMI_MOCK=1 uvicorn server:app --host 0.0.0.0 --port 8091
```

### Direct execution

```bash
TEMI_IP=192.168.1.100 python server.py
```

---

## API Reference & curl Examples

### `GET /` — health check

```bash
curl http://localhost:8091/
# {"status":"ok","mock":true,"connected":false}
```

### `GET /status`

```bash
curl http://localhost:8091/status
# {"connected":false,"battery":87,"position":{"x":1.2,"y":0.5},"is_moving":false,"mock":true}
```

### `POST /goto`

```bash
curl -X POST http://localhost:8091/goto \
  -H "Content-Type: application/json" \
  -d '{"location":"入口"}'
# {"ok":true,"message":"(mock) Temi 已导航到 入口","mock":true}
```

English location names are mapped to Chinese automatically (e.g. `entrance` → `入口`,
`kitchen` → `厨房`, `charging station` → `充电桩`).

### `POST /speak`

```bash
curl -X POST http://localhost:8091/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"你好同学！","voice":"friendly"}'
# {"ok":true,"mock":true}
```

`voice` is `"friendly"` (default) or `"professional"`.

### `POST /stop`

```bash
curl -X POST http://localhost:8091/stop \
  -H "Content-Type: application/json" \
  -d '{"immediate":true}'
# {"ok":true,"mock":true}
```

### `POST /detect-person`

```bash
curl -X POST http://localhost:8091/detect-person \
  -H "Content-Type: application/json" \
  -d '{"timeout_ms":5000}'
# {"open_id":null,"confidence":0.0,"mock":true}
```

`timeout_ms` must be between 500 and 15 000.  In mock mode (and Phase 1 real
mode) `open_id` is always `null`.

### `POST /rfid-scan`

```bash
curl -X POST http://localhost:8091/rfid-scan \
  -H "Content-Type: application/json" \
  -d '{"route":["工位区-A3"]}'
# {"tags":[{"tag_id":"TAG-001A","location_estimate":"工位区-A3","rssi":-62}],"mock":true}
```

`route` is optional; omit it to scan all reachable tags.

### `POST /monitor-focus`

```bash
curl -X POST http://localhost:8091/monitor-focus \
  -H "Content-Type: application/json" \
  -d '{"student_open_id":"ou_abc123","duration_s":30}'
# {"samples":[{"ts":1713340800.0,"focused":true,"score":0.95},...],"mock":true}
```

One sample is produced roughly every 5 seconds.  In mock mode the trace
follows a cosine pattern: high focus at the start and end, with a dip in the
middle (realistic study-session shape).

### `POST /gesture`

```bash
curl -X POST http://localhost:8091/gesture \
  -H "Content-Type: application/json" \
  -d '{"type":"encourage"}'
# {"ok":true,"mock":true}
```

Valid gesture types: `encourage`, `poke`, `applause`, `nod`.

---

## Running Tests

```bash
cd temi-sidecar
TEMI_MOCK=1 pytest -v
```

All tests use FastAPI's `TestClient` (no real network required).

---

## Mock Mode vs Real Mode

| Aspect | Mock mode | Real mode |
|---|---|---|
| Robot required | No | Yes (`TEMI_IP` must be set and reachable) |
| `/goto`, `/speak`, `/stop` | Returns `ok:true` instantly | Sends WS command; waits for response or timeout |
| `/detect-person` | Returns `open_id:null` | Returns `open_id:null` (Phase 1 stub) |
| `/rfid-scan` | Returns 3 sample tags | Returns error (Phase 2) |
| `/monitor-focus` | Returns cosine focus trace | Returns error (Phase 2) |
| `/gesture` | Returns `ok:true` | Returns error (Phase 2) |
| Response `mock` field | `true` | `false` |
| Auto-fallback | — | Falls back to mock if robot unreachable at startup |

In real mode, **all robot errors are returned as HTTP 200 with `ok:false`** in
the response body — the sidecar never propagates a 500 for application-level
robot failures.

---

## Roadmap

### Phase 1 (current)

- Navigation (`/goto`), speech (`/speak`), emergency stop (`/stop`)
- Status polling (`/status`)
- Person detection stub (`/detect-person` — always returns `null`)
- Full mock mode for plugin development without a robot

### Phase 2 (deferred)

- **Real person detection** via Temi's camera SDK + face/badge recognition
- **RFID scanning** (`/rfid-scan`) — hardware integration pending
- **Focus monitoring** (`/monitor-focus`) — vision pipeline integration pending
- **Physical gestures** (`/gesture`) — motion primitive library pending

---

## Project Structure

```
temi-sidecar/
├── pyproject.toml          # package metadata & dependencies
├── server.py               # FastAPI app — all 8 endpoints
├── adapters/
│   ├── __init__.py
│   └── temi.py             # async WebSocket client (ported from TemiWebSocketClient)
├── tests/
│   ├── __init__.py
│   └── test_mock_mode.py   # pytest tests (mock mode, no robot needed)
└── README.md
```
