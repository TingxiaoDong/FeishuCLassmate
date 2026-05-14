# ARC Sidecar

HTTP shim that lets the **feishu-classmate** OpenClaw plugin drive
[AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw) (ARC).

The lab uses ARC to **validate experimental ideas**: the
`research-collaboration-agent` skill turns a discussion into a research plan
(Research Goal / Technical Route / Hypothesis), then hands the topic to ARC,
which runs its 23-stage pipeline — real literature, sandbox experiments,
multi-agent peer review — and returns a conference-ready paper draft as the
validation artifact.

ARC runs are long (minutes → hours), so this sidecar is **async**, mirroring
the `temi-sidecar` pattern.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/` | Health + run counts |
| `POST` | `/runs` | Start a run → returns `run_id` immediately |
| `GET`  | `/runs` | List all runs |
| `GET`  | `/runs/{run_id}` | Poll one run's status |
| `GET`  | `/runs/{run_id}/result` | Status + scanned deliverables (once `completed`) |
| `POST` | `/runs/{run_id}/cancel` | Terminate a running ARC process |

`POST /runs` body: `{ topic, mode?, hypothesis?, plan_doc_url? }`
(`mode`: `auto` → `--auto-approve`, `co-pilot` → `--mode co-pilot`).

## Run

```bash
cd arc-sidecar
uv sync                       # or: pip install -e ".[dev]"

# Mock mode (default) — no ARC needed, fake deliverables, good for plugin dev
python server.py

# Real mode — needs AutoResearchClaw installed
ARC_MOCK=0 \
ARC_COMMAND=researchclaw \
ARC_CONFIG=/path/to/config.yaml \
python server.py
```

## Environment variables

| Var | Default | Meaning |
|---|---|---|
| `ARC_MOCK` | `1` | Non-empty/non-`0` → mock mode (no real ARC invocation) |
| `ARC_COMMAND` | `researchclaw` | ARC CLI executable |
| `ARC_CONFIG` | _(unset)_ | Path to a prepared ARC `config.yaml`, passed as `--config` |
| `ARC_WORKDIR` | `./arc-runs` | Base dir for per-run working directories |
| `SIDECAR_PORT` | `8092` | HTTP listen port |
| `LOG_LEVEL` | `INFO` | Python logging level |

The plugin side configures the URL via `plugins.feishu-classmate.config.arc.sidecarUrl`
(or `ARC_SIDECAR_URL`), and toggles mock with `arc.mockMode` (or `ARC_MOCK`).

## Real-mode setup

ARC is **not** bundled. Install it once, alongside this repo:

```bash
git clone https://github.com/aiming-lab/AutoResearchClaw.git
cd AutoResearchClaw && pip install -e . && researchclaw setup && researchclaw init
cp config.researchclaw.example.yaml config.yaml   # then fill in LLM keys
```

Point `ARC_CONFIG` at that `config.yaml`. To have ARC push progress back into
Feishu, enable `openclaw_bridge` (`use_message` / `use_memory` / `use_cron`) in
that config so ARC reuses feishu-classmate's OpenClaw capabilities.
