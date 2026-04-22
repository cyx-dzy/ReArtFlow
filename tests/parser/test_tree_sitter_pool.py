import os
import tempfile
from pathlib import Path

from backend.parser.tree_sitter_pool import parse_file

def test_parse_file_returns_expected_fields():
    # Create a temporary Python file
    with tempfile.TemporaryDirectory() as td:
        file_path = Path(td) / "sample.py"
        file_path.write_text("def foo():\n    pass\n")
        result = parse_file(str(file_path))
        # Verify required keys
        expected_keys = {"path", "size", "mtime", "parse_time_ms", "language", "ast_summary"}
        assert set(result.keys()) == expected_keys
        # Path must be absolute
        assert result["path"].endswith(str(file_path))
        # Size > 0
        assert result["size"] > 0
        # Language detection
        assert result["language"] == "Python"
        # ast_summary contains expected sub‑keys
        assert set(result["ast_summary"].keys()) == {"functions", "classes", "imports", "calls"}
