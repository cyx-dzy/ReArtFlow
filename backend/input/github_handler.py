"""GitHub repository input handler.

Validates the repository URL and clones it into a temporary directory.
"""

import os
import subprocess
import tempfile
from typing import Dict, Any

from ..security.validation import validate_repository_url
from .processor import InputProcessor


class GitHubInputProcessor(InputProcessor):
    """Clone a GitHub repository after validation.

    Expected payload keys:
        - ``repo_url``: HTTPS URL of the GitHub repository.
    """

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        repo_url = payload.get("repo_url")
        if not repo_url:
            raise ValueError("Missing 'repo_url' in payload")
        # Ensure URL is allowed and safe
        validate_repository_url(repo_url, allowed_hosts=["github.com"])

        tmp_dir = tempfile.mkdtemp(prefix="github_clone_")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmp_dir],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git clone failed for {repo_url}: {e}")
        return {"source_type": "github", "path": tmp_dir}

__all__ = ["GitHubInputProcessor"]
