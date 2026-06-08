"""Public API for the parser package."""

import concurrent.futures
from pathlib import Path
from typing import List

from .models import ParsedFile
from .tree_sitter_pool import parse_file

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
}


def _is_supported(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


def parse_project(source_path: str) -> List[ParsedFile]:
    root = Path(source_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Source path {source_path} is not a directory")

    files = [str(path) for path in root.rglob("*") if path.is_file() and _is_supported(str(path))]
    results: List[ParsedFile] = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(parse_file, file_path): file_path for file_path in files}
        for future in concurrent.futures.as_completed(future_to_path):
            data = future.result()
            results.append(ParsedFile(**data))
    results.sort(key=lambda item: item.path)
    return results


__all__ = ["parse_project", "ParsedFile", "SUPPORTED_EXTENSIONS"]
