"""Utilities to convert diagram dictionaries into Mermaid and AntV G6 data."""

from __future__ import annotations

from typing import Any, Dict, List


def _escape_mermaid_text(value: Any) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"').replace("|", "\\|").strip()


def _node_id(node_id: Any) -> str:
    value = str(node_id or "node").strip()
    cleaned = "".join(char if char.isalnum() else "_" for char in value)
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"node_{cleaned or 'item'}"
    return cleaned


def _node_label(node: Dict[str, Any]) -> str:
    label_parts = [_escape_mermaid_text(node.get("label"))]
    node_type = _escape_mermaid_text(node.get("type"))
    if node_type and node_type not in label_parts[0]:
        label_parts.append(node_type)
    path = _escape_mermaid_text(node.get("path"))
    if path and "." in path and len(path.split("/")[-1]) <= 24:
        label_parts.append(f"[{path.split('/')[-1]}]")
    return "<br/>".join(part for part in label_parts if part)


def _render_node(node: Dict[str, Any]) -> str:
    node_id = _node_id(node.get("id"))
    label = _node_label(node)
    shape = node.get("shape") or "document"
    if shape == "database":
        return f'    {node_id}[("{label}")]'
    if shape == "api":
        return f'    {node_id}{{"{label}"}}'
    if shape == "ui":
        return f'    {node_id}(["{label}"])'
    if shape == "config":
        return f'    {node_id}["{label}"]'
    if shape == "test":
        return f'    {node_id}>"{label}"]'
    if shape == "service":
        return f'    {node_id}(("{label}"))'
    if shape == "hexagon":
        return f'    {node_id}{{{{"{label}"}}}}'
    return f'    {node_id}["{label}"]'


def to_mermaid(diagram: Dict[str, Any]) -> str:
    """Convert a diagram dict to a Chinese-friendly Mermaid flowchart."""

    nodes = diagram.get("nodes", [])
    edges = diagram.get("edges", [])
    groups = diagram.get("groups", [])
    rendered_node_ids: set[str] = set()
    lines: List[str] = ["flowchart TD"]

    for group in groups:
        group_id = _node_id(group.get("id"))
        group_label = _escape_mermaid_text(group.get("label"))
        lines.append("")
        lines.append(f'  subgraph sub_{group_id}["{group_label}"]')
        for node in nodes:
            if node.get("groupId") == group.get("id") and node.get("id") != group.get("id"):
                lines.append("  " + _render_node(node).strip())
                rendered_node_ids.add(str(node.get("id")))
        lines.append("  end")

    for node in nodes:
        node_id = str(node.get("id"))
        if node_id in rendered_node_ids:
            continue
        lines.append(_render_node(node))

    for edge in edges:
        source = _node_id(edge.get("source") or edge.get("from"))
        target = _node_id(edge.get("target") or edge.get("to"))
        label = _escape_mermaid_text(edge.get("label") or edge.get("type"))
        connector = "-.->" if edge.get("style") == "dashed" else "-->"
        if label:
            lines.append(f'    {source} {connector}|"{label}"| {target}')
        else:
            lines.append(f"    {source} {connector} {target}")

    lines.append("")
    lines.append("    classDef system fill:#1e293b,stroke:#a78bfa,color:#f8fafc")
    lines.append("    classDef module fill:#102a43,stroke:#38bdf8,color:#e0f2fe")
    lines.append("    classDef file fill:#152033,stroke:#5eead4,color:#e5eef8")
    return "\n".join(lines)


def to_g6(diagram: Dict[str, Any]) -> Dict[str, Any]:
    """Return graph data compatible with the current AntV G6 component."""

    return {
        "groups": diagram.get("groups", []),
        "nodes": diagram.get("nodes", []),
        "edges": diagram.get("edges", []),
        "metadata": diagram.get("metadata", {}),
    }
