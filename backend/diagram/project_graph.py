"""Build and store Chinese architecture diagrams from parser and AI output."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from backend.semantic import to_g6, to_mermaid

PROJECT_DIAGRAM_STORE: Dict[str, Dict[str, Any]] = {}

MAX_GRAPH_GROUPS = 9
MAX_GRAPH_NODES = 42
MAX_GRAPH_EDGES = 72
MAX_FILES_PER_GROUP = 6
MAX_AI_NODES = 42
MAX_AI_EDGES = 72

SUMMARY_LABELS = {
    "functions": "函数",
    "classes": "类",
    "imports": "导入",
    "calls": "调用",
}

GROUP_PALETTES = [
    "#38bdf8",
    "#5eead4",
    "#a78bfa",
    "#fbbf24",
    "#fb7185",
    "#60a5fa",
    "#34d399",
    "#f472b6",
    "#c084fc",
]

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
}

PROJECT_FILE_EXTENSIONS = set(EXTENSION_LANGUAGE_MAP)
IGNORED_FILE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".woff",
    ".woff2",
    ".ttf",
}
IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".vite",
    "coverage",
}

ALLOWED_SHAPES = {"hexagon", "box", "document", "database", "api", "ui", "config", "test", "service"}
RELATION_LABELS = {
    "contains": "包含",
    "routes_to": "路由到",
    "renders": "渲染",
    "reads_writes": "读写数据",
    "configures": "配置",
    "tests": "测试",
    "imports": "导入",
    "calls": "调用",
    "depends_on": "依赖",
    "explains": "说明",
    "serves": "服务于",
    "stores": "存储",
}


def _safe_id(value: str) -> str:
    cleaned = []
    for char in value.lower():
        cleaned.append(char if char.isalnum() else "_")
    result = "".join(cleaned).strip("_")
    if not result or not result[0].isalpha():
        result = f"node_{result or 'item'}"
    return result[:80]


def _relative_path(file_path: str, root_path: Optional[str]) -> str:
    path = Path(file_path)
    if root_path:
        try:
            return path.resolve().relative_to(Path(root_path).resolve()).as_posix()
        except ValueError:
            pass
    return path.name


def _top_level(rel_path: str) -> str:
    parts = [part for part in rel_path.split("/") if part]
    if len(parts) <= 1:
        return "根目录"
    return parts[0]


def _signal(parsed: Any) -> int:
    ast_summary = getattr(parsed, "ast_summary", {}) or {}
    return sum(int(value or 0) for value in ast_summary.values())


def _summary_text(parsed_files: Iterable[Any]) -> str:
    totals: Dict[str, int] = defaultdict(int)
    for parsed in parsed_files:
        for key, value in (getattr(parsed, "ast_summary", {}) or {}).items():
            totals[key] += int(value or 0)
    parts = [f"{SUMMARY_LABELS.get(key, key)} {value}" for key, value in totals.items() if value]
    return "，".join(parts) if parts else "源码结构入口"


def _file_description(parsed: Any, explanation: Optional[str]) -> str:
    if explanation:
        return explanation[:240]
    summary = getattr(parsed, "ast_summary", {}) or {}
    details = [f"{SUMMARY_LABELS.get(key, key)} {value}" for key, value in summary.items() if value]
    return "，".join(details) if details else "项目主体源码文件"


def _classify_file(rel_path: str, language: str) -> Tuple[str, str, str]:
    lower = rel_path.lower()
    name = Path(rel_path).name.lower()
    if any(part in lower for part in ("db", "database", "model", "schema", "migration", "sql")):
        return "数据层", "database", "保存或描述业务数据"
    if any(part in lower for part in ("api", "route", "controller", "endpoint", "handler")):
        return "接口层", "api", "接收请求并暴露业务能力"
    if any(part in lower for part in ("view", "page", "component", "frontend", "ui")) or name.endswith((".vue", ".tsx", ".jsx")):
        return "界面层", "ui", "展示界面并连接用户操作"
    if any(part in lower for part in ("config", "settings", ".env", "vite", "docker", "compose", "package.json")):
        return "配置", "config", "定义运行、构建或部署配置"
    if any(part in lower for part in ("test", "spec", "__tests__")):
        return "测试", "test", "验证系统行为"
    if language in {"Markdown", "JSON", "YAML", "TOML"}:
        return "说明/配置", "config", "说明项目或提供配置数据"
    return "业务逻辑", "service", "承载核心业务流程"


def _is_project_file(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    if any(part in IGNORED_DIRECTORIES for part in relative.parts):
        return False
    suffix = path.suffix.lower()
    if suffix in IGNORED_FILE_EXTENSIONS:
        return False
    return suffix in PROJECT_FILE_EXTENSIONS


def build_architecture_snapshot(
    parsed_files: Iterable[Any],
    root_path: Optional[str] = None,
    explanations: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create a compact repo snapshot that is safe to send to the LLM."""

    explanations = explanations or {}
    files: List[Dict[str, Any]] = []
    for parsed in parsed_files:
        file_path = getattr(parsed, "path", "") or ""
        rel_path = _relative_path(file_path, root_path)
        language = getattr(parsed, "language", "") or EXTENSION_LANGUAGE_MAP.get(Path(rel_path).suffix.lower(), "")
        role, shape, role_hint = _classify_file(rel_path, language)
        files.append(
            {
                "path": rel_path,
                "name": Path(rel_path).name,
                "module": _top_level(rel_path),
                "language": language,
                "role": role,
                "shape": shape,
                "role_hint": role_hint,
                "ast_summary": getattr(parsed, "ast_summary", {}) or {},
                "explanation": (explanations.get(file_path) or "")[:220],
            }
        )
    files.sort(key=lambda item: (-sum(int(v or 0) for v in item["ast_summary"].values()), item["path"]))
    return {
        "goal": "为非技术人员解释跨语言项目结构",
        "files": files[:80],
        "relation_types": RELATION_LABELS,
        "shape_types": {
            "database": "数据库、模型、Schema、迁移脚本",
            "api": "接口、路由、Controller、Handler",
            "ui": "页面、组件、前端入口",
            "config": "配置、构建、部署、说明",
            "test": "测试与验证",
            "service": "核心业务逻辑",
            "document": "普通源码文件",
            "box": "模块/子系统",
            "hexagon": "项目总览",
        },
    }


