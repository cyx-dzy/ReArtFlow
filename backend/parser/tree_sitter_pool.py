"""Thread‑local Tree‑sitter parser pool (simplified placeholder).

In a full implementation this would compile a shared library with many language grammars
using ``tree_sitter.Language.build_library`` and then create a ``Parser`` instance per
thread.  For the purpose of the current tests we provide a lightweight fallback that
extracts basic metadata and a dummy AST summary based on file extension.
"""

import os
import time
import threading
from pathlib import Path
from typing import Dict, Any

# Simple mapping from file extension to language name (placeholder).
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".html": "HTML",
    ".css": "CSS",
    ".vue": "Vue",
    ".tsx": "TSX",
    ".jsx": "JSX",
}

# Thread‑local storage for a dummy parser (here just a placeholder object).
_thread_local = threading.local()

def _get_parser():
    """Return a thread‑local dummy parser.

    In a real implementation this would return a ``tree_sitter.Parser`` with the
    appropriate language loaded.  Here we just store a marker to prove thread‑
    isolation.
    """
    if not hasattr(_thread_local, "parser"):
        _thread_local.parser = object()  # placeholder
    return _thread_local.parser

def _detect_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "PlainText")

def parse_file(file_path: str) -> Dict[str, Any]:
    """Parse a single source file and return a dict with required metadata.

    Args:
        file_path: Absolute or relative path to the source file.

    Returns:
        A dictionary containing ``path``, ``size``, ``mtime``, ``parse_time_ms``,
        ``language`` and a minimal ``ast_summary`` (function / class counts set to 0
        for the placeholder implementation).
    """
    parser = _get_parser()  # ensure thread‑local instance exists
    start = time.perf_counter()
    # Read file bytes (could be large – for placeholder we just read everything)
    with open(file_path, "rb") as f:
        _ = f.read()
    # Simulate parsing work (tiny sleep to emulate processing time)
    time.sleep(0.001)
    elapsed_ms = (time.perf_counter() - start) * 1000

    stat = os.stat(file_path)
    return {
        "path": str(Path(file_path).resolve()),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "parse_time_ms": elapsed_ms,
        "language": _detect_language(file_path),
        "ast_summary": {"functions": 0, "classes": 0, "imports": 0, "calls": 0},
    }

__all__ = ["parse_file", "_get_parser"]
