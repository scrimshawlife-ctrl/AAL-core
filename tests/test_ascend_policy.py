from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ascend_blocked_without_exec_capability():
    r = client.post(
        "/invoke/abraxas",
        json={"phase": "ASCEND", "data": {"op": "danger"}}
    )
    assert r.status_code == 403
    assert "exec" in r.json()["detail"]
