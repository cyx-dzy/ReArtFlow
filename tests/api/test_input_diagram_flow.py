from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.app import app


client = TestClient(app)


def test_local_input_generates_retrievable_diagram(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    sample = tmp_path / "sample.py"
    sample.write_text("import os\n\ndef hello():\n    return os.getcwd()\n", encoding="utf-8")

    response = client.post("/input", json={"type": "local", "payload": {"dir_path": str(tmp_path)}})
    assert response.status_code == 200
    created = response.json()
    assert created["status"] == "ready"
    assert created["project_id"]
    assert "sample.py" in str(created["g6"])

    diagram_response = client.get(f"/diagram/{created['project_id']}")
    assert diagram_response.status_code == 200
    diagram = diagram_response.json()
    assert diagram["project_id"] == created["project_id"]
    assert diagram["status"] == "ready"
    assert "sample.py" in str(diagram["g6"])
    assert "模块一" not in str(diagram["g6"])


def test_missing_diagram_returns_404():
    response = client.get("/diagram/not-a-real-project")
    assert response.status_code == 404
