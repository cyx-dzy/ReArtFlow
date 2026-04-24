"""Prompt templates for code explanation.

The LLM receives a list of messages (compatible with both OpenAI and Qianwen chat APIs).
We use a **few‑shot** block (two short examples) followed by a **chain‑of‑thought** instruction,
and finally request a function call named ``explain_code`` that returns JSON with
``explanation`` (Chinese text) and ``diagram`` (structured object).
"""

from typing import List, Dict
import json

# ---------------------------------------------------------------------------
# Example few‑shot entries (very short for demonstration)
# ---------------------------------------------------------------------------
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

# System prompt – brief instruction in Chinese
SYSTEM_PROMPT = (
    "你是一个代码解释专家。请用中文说明给出的代码功能，并以 JSON 对象返回。"
)

# Function‑call schema is defined in llm_client.py; we only need to reference it.

def render_prompt(code: str, language: str) -> List[Dict]:
    """Render the full message list for the LLM.

    Returns a list of dicts compatible with ``openai.ChatCompletion.create`` and
    Qianwen's chat endpoint. The structure is:
        1. System prompt
        2. Few‑shot examples (as user/assistant pairs)
        3. User message with the *actual* code to explain
    """
    messages: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Add few‑shot examples
    for ex in FEW_SHOT_EXAMPLES:
        # User part – provide the code snippet
        messages.append({"role": "user", "content": f"下面是一段 {ex['language']} 代码:\n```\n{ex['code']}\n```"})
        # Assistant part – provide the expected JSON (as string) to guide model
        assistant_json = {
            "explanation": ex["explanation"],
            "diagram": ex["diagram"],
        }
        messages.append({"role": "assistant", "content": json.dumps(assistant_json, ensure_ascii=False)})
    # Final user request with the actual code
    messages.append({"role": "user", "content": f"请解释以下 {language} 代码并返回 JSON：\n```\n{code}\n```"})
    return messages
