import tempfile
from pathlib import Path

import pytest

from backend.parser import parse_project
from backend.parser.tree_sitter_pool import parse_file


def test_parse_file_returns_expected_fields():
    with tempfile.TemporaryDirectory() as td:
        file_path = Path(td) / "sample.py"
        file_path.write_text("import os\nclass Foo:\n    pass\n\ndef foo():\n    print(os.getcwd())\n")
        try:
            result = parse_file(str(file_path))
        except RuntimeError as exc:
            if "Tree-sitter runtime is not installed" in str(exc):
                pytest.skip(str(exc))
            raise
        expected_keys = {"path", "size", "mtime", "parse_time_ms", "language", "ast_summary"}
        assert set(result.keys()) == expected_keys
        assert result["path"].endswith(str(file_path))
        assert result["size"] > 0
        assert result["language"] == "Python"
        assert set(result["ast_summary"].keys()) == {"functions", "classes", "imports", "calls"}
        assert result["ast_summary"]["functions"] >= 1
        assert result["ast_summary"]["classes"] >= 1
        assert result["ast_summary"]["imports"] >= 1
        assert result["ast_summary"]["calls"] >= 1


def test_parse_project_ignores_assets_and_data_files(tmp_path):
    (tmp_path / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"fake image")
    (tmp_path / "data.csv").write_text("name,value\nfoo,1\n", encoding="utf-8")
    (tmp_path / "photo.jpg").write_bytes(b"fake image")

    parsed = parse_project(str(tmp_path))
    paths = {Path(item.path).name for item in parsed}

    assert paths == {"main.py"}
