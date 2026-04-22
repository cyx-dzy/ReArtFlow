"""Security validation utilities for input handling.

Provides URL validation to prevent SSRF and a simple secret loader that enforces
environment‑variable based configuration.
"""

import os
import re
import urllib.parse
from typing import List


def validate_repository_url(url: str, allowed_hosts: List[str]) -> None:
    """Validate a repository URL before any network request.

    Checks performed:
        * Scheme must be HTTPS.
        * Host must be in ``allowed_hosts``.
        * Disallow IP literals, ``localhost`` and ``127.0.0.1``.
        * Disallow suspicious path components such as ``..``.
    Raises:
        ValueError – if any check fails.
    """
    if not url:
        raise ValueError("URL is empty")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS URLs are allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("URL must contain a hostname")
    # reject IP addresses and localhost
    if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", host) or host in {"localhost", "127.0.0.1"}:
        raise ValueError("IP addresses or localhost are not allowed in repository URLs")
    if host not in allowed_hosts:
        raise ValueError(f"Host '{host}' is not in the allowed list: {allowed_hosts}")
    # reject path traversal attempts
    if ".." in (parsed.path or ""):
        raise ValueError("Path traversal components ('..') are not allowed in the URL")
    # optional: enforce no query parameters (tighten further if needed)
    if parsed.query:
        raise ValueError("Query parameters are not allowed in repository URLs")


def load_secret(name: str) -> str:
    """Load a secret from the environment.

    Raises ``RuntimeError`` if the variable is missing or empty.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required secret '{name}' not set in environment")
    return value

__all__ = ["validate_repository_url", "load_secret"]
