#!/usr/bin/env python3
"""
verify_llm_api.py – 简易脚本用于验证 LLM（OpenAI / Qianwen）调用能否正常返回
function_call 数据。适合在本地快速排查 API、模型、函数调用配置问题。

使用方法（在项目根目录）：
    $ source .venv/bin/activate
    $ python verify_llm_api.py
"""

import os
import sys
import json
from pathlib import Path

# 确保项目根目录在 import 路径中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入项目内部的 LLM 客户端
from backend.semantic.llm_client import LLMClient


def main() -> None:
    dummy_code = "print('hello world')"
    language = "python"

    # 实例化客户端（会读取 config/llm.yaml 或 env）
    try:
        client = LLMClient()
    except Exception as exc:
        print("❌ 初始化 LLMClient 失败：", exc)
        sys.exit(1)

    # 根据当前 provider 调用底层 API，获取完整响应
    try:
        if client.provider == "openai":
            # OpenAI 1.x SDK
            from openai import OpenAI
            openai_client = OpenAI(api_key=client.openai_key) if client.openai_key else OpenAI()
            if client.api_url:
                openai_client.base_url = client.api_url
            response = openai_client.chat.completions.create(
                model=client.model,
                messages=[{"role": "user", "content": dummy_code}],
                functions=[client.function_schema],
                function_call={"name": "explain_code"},
            )
            # OpenAI response 对象转为 dict 便于打印
            response_dict = json.loads(response.model_dump_json())
        else:
            # Qianwen（使用 requests）
            import requests
            endpoint = client.api_url or "https://api.qianwen.cn/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {client.qianwen_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": client.model,
                "messages": [{"role": "user", "content": dummy_code}],
                "functions": [client.function_schema],
                "function_call": {"name": "explain_code"},
            }
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            response_dict = resp.json()

        # 打印完整原始响应（美化）
        print("\n=== 原始响应 (pretty‑printed) ===")
        print(json.dumps(response_dict, ensure_ascii=False, indent=2))

        # 检查并解析 function_call.arguments
        try:
            if client.provider == "openai":
                func = response.choices[0].message.function_call
            else:
                func = response_dict["choices"][0]["message"].get("function_call")
            if not func:
                raise KeyError("function_call missing")
            args = func.arguments if client.provider == "openai" else func["arguments"]
            parsed = json.loads(args) if isinstance(args, str) else args
            print("\n✅ function_call.arguments 已成功解析：")
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
        except Exception as exc:
            print("\n⚠️ function_call 检查失败：", exc)
            print("如果模型不支持 function calling，请尝试使用 gpt-4o、gpt-4-turbo 等支持该特性的模型，或改用 Qianwen。")
    except Exception as exc:
        print("\n❌ 调用 LLM 接口时抛出异常：", exc)
        if hasattr(exc, "response"):
            try:
                print("响应状态码:", exc.response.status_code)
                print("响应体 (前 500 字符):", exc.response.text[:500])
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
