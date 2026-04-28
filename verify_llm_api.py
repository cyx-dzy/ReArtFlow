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

    # 使用统一的 generate_explanation 方法获取解释和图结构
    try:
        result = client.generate_explanation(dummy_code, language)
        # 打印完整原始响应（美化）
        print("\n=== 原始响应 (pretty‑printed) ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        # 已经是解析后的结构，直接展示
        print("\n✅ function_call.arguments 已成功解析：")
        print(json.dumps(result, ensure_ascii=False, indent=2))
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
