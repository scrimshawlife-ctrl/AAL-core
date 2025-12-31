"""
Bus-only regression test for overlay invocation.
Prevents spine breakage by testing the AAL-Core bus independently.
"""
import os
import json
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient
from main import app


def test_invoke_overlay():
    """Test basic overlay invocation through the bus."""
    c = TestClient(app)
    r = c.post(
        "/invoke/abraxas",
        json={"phase": "OPEN", "data": {"prompt": "hi", "intent": "smoke"}}
    )
    assert r.status_code == 200
    out = r.json()
    assert out["ok"] is True
    assert out["overlay"] == "abraxas"
    assert out["phase"] == "OPEN"
    assert "request_id" in out
    assert "payload_hash" in out
    assert "result" in out


def test_invoke_all_phases():
    """Test all four Abraxas phases."""
    c = TestClient(app)
    phases = ["OPEN", "ALIGN", "CLEAR", "SEAL"]

    for phase in phases:
        r = c.post(
            "/invoke/abraxas",
            json={"phase": phase, "data": {"prompt": f"test_{phase}", "intent": "test"}}
        )
        assert r.status_code == 200
        out = r.json()
        assert out["ok"] is True
        assert out["phase"] == phase


def test_invalid_phase():
    """Test rejection of invalid phase."""
    c = TestClient(app)
    r = c.post(
        "/invoke/abraxas",
        json={"phase": "INVALID", "data": {"prompt": "test"}}
    )
    assert r.status_code == 400


def test_list_overlays():
    """Test overlay listing endpoint."""
    c = TestClient(app)
    r = c.get("/overlays")
    assert r.status_code == 200
    out = r.json()
    assert "overlays" in out
    assert len(out["overlays"]) > 0
    # Check abraxas is listed
    abraxas = [o for o in out["overlays"] if o["name"] == "abraxas"]
    assert len(abraxas) == 1
    assert abraxas[0]["version"] == "2.1"
    assert abraxas[0]["status"] == "active"
    assert set(abraxas[0]["phases"]) == {"OPEN", "ALIGN", "ASCEND", "CLEAR", "SEAL"}


def test_provenance_logging():
    """Test that invocations are logged to provenance."""
    c = TestClient(app)

    # Make a request
    r = c.post(
        "/invoke/abraxas",
        json={"phase": "CLEAR", "data": {"prompt": "provenance_test", "intent": "test"}}
    )
    assert r.status_code == 200
    request_id = r.json()["request_id"]

    # Check provenance log
    r = c.get("/provenance?limit=10")
    assert r.status_code == 200
    out = r.json()
    assert "events" in out

    # Find our event
    matching = [e for e in out["events"] if e.get("request_id") == request_id]
    assert len(matching) == 1
    event = matching[0]
    assert event["overlay"] == "abraxas"
    assert event["phase"] == "CLEAR"
    assert "payload_hash" in event
    # Payload presence depends on AAL_DEV_LOG_PAYLOAD env var
    if os.environ.get("AAL_DEV_LOG_PAYLOAD") == "1":
        assert "payload" in event
    assert event["ok"] is True


def test_dev_mode_payload_logging():
    """Test that AAL_DEV_LOG_PAYLOAD controls payload logging."""
    # Set dev mode
    os.environ["AAL_DEV_LOG_PAYLOAD"] = "1"

    c = TestClient(app)
    r = c.post(
        "/invoke/abraxas",
        json={"phase": "OPEN", "data": {"prompt": "dev_test", "intent": "test"}}
    )
    assert r.status_code == 200
    request_id = r.json()["request_id"]

    # Check that payload was logged
    r = c.get("/provenance?limit=10")
    events = r.json()["events"]
    matching = [e for e in events if e.get("request_id") == request_id]
    assert len(matching) == 1
    assert "payload" in matching[0]
    assert matching[0]["payload"]["prompt"] == "dev_test"

    # Unset dev mode
    os.environ.pop("AAL_DEV_LOG_PAYLOAD", None)

    # Make another request
    r = c.post(
        "/invoke/abraxas",
        json={"phase": "OPEN", "data": {"prompt": "prod_test", "intent": "test"}}
    )
    assert r.status_code == 200
    request_id = r.json()["request_id"]

    # Check that payload was NOT logged
    r = c.get("/provenance?limit=10")
    events = r.json()["events"]
    matching = [e for e in events if e.get("request_id") == request_id]
    assert len(matching) == 1
    assert "payload" not in matching[0]
    assert "payload_hash" in matching[0]  # But hash should still be there


def test_replay_functionality():
    """Test that replay tool works with dev mode payloads."""
    # Set dev mode
    os.environ["AAL_DEV_LOG_PAYLOAD"] = "1"

    c = TestClient(app)

    # Clear provenance log
    log_path = Path(__file__).parent.parent / "logs" / "provenance.jsonl"
    if log_path.exists():
        log_path.unlink()

    # Make a request
    r = c.post(
        "/invoke/abraxas",
        json={"phase": "ALIGN", "data": {"prompt": "replay_test", "intent": "test"}}
    )
    assert r.status_code == 200
    original_payload_hash = r.json()["payload_hash"]

    # Replay line 1
    result = subprocess.run(
        ["python3", "TOOLS/replay.py", "1"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    assert result.returncode == 0
    assert "Replaying event from line 1" in result.stdout
    assert "abraxas" in result.stdout
    assert "ALIGN" in result.stdout
    assert '"ok": true' in result.stdout

    # Cleanup
    os.environ.pop("AAL_DEV_LOG_PAYLOAD", None)
