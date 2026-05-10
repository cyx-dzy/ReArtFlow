"""Semantic layer package.

Provides AI-powered code explanation and mind‑map generation.
"""

# Export public symbols for convenience
# Lazy import LLMClient to avoid heavy dependencies during startup
try:
    from .llm_client import LLMClient
except ModuleNotFoundError:
    class LLMClient:
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("LLMClient requires optional dependencies (e.g., langchain) which are not installed.")
from .prompt_templates import render_prompt
from .cache import get_cached, set_cached
from .formatter import to_mermaid, to_g6
