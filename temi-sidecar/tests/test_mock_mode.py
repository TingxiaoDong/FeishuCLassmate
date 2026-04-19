"""
Tests for the Temi sidecar running in mock mode.

All tests use FastAPI's TestClient (backed by httpx) so no real robot or
real network is needed.  The TEMI_MOCK env var is forced to "1" before the
app module is imported so the lifespan handler starts in mock mode.
"""

from __future__ import annotations

import os
import sys

# Force mock mode BEFORE importing the FastAPI app so the module-level
# _FORCE_MOCK flag is set correctly.
os.environ.setdefault("TEMI_MOCK", "1")
# Remove cached module so environment changes take effect on re-import.
for mod in list(sys.modules.keys()):
    if mod.startswith("server") or mod.startswith("adapters"):
        del sys.modules[mod]

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Module-scoped TestClient so the lifespan runs once per test module."""
    # Import here so TEMI_MOCK is already set
    from server import app  # noqa: PLC0415

    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /  — health check
# ---------------------------------------------------------------------------

class TestHealth:
    def test_status_ok(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200

    def test_response_shape(self, client: TestClient) -> None:
        data = client.get("/").json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "mock" in data
        assert data["mock"] is True
        assert "connected" in data


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_200(self, client: TestClient) -> None:
        resp = client.get("/status")
        assert resp.status_code == 200

    def test_response_shape(self, client: TestClient) -> None:
        data = client.get("/status").json()
        assert "connected" in data
        assert "battery" in data
        assert "position" in data
        assert "x" in data["position"]
        assert "y" in data["position"]
        assert "is_moving" in data
        assert "mock" in data
        assert data["mock"] is True

    def test_battery_range(self, client: TestClient) -> None:
        battery = client.get("/status").json()["battery"]
        assert 0 <= battery <= 100

    def test_connected_is_false_in_mock(self, client: TestClient) -> None:
        # In mock mode the sidecar reports connected=False (no real robot)
        assert client.get("/status").json()["connected"] is False


# ---------------------------------------------------------------------------
# POST /goto
# ---------------------------------------------------------------------------

class TestGoto:
    def test_basic_success(self, client: TestClient) -> None:
        resp = client.post("/goto", json={"location": "入口"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_mock_flag(self, client: TestClient) -> None:
        data = client.post("/goto", json={"location": "入口"}).json()
        assert data["mock"] is True

    def test_message_contains_mock_marker(self, client: TestClient) -> None:
        data = client.post("/goto", json={"location": "入口"}).json()
        assert "(mock)" in data["message"]

    def test_english_location_resolved(self, client: TestClient) -> None:
        # "entrance" should map to "入口"
        data = client.post("/goto", json={"location": "entrance"}).json()
        assert data["ok"] is True
        assert "入口" in data["message"]

    def test_unknown_location_passes_through(self, client: TestClient) -> None:
        data = client.post("/goto", json={"location": "my-custom-spot"}).json()
        assert data["ok"] is True
        assert "my-custom-spot" in data["message"]

    def test_missing_location_422(self, client: TestClient) -> None:
        resp = client.post("/goto", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /speak
# ---------------------------------------------------------------------------

class TestSpeak:
    def test_basic_success(self, client: TestClient) -> None:
        resp = client.post("/speak", json={"text": "Hello, student!"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_mock_flag(self, client: TestClient) -> None:
        assert client.post("/speak", json={"text": "Hi"}).json()["mock"] is True

    def test_voice_friendly(self, client: TestClient) -> None:
        resp = client.post("/speak", json={"text": "Hi", "voice": "friendly"})
        assert resp.json()["ok"] is True

    def test_voice_professional(self, client: TestClient) -> None:
        resp = client.post("/speak", json={"text": "Hi", "voice": "professional"})
        assert resp.json()["ok"] is True

    def test_invalid_voice_422(self, client: TestClient) -> None:
        resp = client.post("/speak", json={"text": "Hi", "voice": "robot"})
        assert resp.status_code == 422

    def test_empty_text_422(self, client: TestClient) -> None:
        resp = client.post("/speak", json={"text": ""})
        assert resp.status_code == 422

    def test_missing_text_422(self, client: TestClient) -> None:
        assert client.post("/speak", json={}).status_code == 422


# ---------------------------------------------------------------------------
# POST /stop
# ---------------------------------------------------------------------------

class TestStop:
    def test_basic_success(self, client: TestClient) -> None:
        resp = client.post("/stop", json={})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_mock_flag(self, client: TestClient) -> None:
        assert client.post("/stop", json={}).json()["mock"] is True

    def test_immediate_true(self, client: TestClient) -> None:
        resp = client.post("/stop", json={"immediate": True})
        assert resp.json()["ok"] is True

    def test_immediate_false(self, client: TestClient) -> None:
        resp = client.post("/stop", json={"immediate": False})
        assert resp.json()["ok"] is True

    def test_default_immediate(self, client: TestClient) -> None:
        resp = client.post("/stop", json={})
        assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# POST /detect-person
# ---------------------------------------------------------------------------

class TestDetectPerson:
    def test_basic_success(self, client: TestClient) -> None:
        resp = client.post("/detect-person", json={"timeout_ms": 5000})
        assert resp.status_code == 200

    def test_mock_open_id_null(self, client: TestClient) -> None:
        data = client.post("/detect-person", json={"timeout_ms": 3000}).json()
        assert data["open_id"] is None

    def test_confidence_zero_in_mock(self, client: TestClient) -> None:
        data = client.post("/detect-person", json={"timeout_ms": 3000}).json()
        assert data["confidence"] == 0.0

    def test_mock_flag(self, client: TestClient) -> None:
        data = client.post("/detect-person", json={"timeout_ms": 3000}).json()
        assert data["mock"] is True

    def test_timeout_too_small_422(self, client: TestClient) -> None:
        resp = client.post("/detect-person", json={"timeout_ms": 100})
        assert resp.status_code == 422

    def test_timeout_too_large_422(self, client: TestClient) -> None:
        resp = client.post("/detect-person", json={"timeout_ms": 99_999})
        assert resp.status_code == 422

    def test_missing_timeout_422(self, client: TestClient) -> None:
        assert client.post("/detect-person", json={}).status_code == 422


# ---------------------------------------------------------------------------
# POST /rfid-scan
# ---------------------------------------------------------------------------

class TestRfidScan:
    def test_basic_success(self, client: TestClient) -> None:
        resp = client.post("/rfid-scan", json={})
        assert resp.status_code == 200

    def test_returns_tags_list(self, client: TestClient) -> None:
        data = client.post("/rfid-scan", json={}).json()
        assert "tags" in data
        assert isinstance(data["tags"], list)

    def test_mock_flag(self, client: TestClient) -> None:
        assert client.post("/rfid-scan", json={}).json()["mock"] is True

    def test_tag_shape(self, client: TestClient) -> None:
        data = client.post("/rfid-scan", json={}).json()
        assert len(data["tags"]) > 0
        tag = data["tags"][0]
        assert "tag_id" in tag
        assert "location_estimate" in tag
        assert "rssi" in tag

    def test_rssi_is_negative(self, client: TestClient) -> None:
        data = client.post("/rfid-scan", json={}).json()
        for tag in data["tags"]:
            assert tag["rssi"] < 0

    def test_no_tags_for_unmatched_route(self, client: TestClient) -> None:
        data = client.post(
            "/rfid-scan", json={"route": ["nonexistent-location"]}
        ).json()
        # Falls back to first tag when no match; just check it's a list
        assert isinstance(data["tags"], list)

    def test_optional_route_none(self, client: TestClient) -> None:
        resp = client.post("/rfid-scan", json={"route": None})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /monitor-focus
# ---------------------------------------------------------------------------

class TestMonitorFocus:
    def test_basic_success(self, client: TestClient) -> None:
        resp = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 30},
        )
        assert resp.status_code == 200

    def test_returns_samples(self, client: TestClient) -> None:
        data = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 30},
        ).json()
        assert "samples" in data
        assert isinstance(data["samples"], list)
        assert len(data["samples"]) > 0

    def test_mock_flag(self, client: TestClient) -> None:
        data = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 10},
        ).json()
        assert data["mock"] is True

    def test_sample_shape(self, client: TestClient) -> None:
        data = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 30},
        ).json()
        sample = data["samples"][0]
        assert "ts" in sample
        assert "focused" in sample
        assert "score" in sample

    def test_score_in_range(self, client: TestClient) -> None:
        data = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 60},
        ).json()
        for s in data["samples"]:
            assert 0.0 <= s["score"] <= 1.0

    def test_focused_is_bool(self, client: TestClient) -> None:
        data = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 20},
        ).json()
        for s in data["samples"]:
            assert isinstance(s["focused"], bool)

    def test_timestamps_ascending(self, client: TestClient) -> None:
        data = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 60},
        ).json()
        ts_list = [s["ts"] for s in data["samples"]]
        assert ts_list == sorted(ts_list)

    def test_missing_open_id_422(self, client: TestClient) -> None:
        resp = client.post("/monitor-focus", json={"duration_s": 10})
        assert resp.status_code == 422

    def test_duration_too_small_422(self, client: TestClient) -> None:
        resp = client.post(
            "/monitor-focus",
            json={"student_open_id": "ou_abc123", "duration_s": 0},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /gesture
# ---------------------------------------------------------------------------

class TestGesture:
    def test_encourage(self, client: TestClient) -> None:
        resp = client.post("/gesture", json={"type": "encourage"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_poke(self, client: TestClient) -> None:
        assert client.post("/gesture", json={"type": "poke"}).json()["ok"] is True

    def test_applause(self, client: TestClient) -> None:
        assert client.post("/gesture", json={"type": "applause"}).json()["ok"] is True

    def test_nod(self, client: TestClient) -> None:
        assert client.post("/gesture", json={"type": "nod"}).json()["ok"] is True

    def test_mock_flag(self, client: TestClient) -> None:
        assert client.post("/gesture", json={"type": "nod"}).json()["mock"] is True

    def test_invalid_type_422(self, client: TestClient) -> None:
        resp = client.post("/gesture", json={"type": "dance"})
        assert resp.status_code == 422

    def test_missing_type_422(self, client: TestClient) -> None:
        assert client.post("/gesture", json={}).status_code == 422