def _rank_groups(parsed_list: Sequence[Any], root_path: Optional[str]) -> List[Tuple[str, List[Any]]]:
    groups_by_name: Dict[str, List[Any]] = defaultdict(list)
    for parsed in parsed_list:
        rel_path = _relative_path(getattr(parsed, "path", "") or "", root_path)
        groups_by_name[_top_level(rel_path)].append(parsed)
    return sorted(groups_by_name.items(), key=lambda item: (-sum(_signal(parsed) for parsed in item[1]), item[0]))[
        :MAX_GRAPH_GROUPS
    ]


def _static_edges(nodes: List[Dict[str, Any]], group_ids: Set[str]) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    file_nodes = [node for node in nodes if node.get("path") and node.get("id") not in group_ids]
    api_nodes = [node for node in file_nodes if node.get("shape") == "api"]
    ui_nodes = [node for node in file_nodes if node.get("shape") == "ui"]
    data_nodes = [node for node in file_nodes if node.get("shape") == "database"]
    config_nodes = [node for node in file_nodes if node.get("shape") == "config"]
    test_nodes = [node for node in file_nodes if node.get("shape") == "test"]
    service_nodes = [node for node in file_nodes if node.get("shape") == "service"]

    def add(source: str, target: str, relation_type: str, style: str = "solid") -> None:
        if source == target or len(edges) >= MAX_GRAPH_EDGES:
            return
        edge = {
            "source": source,
            "target": target,
            "type": relation_type,
            "label": RELATION_LABELS.get(relation_type, relation_type),
            "style": style,
        }
        if edge not in edges:
            edges.append(edge)

    for node in nodes:
        if node["id"] in group_ids:
            add("project", node["id"], "contains")
        elif node.get("groupId"):
            add(node["groupId"], node["id"], "contains")

    for ui_node in ui_nodes[:8]:
        for api_node in api_nodes[:3]:
            add(ui_node["id"], api_node["id"], "routes_to")
    for api_node in api_nodes[:8]:
        targets = service_nodes[:2] or data_nodes[:2]
        for target in targets:
            add(api_node["id"], target["id"], "calls")
    for service_node in service_nodes[:10]:
        for data_node in data_nodes[:2]:
            add(service_node["id"], data_node["id"], "reads_writes")
    for config_node in config_nodes[:6]:
        for target in (api_nodes or service_nodes or ui_nodes)[:2]:
            add(config_node["id"], target["id"], "configures", style="dashed")
    for test_node in test_nodes[:6]:
        for target in (service_nodes or api_nodes or file_nodes)[:2]:
            add(test_node["id"], target["id"], "tests", style="dashed")

    return edges[:MAX_GRAPH_EDGES]


