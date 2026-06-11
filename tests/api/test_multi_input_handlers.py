import os
import subprocess
import time
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.app import app
from backend.input.gitee_handler import GiteeInputProcessor
from backend.input.github_handler import GitHubInputProcessor


client = TestClient(app)


def test_raw_zip_upload_generates_diagram(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("main.py", "def run():\n    return 1\n")

    response = client.post("/input/zip", content=zip_path.read_bytes(), headers={"Content-Type": "application/zip"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["project_id"]
    assert "main.py" in str(payload["g6"])


def test_zip_job_reports_progress_and_generates_diagram(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("QIANWEN_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "qianwen")
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("main.py", "def run():\n    return 1\n")

    response = client.post("/input/zip/jobs", content=zip_path.read_bytes(), headers={"Content-Type": "application/zip"})

    assert response.status_code == 202
    job = response.json()
    assert job["job_id"]
    deadline = time.time() + 10
    while job["status"] in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.1)
        job = client.get(f"/input/jobs/{job['job_id']}").json()

    assert job["status"] == "ready"
    assert job["progress"] == 100
    assert job["result"]["project_id"]
    assert "main.py" in str(job["result"]["g6"])


def test_github_handler_validates_and_clones_with_mock(monkeypatch):
    calls = []

    def fake_run(command, check, stdout, stderr):
        calls.append(command)
        os.makedirs(command[-1], exist_ok=True)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("backend.input.github_handler.subprocess.run", fake_run)
    result = GitHubInputProcessor().process({"repo_url": "https://github.com/example/repo"})

    assert result["source_type"] == "github"
    assert os.path.isdir(result["path"])
    assert calls[0][:3] == ["git", "clone", "--depth"]


def test_gitee_handler_validates_and_clones_with_mock(monkeypatch):
    calls = []

    def fake_run(command, check, stdout, stderr):
        calls.append(command)
        os.makedirs(command[-1], exist_ok=True)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("backend.input.gitee_handler.subprocess.run", fake_run)
    result = GiteeInputProcessor().process({"repo_url": "https://gitee.com/example/repo"})

    assert result["source_type"] == "gitee"
    assert os.path.isdir(result["path"])
    assert calls[0][:3] == ["git", "clone", "--depth"]
