# Unified LLM client using LangChain
"""
Provides a client that generates Chinese explanations and diagram data for source code.
Implemented on top of LangChain's chat model wrappers, supporting OpenAI and Qianwen
via function calling. Caches results in the existing cache module.
"""

import os
import json
import hashlib
import logging
from typing import Dict, Any

# LangChain and OpenAI/Qwen imports
# OpenAI client (new package)
try:
    from langchain_openai import ChatOpenAI
except Exception:
    # Fallback to legacy import if the new package is not installed
    try:
        from langchain.chat_models import ChatOpenAI
    except Exception:
        ChatOpenAI = None
# Qwen client (separate package)
try:
    from langchain_qwen import ChatQwen
except Exception:
    # If not installed, we will fall back to raw HTTP calls
    ChatQwen = None

# Message schemas – use core messages to avoid heavy dependencies
try:
    from langchain_core.messages import HumanMessage, AIMessage, FunctionMessage
except Exception:
    # Fallback imports if core not available
    from langchain.schema import HumanMessage, AIMessage, FunctionMessage


# Optional YAML and OpenAI imports
try:
    import openai
except Exception:
    openai = None

# Optional YAML config
try:
    import yaml
except ImportError:
    yaml = None

from .cache import get_cached, set_cached

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: deterministic cache key
# ---------------------------------------------------------------------------
def _build_key(code: str, provider: str, model: str, prompt_version: str = "v1") -> str:
    raw = f"{code}\n{provider}\n{model}\n{prompt_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# LLMClient implementation
