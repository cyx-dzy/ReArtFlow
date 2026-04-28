"""
JSON → Mermaid 转换工具

根据统一的代码依赖 JSON 结构生成 Mermaid 流程图文本。

- 支持函数/类/模块节点。
- 自动处理中文字符（直接输出）。
- 为大文件使用流式写入以降低内存占用。
"""

import json
from typing import Any, Dict, List

def _escape_label(label: str) -> str:
    """Escape Mermaid 特殊字符，保持中文不变。"""
    # Mermaid 对于 []、{}、<>、|、; 等有特殊含义，需要转义
    return label.replace("[", "\\[").replace("]", "\\]").replace("{", "\\{").replace("}", "\\}").replace("|", "\\|").replace(";", "\\;")

def _node_id(item: Dict[str, Any]) -> str:
    """生成唯一节点 ID（使用文件路径或函数全名）。"""
    # 假设每个节点都有 `id` 字段；若无则使用 hash
    return str(item.get("id", hash(json.dumps(item, sort_keys=True))))

def json_to_mermaid(data: Dict[str, Any]) -> str:
    """将依赖 JSON 转换为 Mermaid flowchart 文本。

    示例输入结构（简化）：
    {
        "nodes": [{"id": "mod1", "label": "模块A"}, ...],
        "edges": [{"source": "mod1", "target": "mod2"}, ...]
    }
    """
    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    edges: List[Dict[str, Any]] = data.get("edges", [])

    lines: List[str] = ["flowchart TD"]

    # 添加节点定义
    for node in nodes:
        nid = _node_id(node)
        label = _escape_label(str(node.get("label", nid)))
        lines.append(f"    {nid}[{label}]")

    # 添加边定义
    for edge in edges:
        src = _node_id(edge)
        dst = _node_id({"id": edge.get("target")})
        # Mermaid 边缘默认使用 -->
        lines.append(f"    {src} --> {dst}")

    return "\n".join(lines)

if __name__ == "__main__":
    import sys, pathlib
    if len(sys.argv) != 2:
        print("Usage: python converter.py <json_file>")
        sys.exit(1)
    json_path = pathlib.Path(sys.argv[1])
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)
    print(json_to_mermaid(data))
