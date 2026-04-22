import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.parse_endpoint import router as parse_router

app = FastAPI()
app.include_router(parse_router, prefix="/api")
client = TestClient(app)

def test_parse_endpoint_returns_parsed_files(tmp_path: Path):
    # Create a simple JavaScript file
    sample_file = tmp_path / "sample.js"
    sample_file.write_text("function hello() { return 42; }")
    # Call the endpoint with the temporary directory as source_path
    response = client.post("/api/parse", json={"source_path": str(tmp_path)})
    assert response.status_code == 200
    data = response.json()
    # Should return a list with at least one parsed entry
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    # Verify essential fields exist and have reasonable values
    expected_keys = {"path", "size", "mtime", "parse_time_ms", "language", "ast_summary"}
    assert set(first.keys()) == expected_keys
    assert first["language"] == "JavaScript"
    assert first["ast_summary"] == {"functions": 0, "classes": 0, "imports": 0, "calls": 0}
