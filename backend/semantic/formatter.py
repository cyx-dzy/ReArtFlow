"""Utilities to convert diagram dicts into Mermaid strings and AntV G6 JSON.

The *diagram* dict returned by the LLM is expected to have the shape:
{
    "nodes": [{"id": "node1", "label": "中文标签"}, ...],
    "edges": [{"source": "node1", "target": "node2", "label": "依赖"}, ...]
}
Both converters preserve Unicode characters – no escaping is required.
"""

from typing import Dict, List

def to_mermaid(diagram: Dict) -> str:
    """Convert *diagram* dict to a Mermaid flowchart string.

    Example output:
    ```mermaid
    flowchart TD
        node1[中文节点1]
        node2[中文节点2]
        node1 -->|依赖| node2
    ```
    """
    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])
    lines: List[str] = ["flowchart TD"]
    for n in nodes:
        nid = n.get("id")
        label = n.get("label", "")
        lines.append(f"    {nid}[{label}]")
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        lbl = e.get("label", "")
        if lbl:
            lines.append(f"    {src} -->|{lbl}| {tgt}")
        else:
            lines.append(f"    {src} --> {tgt}")
    return "\n".join(lines)

def to_g6(diagram: Dict) -> Dict:
    """Convert *diagram* dict to AntV G6 JSON format.

    Returns a dict compatible with the G6 `graphData` prop, e.g.:
    {
        "nodes": [{"id": "node1", "label": "中文节点1"}],
        "edges": [{"source": "node1", "target": "node2", "label": "依赖"}]
    }
    """
    # Directly map the input structure – ensure required keys exist
    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])
    # Optionally, we could enrich with default styles here.
    return {"nodes": nodes, "edges": edges}