def _build_static_diagram(
    parsed_list: Sequence[Any],
    root_path: Optional[str],
    explanations: Dict[str, str],
) -> Dict[str, Any]:
    ranked_groups = _rank_groups(parsed_list, root_path)
    group_meta: List[Dict[str, Any]] = []
    nodes: List[Dict[str, Any]] = [
        {
            "id": "project",
            "label": "项目总览",
            "type": "系统",
            "description": f"包含 {len(parsed_list)} 个主体源码文件，按模块、职责和关系生成中文结构图。",
            "shape": "hexagon",
            "color": "#a78bfa",
        }
    ]

    for group_index, (group_name, group_files) in enumerate(ranked_groups):
        if len(nodes) >= MAX_GRAPH_NODES:
            break
        group_id = f"group_{_safe_id(group_name)}"
        group_label = f"{group_name} 模块"
        group_color = GROUP_PALETTES[group_index % len(GROUP_PALETTES)]
        group_description = _summary_text(group_files)
        group_meta.append({"id": group_id, "label": group_label, "description": group_description, "color": group_color})
        nodes.append(
            {
                "id": group_id,
                "label": group_label,
                "type": "模块",
                "description": group_description,
                "groupId": group_id,
                "path": "" if group_name == "根目录" else f"{group_name}/",
                "shape": "box",
                "color": group_color,
            }
        )

        ranked_files = sorted(group_files, key=lambda parsed: (-_signal(parsed), getattr(parsed, "path", "")))
        for parsed in ranked_files[:MAX_FILES_PER_GROUP]:
            if len(nodes) >= MAX_GRAPH_NODES:
                break
            file_path = getattr(parsed, "path", "") or ""
            rel_path = _relative_path(file_path, root_path)
            language = getattr(parsed, "language", "") or "源码"
            role, shape, role_hint = _classify_file(rel_path, language)
            nodes.append(
                {
                    "id": f"file_{group_index}_{_safe_id(rel_path)}",
                    "label": Path(rel_path).name,
                    "type": role,
                    "language": language,
                    "description": _file_description(parsed, explanations.get(file_path)) or role_hint,
                    "groupId": group_id,
                    "path": rel_path,
                    "shape": shape,
                    "color": group_color,
                }
            )

    group_ids = {group["id"] for group in group_meta}
    edges = _static_edges(nodes, group_ids)
    return {
        "groups": group_meta,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "source": "static",
            "relationship_mode": "heuristic",
            "audience": "non-technical",
        },
    }


