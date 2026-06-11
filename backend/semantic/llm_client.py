"""LLM client with optional dependency fallbacks."""

import json
import os
from typing import Any, Dict

import requests

try:
    import openai
except ModuleNotFoundError:  # pragma: no cover
    class _OpenAIChatCompletion:
        @staticmethod
        def create(*args, **kwargs):
            raise RuntimeError("openai package is not installed")

    class _OpenAIStub:
        ChatCompletion = _OpenAIChatCompletion
        api_key = None

    openai = _OpenAIStub()

try:  # Optional dependency; not required for current request path.
    from langchain_core.prompts import ChatPromptTemplate  # noqa: F401
    from langchain_openai import ChatOpenAI  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    ChatPromptTemplate = None
    ChatOpenAI = None

from .cache import SemanticCache
from .prompt_templates import build_semantic_function_schema, build_semantic_messages


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "qianwen").lower()
        default_models = {
            "deepseek": "deepseek-chat",
            "qianwen": "qwen-plus",
            "openai": "gpt-4o-mini",
        }
        default_model = default_models.get(self.provider, "gpt-4o-mini")
        self.model = os.getenv("LLM_MODEL", default_model)
        self.cache = SemanticCache()

    def generate_explanation(self, code: str, language: str) -> Dict[str, Any]:
        cache_key = {"provider": self.provider, "model": self.model, "code": code, "language": language}
        cached = self.cache.get(cache_key)
        if cached is not None:
            return self._normalize_result(cached)

        if self.provider == "openai":
            result = self._call_openai(code, language)
        elif self.provider == "qianwen":
            result = self._call_qianwen(code, language)
        elif self.provider == "deepseek":
            result = self._call_deepseek(code, language)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        result = self._normalize_result(result)
        self.cache.set(cache_key, result)
        return result

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result.get("explanation"), str):
            result["explanation"] = ""
        if not isinstance(result.get("diagram"), dict):
            result["diagram"] = {"nodes": [], "edges": []}
        result["diagram"].setdefault("nodes", [])
        result["diagram"].setdefault("edges", [])
        return result

    def _call_openai(self, code: str, language: str) -> Dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=build_semantic_messages(code, language),
            functions=[build_semantic_function_schema()],
            function_call={"name": "describe_code_semantics"},
        )
        arguments = response["choices"][0]["message"]["function_call"]["arguments"]
        return json.loads(arguments)

    def _call_qianwen(self, code: str, language: str) -> Dict[str, Any]:
        api_key = os.getenv("QIANWEN_API_KEY")
        if not api_key:
            raise RuntimeError("QIANWEN_API_KEY is not set")

        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": build_semantic_messages(code, language),
                "functions": [build_semantic_function_schema()],
                "function_call": {"name": "describe_code_semantics"},
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        message = payload["choices"][0]["message"]
        function_call = message.get("function_call") or {}
        arguments = function_call.get("arguments")
        if arguments:
            return json.loads(arguments)
        content = message.get("content", "")
        return json.loads(content)

    def _call_deepseek(self, code: str, language: str) -> Dict[str, Any]:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")

        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": build_semantic_messages(code, language),
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
