import os
import json
import pytest
from unittest import mock
from backend.semantic.llm_client import LLMClient


def test_openai_success(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    dummy_response = {
        "choices": [{
            "message": {
                "function_call": {
                    "arguments": json.dumps({"explanation": "解释", "diagram": {"nodes": [], "edges": []}})
                }
            }
        }]
    }
    mock_chat = mock.Mock(return_value=dummy_response)
    monkeypatch.setattr('backend.semantic.llm_client.openai.ChatCompletion.create', mock_chat)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.get", lambda self, payload: None)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.set", lambda self, payload, value, ttl=86400: None)
    client = LLMClient()
    result = client.generate_explanation('print(hello)', 'Python')
    assert result['explanation'] == '解释'
    assert isinstance(result['diagram'], dict)


def test_deepseek_success(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    dummy_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"explanation": "DeepSeek解释", "diagram": {"nodes": [], "edges": []}})
                }
            }
        ]
    }
    mock_post = mock.Mock()
    mock_response = mock.Mock()
    mock_response.json.return_value = dummy_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    monkeypatch.setattr("backend.semantic.llm_client.requests.post", mock_post)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.get", lambda self, payload: None)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.set", lambda self, payload, value, ttl=86400: None)

    client = LLMClient()
    result = client.generate_explanation("print('hello')", "Python")

    assert client.model == "deepseek-chat"
    assert result["explanation"] == "DeepSeek解释"
    assert isinstance(result["diagram"], dict)
    request_json = mock_post.call_args.kwargs["json"]
    assert request_json["response_format"] == {"type": "json_object"}


def test_qianwen_success(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qianwen")
    monkeypatch.setenv("QIANWEN_API_KEY", "sk-test")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    dummy_response = {
        "choices": [
            {
                "message": {
                    "function_call": {
                        "arguments": json.dumps({"explanation": "千问解释", "diagram": {"nodes": [], "edges": []}})
                    }
                }
            }
        ]
    }
    mock_post = mock.Mock()
    mock_response = mock.Mock()
    mock_response.json.return_value = dummy_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    monkeypatch.setattr("backend.semantic.llm_client.requests.post", mock_post)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.get", lambda self, payload: None)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.set", lambda self, payload, value, ttl=86400: None)

    client = LLMClient()
    result = client.generate_explanation("def hello():\n    return 'world'\n", "Python")

    assert client.model == "qwen-plus"
    assert result["explanation"] == "千问解释"
    request_json = mock_post.call_args.kwargs["json"]
    assert request_json["model"] == "qwen-plus"
    assert mock_post.call_args.args[0] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def test_qianwen_falls_back_to_next_model(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qianwen")
    monkeypatch.setenv("LLM_MODEL", "bad-current-model")
    monkeypatch.setenv("QIANWEN_API_KEY", "sk-test")
    monkeypatch.setenv("QIANWEN_MODEL_FALLBACKS", "qwen3.7-plus,qwen-math-turbo")

    success_response = mock.Mock()
    success_response.raise_for_status.return_value = None
    success_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "function_call": {
                        "arguments": json.dumps({"explanation": "fallback ok", "diagram": {"nodes": [], "edges": []}})
                    }
                }
            }
        ]
    }
    mock_post = mock.Mock(side_effect=[TimeoutError("timeout"), success_response])
    monkeypatch.setattr("backend.semantic.llm_client.requests.post", mock_post)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.get", lambda self, payload: None)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.set", lambda self, payload, value, ttl=86400: None)

    client = LLMClient()
    result = client.generate_explanation("def hello():\n    return 'world'\n", "Python")

    called_models = [call.kwargs["json"]["model"] for call in mock_post.call_args_list]
    assert called_models == ["bad-current-model", "qwen3.7-plus"]
    assert client.last_model == "qwen3.7-plus"
    assert result["explanation"] == "fallback ok"