# ---------------------------------------------------------------------------
class LLMClient:
    def __init__(self):
        # Load optional YAML config
        # Resolve config file relative to this module if not overridden by env
        config_path = os.getenv("LLM_CONFIG_PATH") or os.path.join(os.path.dirname(__file__), "config", "llm.yaml")
        yaml_cfg: Dict[str, Any] = {}
        try:
            if yaml:
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_cfg = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.debug("LLM config %s not found, falling back to env vars", config_path)
        except Exception as e:
            logger.error("Failed to load LLM config %s: %s", config_path, e)

        # Environment overrides
        # Load configuration values – environment variables take precedence.
        # YAML may use either the explicit LL* keys or simplified names.
        self.provider = (
            os.getenv("LLM_PROVIDER")
            or yaml_cfg.get("LLM_PROVIDER")
            or yaml_cfg.get("provider")
            or "openai"
        ).lower()
        self.model = (
            os.getenv("LLM_MODEL")
            or yaml_cfg.get("LLM_MODEL")
            or yaml_cfg.get("model")
            or "gpt-4o"
        )
        self.api_url = (
            os.getenv("LLM_API_URL")
            or yaml_cfg.get("LLM_API_URL")
            or yaml_cfg.get("api_url")
            or yaml_cfg.get("base_url")
        )
        self.openai_key = (
            os.getenv("OPENAI_API_KEY")
            or yaml_cfg.get("OPENAI_API_KEY")
            or yaml_cfg.get("api_key")
            or yaml_cfg.get("openai_key")
        )
        self.qianwen_key = (
            os.getenv("QIANWEN_API_KEY")
            or yaml_cfg.get("QIANWEN_API_KEY")
            or yaml_cfg.get("qianwen_key")
            or yaml_cfg.get("api_key")
        )
        if self.provider not in {"openai", "qianwen"}:
            raise ValueError("LLM_PROVIDER must be 'openai' or 'qianwen'")

        # Function schema for LangChain function calling
        self.function_schema = {
            "name": "explain_code",
            "description": "Explain the given source code in Chinese and provide a diagram structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "explanation": {"type": "string", "description": "Chinese explanation of the code"},
                    "diagram": {"type": "object", "description": "Structured diagram data"},
                },
                "required": ["explanation", "diagram"],
            },
        }

    # ---------------------------------------------------------------------
    # Public method
    # ---------------------------------------------------------------------
    def generate_explanation(self, code: str, language: str) -> Dict[str, Any]:
        """Generate explanation & diagram for *code*.

        Checks cache first; otherwise calls the configured provider via LangChain.
        """
        cache_key = _build_key(code, self.provider, self.model)
        cached = get_cached(cache_key)
        if cached:
            logger.debug("LLM cache hit for key %s", cache_key)
            return cached

        # Prepare messages – simple system prompt + user code
        system_prompt = (
            "你是一个代码解释专家，使用中文解释下面的代码，并返回符合函数 schema 的 JSON。"
        )
        user_prompt = f"语言: {language}\n代码:\n```{language}\n{code}\n```"
        messages = [HumanMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        try:
            if self.provider == "openai":
                result = self._call_openai(messages, cache_key)
            else:
                result = self._call_qianwen(messages, cache_key)
        except Exception as exc:
            logger.warning("Primary provider %s failed: %s", self.provider, exc)
            fallback = "qianwen" if self.provider == "openai" else "openai"
            # Fallback only if credentials for the fallback provider are present
            if fallback == "openai" and self.openai_key:
                result = self._call_openai(messages, cache_key)
            elif fallback == "qianwen" and self.qianwen_key:
                result = self._call_qianwen(messages, cache_key)
            else:
                raise
            return result

    # ---------------------------------------------------------------------
    # OpenAI implementation using LangChain ChatOpenAI with function calling
    # ---------------------------------------------------------------------
    def _call_openai(self, messages, cache_key):
        """Call OpenAI-compatible endpoint via raw HTTP request.
        Supports function calling when the endpoint returns a `function_call` field.
        If the endpoint does not support function calls, falls back to plain text response.
        """
        if not self.openai_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI provider")
        # Build payload
        payload_messages = [{"role": "system", "content": m.content} if isinstance(m, HumanMessage) else {"role": "user", "content": m.content} for m in messages]
        payload = {
            "model": self.model,
            "messages": payload_messages,
            "functions": [self.function_schema],
            "function_call": {"name": "explain_code"},
        }
        # Determine endpoint URL
        base = self.api_url.rstrip('/') if self.api_url else "https://api.openai.com/v1"
        endpoint = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        import requests
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Try to extract function call
        message = data.get("choices", [{}])[0].get("message", {})
        func = message.get("function_call")
        if func and "arguments" in func:
            parsed = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
        else:
            # No function call – use plain content as explanation
            content = message.get("content", "")
            parsed = {"explanation": content, "diagram": {}}
        set_cached(cache_key, parsed)
        return parsed

    # ---------------------------------------------------------------------
    # Qianwen implementation (fallback) – uses raw HTTP via requests
    # ---------------------------------------------------------------------
    def _call_qianwen(self, messages, cache_key):
        # Prefer using LangChain Qwen client if available
        if ChatQwen:
            client_kwargs = {"model": self.model, "api_key": self.qianwen_key}
            if self.api_url:
                client_kwargs["base_url"] = self.api_url
            client = ChatQwen(**client_kwargs)
            response = client.invoke(messages, functions=[self.function_schema], function_call={"name": "explain_code"})
            if not isinstance(response, FunctionMessage):
                raise RuntimeError("Qianwen response missing function call data")
            parsed = json.loads(response.arguments)
            set_cached(cache_key, parsed)
            return parsed
        # Fallback to raw HTTP request
        import requests
        if not self.qianwen_key:
            raise RuntimeError("QIANWEN_API_KEY is required for Qianwen provider")
        endpoint = self.api_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        payload = {
            "model": self.model,
            "messages": [{"role": m.type, "content": m.content} for m in messages],
            "functions": [self.function_schema],
            "function_call": {"name": "explain_code"},
        }
        headers = {"Authorization": f"Bearer {self.qianwen_key}", "Content-Type": "application/json"}
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        func = data["choices"][0]["message"].get("function_call")
        if not func:
            raise RuntimeError("Qianwen response missing function call")
        parsed = func["arguments"] if isinstance(func["arguments"], dict) else json.loads(func["arguments"])  # ensure dict
        set_cached(cache_key, parsed)
        return parsed
