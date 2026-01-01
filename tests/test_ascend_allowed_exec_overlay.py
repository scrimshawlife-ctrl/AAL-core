"""
Capability Enforcement Test: ASCEND phase requires 'exec' capability
Proves that overlays without 'exec' cannot use ASCEND phase.
"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_ascend_allowed_for_exec_capable_overlay():
    """Test that ASCEND works when 'exec' capability is declared."""
    r = client.post(
        "/invoke/abraxas_exec",
        json={"phase": "ASCEND", "data": {"op": "hash", "value": "hello"}}
    )
    assert r.status_code == 200
    out = r.json()
    assert out["ok"] is True
    assert out["overlay"] == "abraxas_exec"
    assert out["phase"] == "ASCEND"

    # Check the result contains exec operation output
    result = out.get("result")
    assert result is not None
    assert result.get("status") == "ascended"
    assert result.get("operation") == "hash"
    assert result.get("exec_performed") is True
    assert "output" in result  # Hash output


def test_ascend_blocked_for_analysis_only_overlay():
    """Test that ASCEND is blocked when only 'analysis' capability declared."""
    # abraxas overlay only has 'analysis' capability, not 'exec'
    r = client.post(
        "/invoke/abraxas",
        json={"phase": "ASCEND", "data": {"op": "hash", "value": "hello"}}
    )
    # Phase is present, but policy must deny due to missing 'exec' capability.
    assert r.status_code == 403
    assert "exec" in r.json()["detail"]


def test_exec_overlay_lists_ascend_phase():
    """Test that abraxas_exec lists ASCEND in its phases."""
    r = client.get("/overlays")
    assert r.status_code == 200

    overlays = r.json()["overlays"]
    abraxas_exec = [o for o in overlays if o["name"] == "abraxas_exec"]
    assert len(abraxas_exec) == 1

    overlay = abraxas_exec[0]
    assert "ASCEND" in overlay["phases"]
    assert "exec" in overlay["capabilities"]
    assert "analysis" in overlay["capabilities"]


def test_analysis_overlay_does_not_list_ascend():
    """Test that abraxas (analysis-only) lists ASCEND but lacks 'exec'."""
    r = client.get("/overlays")
    assert r.status_code == 200

    overlays = r.json()["overlays"]
    abraxas = [o for o in overlays if o["name"] == "abraxas"]
    assert len(abraxas) == 1

    overlay = abraxas[0]
    assert "exec" not in overlay["capabilities"]
    assert "analysis" in overlay["capabilities"]
    assert "ASCEND" in overlay["phases"]


def test_exec_overlay_can_use_clear_phase():
    """Test that exec-capable overlays can still use read-only phases."""
    r = client.post(
        "/invoke/abraxas_exec",
        json={"phase": "CLEAR", "data": {"prompt": "test"}}
    )
    assert r.status_code == 200
    out = r.json()
    assert out["ok"] is True
    assert out["phase"] == "CLEAR"

    result = out.get("result")
    assert result.get("readonly") is True