def test_qianwen_raises_after_all_fallback_models_fail(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qianwen")
    monkeypatch.setenv("LLM_MODEL", "bad-current-model")
    monkeypatch.setenv("QIANWEN_API_KEY", "sk-test")
    monkeypatch.setenv("QIANWEN_MODEL_FALLBACKS", "qwen3.7-plus,qwen-math-turbo")
    mock_post = mock.Mock(side_effect=TimeoutError("timeout"))
    monkeypatch.setattr("backend.semantic.llm_client.requests.post", mock_post)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.get", lambda self, payload: None)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.set", lambda self, payload, value, ttl=86400: None)

    client = LLMClient()
    with pytest.raises(RuntimeError, match="All Qianwen models failed"):
        client.generate_explanation("def hello():\n    return 'world'\n", "Python")

    called_models = [call.kwargs["json"]["model"] for call in mock_post.call_args_list]
    assert called_models == ["bad-current-model", "qwen3.7-plus", "qwen-math-turbo"]


def test_qianwen_architecture_graph_parses_json(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qianwen")
    monkeypatch.setenv("QIANWEN_API_KEY", "sk-test")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    dummy_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "title": "示例项目",
                            "summary": "前端调用后端接口。",
                            "groups": [{"id": "frontend", "label": "前端模块"}],
                            "nodes": [{"id": "app", "label": "App", "shape": "ui", "path": "frontend/App.vue"}],
                            "edges": [{"source": "app", "target": "api", "type": "routes_to"}],
                        }
                    )
                }
            }
        ]
    }
    mock_post = mock.Mock()
    mock_response = mock.Mock()
    mock_response.json.return_value = dummy_response
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    monkeypatch.setattr("backend.semantic.llm_client.requests.post", mock_post)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.get", lambda self, payload: None)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.set", lambda self, payload, value, ttl=86400: None)

    client = LLMClient()
    result = client.generate_architecture_graph({"files": [{"path": "frontend/App.vue"}]})

    assert result["title"] == "示例项目"
    assert result["groups"][0]["label"] == "前端模块"
    assert result["nodes"][0]["shape"] == "ui"
    request_json = mock_post.call_args.kwargs["json"]
    assert request_json["response_format"] == {"type": "json_object"}


def test_qianwen_architecture_graph_uses_configured_timeout(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qianwen")
    monkeypatch.setenv("QIANWEN_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_ARCHITECTURE_TIMEOUT", "7")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    dummy_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"groups": [], "nodes": [], "edges": []})
                }
            }
        ]
    }
    mock_response = mock.Mock()
    mock_response.json.return_value = dummy_response
    mock_response.raise_for_status.return_value = None
    mock_post = mock.Mock(return_value=mock_response)
    monkeypatch.setattr("backend.semantic.llm_client.requests.post", mock_post)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.get", lambda self, payload: None)
    monkeypatch.setattr("backend.semantic.llm_client.SemanticCache.set", lambda self, payload, value, ttl=86400: None)

    client = LLMClient()
    client.generate_architecture_graph({"files": []})

    assert mock_post.call_args.kwargs["timeout"] == 7


@pytest.mark.integration
def test_deepseek_real_api(monkeypatch):
    if os.getenv("RUN_DEEPSEEK_INTEGRATION") != "1":
        pytest.skip("Set RUN_DEEPSEEK_INTEGRATION=1 to run the real DeepSeek API test")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY is not set")

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    client = LLMClient()
    result = client.generate_explanation("def hello():\n    return 'world'\n", "Python")

    assert isinstance(result.get("explanation"), str)
    assert isinstance(result.get("diagram"), dict)
    assert isinstance(result["diagram"].get("nodes"), list)


@pytest.mark.integration
def test_qianwen_real_api(monkeypatch):
    if os.getenv("RUN_QIANWEN_INTEGRATION") != "1":
        pytest.skip("Set RUN_QIANWEN_INTEGRATION=1 to run the real Qianwen API test")
    api_key = os.getenv("QIANWEN_API_KEY")
    if not api_key:
        pytest.skip("QIANWEN_API_KEY is not set")

    monkeypatch.setenv("LLM_PROVIDER", "qianwen")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    client = LLMClient()
    result = client.generate_explanation("def hello():\n    return 'world'\n", "Python")

    assert isinstance(result.get("explanation"), str)
    assert isinstance(result.get("diagram"), dict)
    assert isinstance(result["diagram"].get("nodes"), list)
