"""Zip input handler.

Validates that the uploaded file is a zip archive, extracts it safely to a temporary directory,
and returns a descriptor dict.
"""

import os
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any

from .processor import InputProcessor


class ZipInputProcessor(InputProcessor):
    """Handle zip file uploads.

    Expected payload keys:
        - ``filename``: Name of the uploaded file (used for basic extension check).
        - ``file_path``: Absolute path to the uploaded zip on the server.
    """

    def _is_zip(self, file_path: str) -> bool:
        return zipfile.is_zipfile(file_path)

    def _safe_extract(self, zip_path: str, extract_to: str) -> None:
        """Extract zip safely, preventing path traversal.
        """
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                # Resolve target path and ensure it stays within extraction dir
                target_path = Path(extract_to) / member.filename
                if not str(target_path.resolve()).startswith(str(Path(extract_to).resolve())):
                    raise Exception("Zip entry attempts path traversal: %s" % member.filename)
                zf.extract(member, extract_to)

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = payload.get("file_path")
        if not file_path or not os.path.isfile(file_path):
            raise ValueError("Invalid or missing 'file_path' in payload")
        if not self._is_zip(file_path):
            raise ValueError("Provided file is not a valid zip archive")

        # Create a temporary directory for extraction
        tmp_dir = tempfile.mkdtemp(prefix="zip_extract_")
        self._safe_extract(file_path, tmp_dir)
        return {"source_type": "zip", "path": tmp_dir}

__all__ = ["ZipInputProcessor"]
