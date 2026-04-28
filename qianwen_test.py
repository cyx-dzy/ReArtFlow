#!/usr/bin/env python3
"""qianwen_test.py – 演示如何使用阿里云百炼（DashScope）兼容 OpenAI SDK 调用模型 qwen-plus。"""

import os
from openai import OpenAI

# -------------------------------------------------
# 读取 API Key（推荐从环境变量）
# -------------------------------------------------
api_key = os.getenv("DASHSCOPE_API_KEY")
# 若没有在环境变量中设置，可直接在下方填入你的 API Key（仅用于临时测试）
# api_key = "sk-你的千问APIKey"


if not api_key:
    raise RuntimeError(
        "请先在环境变量中设置 DASHSCOPE_API_KEY，或在本文件中直接填写 API Key。"
    )

# -------------------------------------------------
# 创建兼容 OpenAI 的客户端
# -------------------------------------------------
client = OpenAI(
    api_key=api_key,
    # 官方推荐的兼容端点 URL（如需自定义代理，可修改此行）
    base_url="https://dashscope.aliyuncs.com/compatible-mode",
)

# -------------------------------------------------
# 发起一次普通聊天请求（不使用函数调用）
# -------------------------------------------------
try:
    completion = client.chat.completions.create(
        model="openclaw",  # 参考文档的模型列表
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "你是谁？"},
        ],
    )
    print("✅ 模型回复：")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"❌ 错误信息：{e}")
    print("请参考文档：https://help.aliyun.com/model-studio/developer-reference/error-code")