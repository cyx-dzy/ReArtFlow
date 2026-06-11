"""Public API for the parser package."""

import concurrent.futures
from pathlib import Path
from typing import Callable, List, Optional

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

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".vite",
    "coverage",
}


def _is_supported(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part in IGNORED_DIRECTORIES for part in relative.parts)


ProgressCallback = Callable[[int, int, str], None]


def parse_project(source_path: str, progress_callback: Optional[ProgressCallback] = None) -> List[ParsedFile]:
    root = Path(source_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Source path {source_path} is not a directory")

    files = [
        str(path)
        for path in root.rglob("*")
        if path.is_file() and not _is_ignored(path, root) and _is_supported(str(path))
    ]
    results: List[ParsedFile] = []
    total = len(files)
    if progress_callback:
        progress_callback(0, total, "discovered")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(parse_file, file_path): file_path for file_path in files}
        for completed, future in enumerate(concurrent.futures.as_completed(future_to_path), start=1):
            data = future.result()
            results.append(ParsedFile(**data))
            if progress_callback:
                progress_callback(completed, total, future_to_path[future])
    results.sort(key=lambda item: item.path)
    return results


__all__ = ["parse_project", "ParsedFile", "SUPPORTED_EXTENSIONS", "IGNORED_DIRECTORIES"]
