"""Build and store project diagrams from parser output."""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.semantic import to_g6, to_mermaid

PROJECT_DIAGRAM_STORE: Dict[str, Dict[str, Any]] = {}


SUMMARY_LABELS = {
    "functions": "函数",
    "classes": "类",
    "imports": "导入",
    "calls": "调用",
}


def _safe_id(value: str) -> str:
    cleaned = []
    for char in value:
        cleaned.append(char if char.isalnum() else "_")
    result = "".join(cleaned).strip("_")
    return result or "node"


def _relative_path(file_path: str, root_path: Optional[str]) -> str:
    path = Path(file_path)
    if root_path:
        try:
            return path.relative_to(Path(root_path).resolve()).as_posix()
        except ValueError:
            pass
    return path.name


def build_diagram_from_parsed_files(
    parsed_files: Iterable[Any],
    root_path: Optional[str] = None,
    explanations: Optional[Dict[str, str]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    nodes: List[Dict[str, Any]] = [{"id": "project", "label": "项目", "type": "project"}]
    edges: List[Dict[str, Any]] = []
    explanations = explanations or {}

    for index, parsed in enumerate(parsed_files):
        file_path = getattr(parsed, "path", "") or ""
        rel_path = _relative_path(file_path, root_path)
        file_id = f"file_{index}_{_safe_id(rel_path)}"
        language = getattr(parsed, "language", "")
        ast_summary = getattr(parsed, "ast_summary", {}) or {}
        label = f"{rel_path} ({language})" if language else rel_path
        node: Dict[str, Any] = {"id": file_id, "label": label, "type": "file", "path": rel_path}
        if file_path in explanations:
            node["description"] = explanations[file_path]
        nodes.append(node)
        edges.append({"source": "project", "target": file_id, "label": "包含", "type": "contains"})

        for summary_key, count in ast_summary.items():
            if not count:
                continue
            summary_id = f"{file_id}_{summary_key}"
            summary_label = f"{SUMMARY_LABELS.get(summary_key, summary_key)}: {count}"
            nodes.append({"id": summary_id, "label": summary_label, "type": summary_key, "path": rel_path})
            edges.append({"source": file_id, "target": summary_id, "label": "分析结果", "type": summary_key})

    return {"nodes": nodes, "edges": edges}


def store_project_diagram(
    project_id: str,
    diagram: Dict[str, List[Dict[str, Any]]],
    *,
    status: str = "ready",
    source_type: str = "",
    source_path: str = "",
    errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    record = {
        "project_id": project_id,
        "status": status,
        "source_type": source_type,
        "source_path": source_path,
        "diagram": diagram,
        "errors": errors or [],
    }
    PROJECT_DIAGRAM_STORE[project_id] = record
    return record


def get_project_diagram(project_id: str) -> Optional[Dict[str, Any]]:
    return PROJECT_DIAGRAM_STORE.get(project_id)


def format_diagram_response(record: Dict[str, Any]) -> Dict[str, Any]:
    diagram = record["diagram"]
    return {
        "project_id": record["project_id"],
        "status": record["status"],
        "source_type": record.get("source_type", ""),
        "errors": record.get("errors", []),
        "mermaid": to_mermaid(diagram),
        "g6": to_g6(diagram),
    }
