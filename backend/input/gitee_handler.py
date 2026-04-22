"""Gitee repository input handler.

Works similarly to the GitHub handler but allows ``gitee.com`` as host.
"""

import os
import subprocess
import tempfile
from typing import Dict, Any

from ..security.validation import validate_repository_url
from .processor import InputProcessor


class GiteeInputProcessor(InputProcessor):
    """Clone a Gitee repository after URL validation.

    Expected payload keys:
        - ``repo_url``: HTTPS URL of the Gitee repository.
    """

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        repo_url = payload.get("repo_url")
        if not repo_url:
            raise ValueError("Missing 'repo_url' in payload")
        validate_repository_url(repo_url, allowed_hosts=["gitee.com"])

        tmp_dir = tempfile.mkdtemp(prefix="gitee_clone_")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmp_dir],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git clone failed for {repo_url}: {e}")
        return {"source_type": "gitee", "path": tmp_dir}

__all__ = ["GiteeInputProcessor"]
