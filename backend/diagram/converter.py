"""JSON → Mermaid 转换工具。"""

import json
from typing import Any, Dict, List


def _escape_label(label: str) -> str:
    return (
        label.replace("[", "\\[")
        .replace("]", "\\]")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("|", "\\|")
        .replace(";", "\\;")
    )


def _node_id(item: Dict[str, Any]) -> str:
    return str(item.get("id", hash(json.dumps(item, sort_keys=True))))


def json_to_mermaid(data: Dict[str, Any]) -> str:
    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    edges: List[Dict[str, Any]] = data.get("edges", [])

    lines: List[str] = ["flowchart TD"]

    for node in nodes:
        nid = _node_id(node)
        label = _escape_label(str(node.get("label", nid)))
        lines.append(f"    {nid}[{label}]")

    for edge in edges:
        src = str(edge.get("source", edge.get("id", "")))
        dst = str(edge.get("target", ""))
        if not src or not dst:
            continue
        lines.append(f"    {src} --> {dst}")

    return "\n".join(lines)


if __name__ == "__main__":
    import pathlib
    import sys

    if len(sys.argv) != 2:
        print("Usage: python converter.py <json_file>")
        sys.exit(1)
    json_path = pathlib.Path(sys.argv[1])
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)
    print(json_to_mermaid(data))
