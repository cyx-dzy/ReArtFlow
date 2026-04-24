"""Semantic layer package.

Provides AI-powered code explanation and mind‑map generation.
"""

# Export public symbols for convenience
from .llm_client import LLMClient
from .prompt_templates import render_prompt
from .cache import get_cached, set_cached
from .formatter import to_mermaid, to_g6
