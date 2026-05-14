"""
ARC Sidecar — FastAPI HTTP server bridging the feishu-classmate TypeScript
plugin to AutoResearchClaw (ARC, https://github.com/aiming-lab/AutoResearchClaw).

The feishu-classmate `research-collaboration-agent` skill produces a research
plan (Research Goal / Technical Route / Hypothesis); this sidecar takes that
as a *topic* and runs ARC's 23-stage pipeline asynchronously to **validate the
idea** — real literature, sandbox experiments, multi-agent peer review — then
exposes run status + deliverables over HTTP.

ARC runs are long (minutes to hours), so every run is async:
  POST /runs          → returns a run_id immediately, ARC runs in the background
  GET  /runs/{id}     → poll status
  GET  /runs/{id}/result → fetch deliverables once status == "completed"

This mirrors the `temi-sidecar` pattern: a thin FastAPI shim the TS plugin
talks to over HTTP, with a mock mode so the plugin + tools can be developed
without ARC installed.

Environment variables
---------------------
ARC_MOCK       If set to any non-empty, non-"0" value (default: "1"), run in
               mock mode — no real ARC invocation, fast fake deliverables.
ARC_COMMAND    ARC CLI executable (default: "researchclaw").
ARC_CONFIG     Path to a prepared ARC config.yaml, passed as `--config`.
               Optional; if unset ARC uses its own default discovery.
ARC_WORKDIR    Base directory for per-run working dirs (default: "./arc-runs").
SIDECAR_PORT   Port this HTTP server listens on (default: 8092).
LOG_LEVEL      Python logging level, e.g. DEBUG / INFO (default: INFO).
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("arc-sidecar")

# --------------------------------------------------------------------------- #
# Config                                                                      #
# --------------------------------------------------------------------------- #


def _is_mock() -> bool:
    v = os.environ.get("ARC_MOCK", "1")
    return v not in ("", "0", "false", "no", "off")


ARC_COMMAND = os.environ.get("ARC_COMMAND", "researchclaw")
ARC_CONFIG = os.environ.get("ARC_CONFIG", "").strip()
ARC_WORKDIR = Path(os.environ.get("ARC_WORKDIR", "./arc-runs")).resolve()

RunStatus = Literal["queued", "running", "completed", "failed"]

# Deliverable filenames ARC writes (see AutoResearchClaw README "One Command. One Paper.").
_DELIVERABLE_FILES = {
    "paper_draft": "paper_draft.md",
    "paper_tex": "paper.tex",
    "references_bib": "references.bib",
    "verification_report": "verification_report.json",
    "reviews": "reviews.md",
}
_DELIVERABLE_DIRS = {
    "charts": "charts",
    "experiments": "experiment runs",
    "evolution": "evolution",
    "deliverables": "deliverables",
}


# --------------------------------------------------------------------------- #
# Run state                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class RunState:
    run_id: str
    topic: str
    mode: str
    hypothesis: str = ""
    plan_doc_url: str = ""
    status: RunStatus = "queued"
    started_at: str = ""
    finished_at: str = ""
    return_code: Optional[int] = None
    workdir: str = ""
    error: str = ""
    log_tail: list[str] = field(default_factory=list)
    _proc: Optional[subprocess.Popen] = None

    def public(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "topic": self.topic,
            "mode": self.mode,
            "hypothesis": self.hypothesis,
            "plan_doc_url": self.plan_doc_url,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "return_code": self.return_code,
            "workdir": self.workdir,
            "error": self.error,
            "log_tail": self.log_tail[-20:],
        }


# run_id -> RunState. Guarded by _RUNS_LOCK.
_RUNS: dict[str, RunState] = {}
_RUNS_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Run execution                                                               #
# --------------------------------------------------------------------------- #


def _scan_deliverables(workdir: Path) -> dict[str, Any]:
    """Best-effort scan of an ARC run workdir for known deliverables."""
    out: dict[str, Any] = {"workdir": str(workdir), "files": {}, "dirs": {}}
    if not workdir.exists():
        return out
    # Files: record path + a short preview for text artifacts.
    for key, name in _DELIVERABLE_FILES.items():
        for candidate in (workdir / name, workdir / "deliverables" / name):
            if candidate.is_file():
                entry: dict[str, Any] = {"path": str(candidate), "bytes": candidate.stat().st_size}
                if name.endswith((".md", ".tex", ".json", ".bib")):
                    try:
                        entry["preview"] = candidate.read_text(
                            encoding="utf-8", errors="replace"
                        )[:1200]
                    except OSError:
                        pass
                out["files"][key] = entry
                break
    # Dirs: record path + child count.
    for key, name in _DELIVERABLE_DIRS.items():
        d = workdir / name
        if d.is_dir():
            children = sorted(p.name for p in d.iterdir())
            out["dirs"][key] = {"path": str(d), "count": len(children), "children": children[:50]}
    return out


def _run_arc_subprocess(state: RunState) -> None:
    """Spawn ARC, stream a log tail, update state on exit. Runs in a daemon thread."""
    workdir = ARC_WORKDIR / state.run_id
    workdir.mkdir(parents=True, exist_ok=True)
    state.workdir = str(workdir)

    cmd = [ARC_COMMAND, "run", "--topic", state.topic]
    if state.mode == "co-pilot":
        cmd += ["--mode", "co-pilot"]
    else:
        cmd += ["--auto-approve"]
    if ARC_CONFIG:
        cmd += ["--config", ARC_CONFIG]

    log_path = workdir / "arc-run.log"
    logger.info("[%s] launching ARC: %s (cwd=%s)", state.run_id, " ".join(cmd), workdir)
    state.status = "running"
    state.started_at = _now()

    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(  # noqa: S603 — command is operator-configured
                cmd,
                cwd=str(workdir),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
            state._proc = proc
            proc.wait()
        state.return_code = proc.returncode
        # Capture a tail of the log for quick diagnosis.
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            state.log_tail = lines[-20:]
        except OSError:
            pass
        if proc.returncode == 0:
            state.status = "completed"
        else:
            state.status = "failed"
            state.error = f"ARC exited with code {proc.returncode}"
    except FileNotFoundError:
        state.status = "failed"
        state.error = (
            f"ARC command '{ARC_COMMAND}' not found. Install AutoResearchClaw "
            f"and set ARC_COMMAND, or run the sidecar with ARC_MOCK=1."
        )
        logger.error("[%s] %s", state.run_id, state.error)
    except Exception as exc:  # noqa: BLE001 — sidecar must never crash on a run
        state.status = "failed"
        state.error = f"{type(exc).__name__}: {exc}"
        logger.exception("[%s] ARC run crashed", state.run_id)
    finally:
        state.finished_at = _now()
        state._proc = None
        logger.info("[%s] ARC run %s", state.run_id, state.status)


def _run_mock(state: RunState) -> None:
    """Mock run: 'running' for ~3s, then 'completed' with fake deliverables."""
    workdir = ARC_WORKDIR / state.run_id
    workdir.mkdir(parents=True, exist_ok=True)
    state.workdir = str(workdir)
    state.status = "running"
    state.started_at = _now()
    time.sleep(3)
    (workdir / "paper_draft.md").write_text(
        f"# (mock) {state.topic}\n\n"
        f"Hypothesis: {state.hypothesis or '(none)'}\n\n"
        "## Abstract\n\n(mock) ARC_MOCK=1 — no real pipeline was run.\n",
        encoding="utf-8",
    )
    (workdir / "reviews.md").write_text(
        "# (mock) Peer Review\n\nScore: 6/10 — mock review, idea looks plausible.\n",
        encoding="utf-8",
    )
    state.return_code = 0
    state.status = "completed"
    state.finished_at = _now()
    state.log_tail = ["(mock) ARC pipeline simulated — set ARC_MOCK=0 for real runs."]
    logger.info("[%s] mock ARC run completed", state.run_id)


# --------------------------------------------------------------------------- #
# API                                                                         #
# --------------------------------------------------------------------------- #


class StartRunRequest(BaseModel):
    topic: str = Field(..., description="Research idea / hypothesis to validate — becomes ARC's --topic")
    mode: Literal["auto", "co-pilot"] = Field("auto", description="auto = --auto-approve; co-pilot = human-in-the-loop")
    hypothesis: str = Field("", description="Optional explicit hypothesis being validated, for traceability")
    plan_doc_url: str = Field("", description="Optional link to the Feishu Doc holding the research plan")


class StartRunResponse(BaseModel):
    ok: bool
    run_id: str
    status: RunStatus
    mock: bool


app = FastAPI(
    title="feishu-classmate ARC sidecar",
    description="Async HTTP shim over AutoResearchClaw's 23-stage research pipeline.",
    version="0.1.0",
)


@app.get("/")
async def health() -> dict[str, Any]:
    with _RUNS_LOCK:
        counts: dict[str, int] = {}
        for s in _RUNS.values():
            counts[s.status] = counts.get(s.status, 0) + 1
    return {
        "ok": True,
        "service": "arc-sidecar",
        "mock": _is_mock(),
        "arc_command": ARC_COMMAND,
        "arc_config": ARC_CONFIG or None,
        "workdir": str(ARC_WORKDIR),
        "runs": counts,
    }


@app.post("/runs", response_model=StartRunResponse)
async def start_run(req: StartRunRequest) -> StartRunResponse:
    run_id = f"arc_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    state = RunState(
        run_id=run_id,
        topic=req.topic,
        mode=req.mode,
        hypothesis=req.hypothesis,
        plan_doc_url=req.plan_doc_url,
    )
    with _RUNS_LOCK:
        _RUNS[run_id] = state

    target = _run_mock if _is_mock() else _run_arc_subprocess
    threading.Thread(target=target, args=(state,), name=f"arc-{run_id}", daemon=True).start()

    logger.info("[%s] queued: topic=%r mode=%s mock=%s", run_id, req.topic, req.mode, _is_mock())
    return StartRunResponse(ok=True, run_id=run_id, status=state.status, mock=_is_mock())


@app.get("/runs")
async def list_runs() -> dict[str, Any]:
    with _RUNS_LOCK:
        return {"ok": True, "runs": [s.public() for s in _RUNS.values()]}


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    with _RUNS_LOCK:
        state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"unknown run_id: {run_id}")
    return {"ok": True, **state.public()}


@app.get("/runs/{run_id}/result")
async def get_run_result(run_id: str) -> dict[str, Any]:
    with _RUNS_LOCK:
        state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"unknown run_id: {run_id}")
    deliverables = None
    if state.status == "completed":
        deliverables = _scan_deliverables(Path(state.workdir))
    return {"ok": True, **state.public(), "deliverables": deliverables}


@app.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, Any]:
    with _RUNS_LOCK:
        state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"unknown run_id: {run_id}")
    proc = state._proc
    if proc is not None and proc.poll() is None:
        proc.terminate()
        state.status = "failed"
        state.error = "cancelled by request"
        state.finished_at = _now()
        return {"ok": True, "run_id": run_id, "status": state.status, "cancelled": True}
    return {"ok": True, "run_id": run_id, "status": state.status, "cancelled": False}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("SIDECAR_PORT", "8092"))
    ARC_WORKDIR.mkdir(parents=True, exist_ok=True)
    logger.info("ARC sidecar starting on :%d (mock=%s, workdir=%s)", port, _is_mock(), ARC_WORKDIR)
    uvicorn.run(app, host="127.0.0.1", port=port)
