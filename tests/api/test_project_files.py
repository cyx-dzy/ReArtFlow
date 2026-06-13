from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.app import app


client = TestClient(app)


def _create_project(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    (tmp_path / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    response = client.post("/input", json={"type": "local", "payload": {"dir_path": str(tmp_path)}})
    assert response.status_code == 200
    return response.json()["project_id"]


def test_project_files_and_content(tmp_path: Path, monkeypatch):
    project_id = _create_project(tmp_path, monkeypatch)

    files_response = client.get(f"/projects/{project_id}/files")
    assert files_response.status_code == 200
    files = files_response.json()["files"]
    assert {item["path"] for item in files} >= {"main.py", "README.md"}

    content_response = client.get(f"/projects/{project_id}/files/content", params={"path": "main.py"})
    assert content_response.status_code == 200
    content = content_response.json()
    assert content["path"] == "main.py"
    assert "def hello" in content["content"]
    assert content["language"] == "Python"


def test_project_files_exclude_assets_and_data_files(tmp_path: Path, monkeypatch):
    project_id = _create_project(tmp_path, monkeypatch)
    (tmp_path / "logo.png").write_bytes(b"fake image")
    (tmp_path / "data.csv").write_text("name,value\nfoo,1\n", encoding="utf-8")
    (tmp_path / "notes.jpg").write_bytes(b"fake image")

    files_response = client.get(f"/projects/{project_id}/files")
    assert files_response.status_code == 200
    paths = {item["path"] for item in files_response.json()["files"]}

    assert "main.py" in paths
    assert "README.md" in paths
    assert "logo.png" not in paths
    assert "data.csv" not in paths
    assert "notes.jpg" not in paths

    csv_response = client.get(f"/projects/{project_id}/files/content", params={"path": "data.csv"})
    assert csv_response.status_code == 404


def test_project_file_content_rejects_path_traversal(tmp_path: Path, monkeypatch):
    project_id = _create_project(tmp_path, monkeypatch)
    response = client.get(f"/projects/{project_id}/files/content", params={"path": "../secret.txt"})
    assert response.status_code == 400
