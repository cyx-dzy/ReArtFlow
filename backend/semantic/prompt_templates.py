"""Prompt templates for code explanation."""

import json
from typing import Dict, List

FEW_SHOT_EXAMPLES = [
    {
        "code": "def add(a, b):\n    return a + b",
        "language": "Python",
        "explanation": "该函数接受两个数字 a 和 b，返回它们的和。",
        "diagram": {"nodes": [{"id": "add", "label": "add(a, b)"}], "edges": []},
    },
    {
        "code": "function greet(name) {\n  console.log('Hello, ' + name);\n}",
        "language": "JavaScript",
        "explanation": "greet 函数接受一个名字，在控制台输出欢迎语。",
        "diagram": {"nodes": [{"id": "greet", "label": "greet(name)"}], "edges": []},
    },
]

SYSTEM_PROMPT = "你是一个代码解释专家。请用中文说明给出的代码功能，并以 JSON 对象返回。"


def render_prompt(code: str, language: str) -> List[Dict]:
    return build_semantic_messages(code, language)


def build_semantic_messages(code: str, language: str) -> List[Dict]:
    messages: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": f"下面是一段 {example['language']} 代码:\n```\n{example['code']}\n```"})
        assistant_json = {
            "explanation": example["explanation"],
            "diagram": example["diagram"],
        }
        messages.append({"role": "assistant", "content": json.dumps(assistant_json, ensure_ascii=False)})
    messages.append({"role": "user", "content": f"请解释以下 {language} 代码并返回 JSON：\n```\n{code}\n```"})
    return messages


def build_semantic_function_schema() -> Dict:
    return {
        "name": "describe_code_semantics",
        "description": "用中文解释代码，并返回图谱结构。",
        "parameters": {
            "type": "object",
            "properties": {
                "explanation": {"type": "string", "description": "中文解释"},
                "diagram": {
                    "type": "object",
                    "properties": {
                        "nodes": {"type": "array", "items": {"type": "object"}},
                        "edges": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["nodes", "edges"],
                },
            },
            "required": ["explanation", "diagram"],
        },
    }
