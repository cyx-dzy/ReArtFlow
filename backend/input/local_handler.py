"""Local path input handler.

Validates that a provided path exists and is a directory, then returns it.
"""

import os
from typing import Dict, Any

from .processor import InputProcessor


class LocalPathInputProcessor(InputProcessor):
    """Accept a local directory path as input.

    Expected payload keys:
        - ``dir_path``: Absolute or relative path to the source directory.
    """

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        dir_path = payload.get("dir_path")
        if not dir_path:
            raise ValueError("Missing 'dir_path' in payload")
        # Resolve to absolute path
        abs_path = os.path.abspath(dir_path)
        if not os.path.isdir(abs_path):
            raise ValueError(f"Provided path is not a directory: {abs_path}")
        # Simple sanity check – ensure we can list the directory
        if not os.access(abs_path, os.R_OK):
            raise PermissionError(f"Cannot read directory: {abs_path}")
        return {"source_type": "local", "path": abs_path}

__all__ = ["LocalPathInputProcessor"]
