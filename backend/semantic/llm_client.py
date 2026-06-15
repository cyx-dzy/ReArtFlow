"""LLM client with optional dependency fallbacks."""

import json
import logging
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

logger = logging.getLogger(__name__)

QIANWEN_FALLBACK_MODELS: list[str] = []


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(int(os.getenv(name, str(default))), minimum)
    except ValueError:
        return default


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
        self.last_model = self.model
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

    def generate_architecture_graph(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Ask the configured LLM for a GitDiagram-style architecture graph."""

        cache_key = {
            "provider": self.provider,
            "model": self.model,
            "task": "architecture_graph",
            "snapshot": snapshot,
        }
        cached = self.cache.get(cache_key)
        if cached is not None:
            return self._normalize_architecture_graph(cached)

        messages = self._build_architecture_messages(snapshot)
        if self.provider == "openai":
            result = self._call_openai_json(messages)
        elif self.provider == "qianwen":
            result = self._call_qianwen_json(messages)
        elif self.provider == "deepseek":
            result = self._call_deepseek_json(messages)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        result = self._normalize_architecture_graph(result)
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

    def _normalize_architecture_graph(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"groups": [], "nodes": [], "edges": []}
        for key in ("groups", "nodes", "edges"):
            if not isinstance(result.get(key), list):
                result[key] = []
        if not isinstance(result.get("summary"), str):
            result["summary"] = ""
        if not isinstance(result.get("title"), str):
            result["title"] = "项目总览"
        return result

    def _build_architecture_messages(self, snapshot: Dict[str, Any]) -> list[Dict[str, str]]:
        schema_hint = {
            "title": "中文项目标题",
            "summary": "面向非技术人员的项目结构说明",
            "groups": [
                {"id": "module_id", "label": "模块中文名", "description": "模块职责", "color": "#38bdf8"}
            ],
            "nodes": [
                {
                    "id": "stable_node_id",
                    "label": "节点名称",
                    "type": "接口层/数据层/界面层/业务逻辑/配置/测试",
                    "shape": "database/api/ui/config/test/service/document/box/hexagon",
                    "groupId": "module_id",
                    "path": "必须来自输入 files.path，模块节点可为空",
                    "description": "非技术人员能理解的一句话职责",
                }
            ],
            "edges": [
                {
                    "source": "节点 id",
                    "target": "节点 id",
                    "type": "routes_to/renders/reads_writes/configures/tests/imports/calls/depends_on/serves/stores",
                    "label": "中文关系名",
                    "description": "为什么存在这条关系",
                }
            ],
        }
        return [
            {
                "role": "system",
                "content": (
                    "你是一个代码架构图谱设计助手。你的目标是帮助非技术人员理解跨语言项目结构。"
                    "请优先按业务/技术模块聚类文件，用不同节点形状表达不同功能，"
                    "并用多种关系类型表达文件或模块之间的真实关系。"
                    "只能引用输入 files.path 中存在的文件路径，不要编造路径。"
                    "只返回 JSON，不要返回 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "output_schema": schema_hint,
                        "project_snapshot": snapshot,
                        "requirements": [
                            "把相同模块或相同职责的文件放在一起",
                            "数据库/模型/Schema 用 database 形状",
                            "接口/路由用 api 形状",
                            "页面/组件用 ui 形状",
                            "配置和测试分别用 config/test 形状",
                            "关系不要只有调用，优先识别路由到、渲染、读写数据、配置、测试、依赖、服务于等关系",
                            "节点和关系说明必须用简洁中文，适合非技术人员阅读",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ]

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

        payload = self._post_qianwen_with_fallback(
            api_key,
            {
                "messages": build_semantic_messages(code, language),
                "functions": [build_semantic_function_schema()],
                "function_call": {"name": "describe_code_semantics"},
            },
            timeout=30,
        )
        message = payload["choices"][0]["message"]
        function_call = message.get("function_call") or {}
        arguments = function_call.get("arguments")
        if arguments:
            return json.loads(arguments)
        content = message.get("content", "")
        return json.loads(content)

    def _call_openai_json(self, messages: list[Dict[str, str]]) -> Dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)

    def _call_qianwen_json(self, messages: list[Dict[str, str]]) -> Dict[str, Any]:
        api_key = os.getenv("QIANWEN_API_KEY")
        if not api_key:
            raise RuntimeError("QIANWEN_API_KEY is not set")

        payload = self._post_qianwen_with_fallback(
            api_key,
            {
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=_env_int("LLM_ARCHITECTURE_TIMEOUT", 25),
        )
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)

    def _qianwen_model_candidates(self) -> list[str]:
        configured = os.getenv("QIANWEN_MODEL_FALLBACKS")
        fallback_models = (
            [item.strip() for item in configured.split(",") if item.strip()]
            if configured
            else QIANWEN_FALLBACK_MODELS
        )
        candidates = [self.model, *fallback_models]
        deduped: list[str] = []
        for model in candidates:
            if model and model not in deduped:
                deduped.append(model)
        return deduped

    def _post_qianwen_with_fallback(
        self,
        api_key: str,
        request_payload: Dict[str, Any],
        *,
        timeout: int,
    ) -> Dict[str, Any]:
        last_error: Exception | None = None
        candidates = self._qianwen_model_candidates()
        for index, model in enumerate(candidates, start=1):
            payload = {"model": model, **request_payload}
            try:
                logger.info("Calling Qianwen model %s/%s: %s", index, len(candidates), model)
                response = requests.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                self.last_model = model
                return response.json()
            except Exception as exc:
                last_error = exc
                logger.warning("Qianwen model %s failed: %s", model, exc)
        raise RuntimeError(f"All Qianwen models failed or timed out: {last_error}") from last_error

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

    def _call_deepseek_json(self, messages: list[Dict[str, str]]) -> Dict[str, Any]:
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
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
