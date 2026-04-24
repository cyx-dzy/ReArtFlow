"""Unified LLM client supporting OpenAI and Qianwen (千问) APIs.

The client reads configuration from environment variables:
    LLM_PROVIDER   – "openai" or "qianwen"
    LLM_MODEL      – model identifier (e.g., "gpt-4o", "gpt-4-turbo", "glm-4-0520")
    OPENAI_API_KEY – required for OpenAI provider
    QIANWEN_API_KEY – required for Qianwen provider

It exposes a single method ``generate_explanation`` which returns a dict:
    {
        "explanation": <Chinese text>,
        "diagram": <structured dict for mind‑map>
    }
The request uses a function‑calling schema so the LLM returns JSON directly.
If the primary provider fails (network error or non‑2xx status), the client
automatically retries with the secondary provider (if configured).
"""

import os
try:
    import yaml
except ImportError:
    yaml = None
import json
import hashlib
import time
import logging
from .cache import set_cached
from typing import Dict, Any

# Optional imports – may not be installed in all environments
try:
    import openai
except ImportError:  # pragma: no cover
    openai = None
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: build a deterministic cache key from inputs
# ---------------------------------------------------------------------------
def _build_key(code: str, provider: str, model: str, prompt_version: str = "v1") -> str:
    raw = f"{code}\n{provider}\n{model}\n{prompt_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Main client class
# ---------------------------------------------------------------------------
class LLMClient:
    def __init__(self):
        # Load configuration from optional YAML file (default: config/llm.yaml)
        config_path = os.getenv("LLM_CONFIG_PATH", "config/llm.yaml")
        yaml_cfg = {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_cfg = yaml.safe_load(f) if yaml else {}
        except FileNotFoundError:
            logger.debug("LLM YAML config %s not found, falling back to env vars", config_path)
        except Exception as e:
            logger.error("Failed to load LLM YAML config %s: %s", config_path, e)

        # Environment variables take precedence over YAML values
        self.provider = (os.getenv("LLM_PROVIDER") or yaml_cfg.get("LLM_PROVIDER", "openai")).lower()
        self.api_url = os.getenv("LLM_API_URL") or yaml_cfg.get("LLM_API_URL")
        self.model = os.getenv("LLM_MODEL") or yaml_cfg.get("LLM_MODEL", "gpt-4o")
        self.openai_key = os.getenv("OPENAI_API_KEY") or yaml_cfg.get("OPENAI_API_KEY")
        self.qianwen_key = os.getenv("QIANWEN_API_KEY") or yaml_cfg.get("QIANWEN_API_KEY")
        if self.provider not in {"openai", "qianwen"}:
            raise ValueError("LLM_PROVIDER must be 'openai' or 'qianwen'")
        # Pre‑load the function schema – used by both providers
        self.function_schema = {
            "name": "explain_code",
            "description": "Explain the given source code in Chinese and provide a diagram structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "explanation": {"type": "string", "description": "Chinese natural‑language explanation of the code"},
                    "diagram": {"type": "object", "description": "Structured representation for mind‑map generation"},
                },
                "required": ["explanation", "diagram"],
            },
        }

    # ---------------------------------------------------------------------
    # Public entry point
    # ---------------------------------------------------------------------
    def generate_explanation(self, code: str, language: str) -> Dict[str, Any]:
        """Generate a Chinese explanation and diagram for *code*.

        The method first checks the cache (via ``backend.semantic.cache``).
        If a cached response exists, it returns it directly. Otherwise it
        calls the configured LLM provider, stores the result in the cache,
        and returns the JSON dict.
        """
        from .cache import get_cached, set_cached  # lazy import to avoid circular deps

        cache_key = _build_key(code, self.provider, self.model)
        cached = get_cached(cache_key)
        if cached:
            logger.debug("LLM cache hit for key %s", cache_key)
            return cached
        # Build the prompt messages using the Prompt module
        from .prompt_templates import render_prompt
        messages = render_prompt(code, language)
        # Try primary provider first
        try:
            if self.provider == "openai":
                return self._call_openai(messages, cache_key)
            else:
                return self._call_qianwen(messages, cache_key)
        except Exception as exc:  # pragma: no cover – fallback path
            logger.warning("Primary LLM provider failed (%s): %s", self.provider, exc)
            # Attempt fallback to the other provider
            fallback = "qianwen" if self.provider == "openai" else "openai"
            if fallback == "openai":
                return self._call_openai(messages, cache_key)
            else:
                return self._call_qianwen(messages, cache_key)

    # ---------------------------------------------------------------------
    # OpenAI implementation (chat completions with function calling)
    # ---------------------------------------------------------------------
    def _call_openai(self, messages: list[dict], cache_key: str) -> Dict[str, Any]:
        if not openai:
            raise RuntimeError("openai package not installed")
        openai.api_key = self.openai_key
        # If a custom API base URL is provided (e.g., a proxy/gateway), configure the OpenAI client
        if self.api_url:
            openai.api_base = self.api_url
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            functions=[self.function_schema],
            function_call={"name": "explain_code"},
        )
        # Extract function response
        result = response["choices"][0]["message"]["function_call"]["arguments"]
        parsed = json.loads(result)
        set_cached(cache_key, parsed)
        return parsed

    # ---------------------------------------------------------------------
    # Qianwen implementation (similar function‑call style via JSON payload)
    # ---------------------------------------------------------------------
    def _call_qianwen(self, messages: list[dict], cache_key: str) -> Dict[str, Any]:
        # Qianwen API endpoint – this is a generic HTTP POST
        endpoint = self.api_url if self.api_url else "https://api.qianwen.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.qianwen_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "functions": [self.function_schema],
            "function_call": {"name": "explain_code"},
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Qianwen returns "function_call" similarly
        func = data["choices"][0]["message"].get("function_call")
        if not func:
            raise RuntimeError("Qianwen response missing function_call")
        parsed = func["arguments"]  # already a dict in Qianwen response
        set_cached(cache_key, parsed)
        return parsed
