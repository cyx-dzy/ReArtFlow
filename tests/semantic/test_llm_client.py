import os
import json
import pytest
from unittest import mock
from backend.semantic.llm_client import LLMClient


def test_openai_success(monkeypatch):
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_MODEL"] = "gpt-4o"
    os.environ["OPENAI_API_KEY"] = "sk-test"
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
    client = LLMClient()
    result = client.generate_explanation('print(hello)', 'Python')
    assert result['explanation'] == '解释'
    assert isinstance(result['diagram'], dict)
