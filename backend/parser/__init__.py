"""Public API for the parser package.

Provides ``parse_project`` which walks a directory, parses files in parallel using the
placeholder ``tree_sitter_pool`` implementation, and returns a list of ``ParsedFile``
instances.
"""

import os
import concurrent.futures
from pathlib import Path
from typing import List

from .tree_sitter_pool import parse_file
from .models import ParsedFile

# Simple list of extensions we consider parsable (matches the mapping in tree_sitter_pool).
SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".html",
    ".css",
    ".vue",
    ".tsx",
    ".jsx",
}

def _is_supported(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS

def parse_project(source_path: str) -> List[ParsedFile]:
    """Parse every supported source file under ``source_path``.

    The function walks the directory tree, dispatches each file to ``parse_file``
    using a ``ThreadPoolExecutor`` and returns a list of ``ParsedFile`` objects.
    """
    root = Path(source_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Source path {source_path} is not a directory")

    files = [str(p) for p in root.rglob("*") if p.is_file() and _is_supported(str(p))]
    results: List[ParsedFile] = []
    # Use a worker count proportional to CPU cores (default in ThreadPoolExecutor).
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(parse_file, fp): fp for fp in files}
        for future in concurrent.futures.as_completed(future_to_path):
            data = future.result()
            results.append(ParsedFile(**data))
    # Sort by path for deterministic output.
    results.sort(key=lambda x: x.path)
    return results

__all__ = ["parse_project", "ParsedFile", "SUPPORTED_EXTENSIONS"]