def _normalize_ai_diagram(
    ai_diagram: Dict[str, Any],
    fallback: Dict[str, Any],
    allowed_paths: Set[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(ai_diagram, dict):
        return None

    fallback_by_path = {node.get("path"): node for node in fallback.get("nodes", []) if node.get("path")}
    fallback_by_id = {node.get("id"): node for node in fallback.get("nodes", [])}

    groups: List[Dict[str, Any]] = []
    group_ids: Set[str] = set()
    for index, group in enumerate(ai_diagram.get("groups") or fallback.get("groups", [])):
        if not isinstance(group, dict) or len(groups) >= MAX_GRAPH_GROUPS:
            continue
        group_id = _safe_id(str(group.get("id") or group.get("label") or f"group_{index}"))
        color = str(group.get("color") or GROUP_PALETTES[index % len(GROUP_PALETTES)])
        groups.append(
            {
                "id": group_id,
                "label": str(group.get("label") or f"模块 {index + 1}")[:40],
                "description": str(group.get("description") or "")[:240],
                "color": color,
            }
        )
        group_ids.add(group_id)

    if not groups:
        groups = fallback.get("groups", [])[:MAX_GRAPH_GROUPS]
        group_ids = {group["id"] for group in groups}

    nodes: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    def add_node(node: Dict[str, Any], index: int) -> None:
        node_id = _safe_id(str(node.get("id") or node.get("path") or node.get("label") or f"node_{index}"))
        if node_id in seen_ids or len(nodes) >= MAX_AI_NODES:
            return
        path = str(node.get("path") or "")
        if path and path not in allowed_paths and not path.endswith("/"):
            return
        fallback_node = fallback_by_path.get(path) or fallback_by_id.get(node_id) or {}
        group_id = _safe_id(str(node.get("groupId") or fallback_node.get("groupId") or ""))
        if group_id and group_id not in group_ids:
            group_id = ""
        shape = str(node.get("shape") or fallback_node.get("shape") or "document")
        if shape not in ALLOWED_SHAPES:
            shape = "document"
        color = str(node.get("color") or fallback_node.get("color") or "")
        nodes.append(
            {
                "id": node_id,
                "label": str(node.get("label") or fallback_node.get("label") or path or node_id)[:48],
                "type": str(node.get("type") or fallback_node.get("type") or "文件")[:32],
                "language": str(node.get("language") or fallback_node.get("language") or "")[:32],
                "description": str(node.get("description") or fallback_node.get("description") or "")[:260],
                "groupId": group_id,
                "path": path,
                "shape": shape,
                "color": color,
            }
        )
        seen_ids.add(node_id)

    add_node(
        {
            "id": "project",
            "label": ai_diagram.get("title") or "项目总览",
            "type": "系统",
            "description": ai_diagram.get("summary") or fallback_by_id.get("project", {}).get("description", ""),
            "shape": "hexagon",
            "color": "#a78bfa",
        },
        0,
    )

    for group in groups:
        add_node(
            {
                "id": group["id"],
                "label": group["label"],
                "type": "模块",
                "description": group.get("description", ""),
                "groupId": group["id"],
                "path": "",
                "shape": "box",
                "color": group.get("color", ""),
            },
            len(nodes),
        )

    for index, node in enumerate(ai_diagram.get("nodes") or [], start=len(nodes)):
        if isinstance(node, dict):
            add_node(node, index)

    if len(nodes) < 2:
        return None

    valid_ids = {node["id"] for node in nodes}
    edges: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str, str]] = set()

    def add_edge(source: str, target: str, relation_type: str, label: str = "", description: str = "") -> None:
        if source not in valid_ids or target not in valid_ids or source == target or len(edges) >= MAX_AI_EDGES:
            return
        key = (source, target, relation_type)
        if key in seen_edges:
            return
        edges.append(
            {
                "source": source,
                "target": target,
                "type": relation_type,
                "label": label or RELATION_LABELS.get(relation_type, relation_type),
                "description": description[:180],
                "style": "dashed" if relation_type in {"configures", "tests", "explains"} else "solid",
            }
        )
        seen_edges.add(key)

    for group_id in sorted(group_ids):
        add_edge("project", group_id, "contains")
    for node in nodes:
        group_id = node.get("groupId")
        if group_id and node["id"] != group_id:
            add_edge(group_id, node["id"], "contains")

    for edge in ai_diagram.get("edges") or []:
        if not isinstance(edge, dict) or len(edges) >= MAX_AI_EDGES:
            continue
        source = _safe_id(str(edge.get("source") or edge.get("from") or ""))
        target = _safe_id(str(edge.get("target") or edge.get("to") or ""))
        if source not in valid_ids or target not in valid_ids or source == target:
            continue
        relation_type = str(edge.get("type") or "depends_on")
        label = str(edge.get("label") or RELATION_LABELS.get(relation_type, relation_type))[:32]
        add_edge(source, target, relation_type, label=label, description=str(edge.get("description") or ""))

    if not edges:
        edges = _static_edges(nodes, group_ids)

    return {
        "groups": groups,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "source": "ai",
            "relationship_mode": "qianwen" if ai_diagram else "static",
            "audience": "non-technical",
            "summary": str(ai_diagram.get("summary") or "")[:500],
        },
    }


def build_diagram_from_parsed_files(
    parsed_files: Iterable[Any],
    root_path: Optional[str] = None,
    explanations: Optional[Dict[str, str]] = None,
    ai_diagram: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a GitDiagram-inspired architecture overview with Chinese labels."""

    parsed_list = list(parsed_files)
    explanations = explanations or {}
    fallback = _build_static_diagram(parsed_list, root_path, explanations)
    if ai_diagram:
        allowed_paths = {
            _relative_path(getattr(parsed, "path", "") or "", root_path)
            for parsed in parsed_list
            if getattr(parsed, "path", "")
        }
        normalized = _normalize_ai_diagram(ai_diagram, fallback, allowed_paths)
        if normalized:
            return normalized
    return fallback


def store_project_diagram(
    project_id: str,
    diagram: Dict[str, Any],
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


def list_project_files(record: Dict[str, Any], limit: int = 1000) -> List[Dict[str, Any]]:
    root = Path(record.get("source_path", "")).resolve()
    if not root.is_dir():
        return []

    files: List[Dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if len(files) >= limit:
            break
        if not _is_project_file(path, root):
            continue
        rel_path = path.relative_to(root).as_posix()
        stat = path.stat()
        files.append(
            {
                "path": rel_path,
                "name": path.name,
                "size": stat.st_size,
                "language": EXTENSION_LANGUAGE_MAP.get(path.suffix.lower(), ""),
            }
        )
    return files


def read_project_file(record: Dict[str, Any], relative_path: str, max_bytes: int = 200_000) -> Dict[str, Any]:
    root = Path(record.get("source_path", "")).resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("File path is outside the project root")
    if not _is_project_file(target, root):
        raise FileNotFoundError(relative_path)
    content = target.read_bytes()[:max_bytes].decode("utf-8", errors="replace")
    return {
        "path": target.relative_to(root).as_posix(),
        "content": content,
        "truncated": target.stat().st_size > max_bytes,
        "language": EXTENSION_LANGUAGE_MAP.get(target.suffix.lower(), ""),
    }
