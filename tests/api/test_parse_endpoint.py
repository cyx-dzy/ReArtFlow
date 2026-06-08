from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.parse_endpoint import router as parse_router

app = FastAPI()
app.include_router(parse_router, prefix="/api")
client = TestClient(app)


def test_parse_endpoint_returns_parsed_files(tmp_path: Path):
    sample_file = tmp_path / "sample.js"
    sample_file.write_text("import x from 'y';\nfunction hello() { return callMe(); }\n")
    response = client.post("/api/parse", json={"source_path": str(tmp_path)})
    if response.status_code == 500 and "Tree-sitter runtime is not installed" in response.text:
        pytest.skip("Tree-sitter runtime is not installed")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    expected_keys = {"path", "size", "mtime", "parse_time_ms", "language", "ast_summary"}
    assert set(first.keys()) == expected_keys
    assert first["language"] == "JavaScript"
    assert first["ast_summary"]["functions"] >= 1
    assert first["ast_summary"]["imports"] >= 1
