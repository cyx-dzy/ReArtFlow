"""Build and store Chinese architecture diagrams from parser and AI output."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from backend.semantic import to_g6, to_mermaid

PROJECT_DIAGRAM_STORE: Dict[str, Dict[str, Any]] = {}

MAX_GRAPH_GROUPS = 9
MAX_GRAPH_FILE_NODES = int(os.getenv("DIAGRAM_MAX_FILE_NODES", "14"))
MAX_FILES_PER_GROUP = int(os.getenv("DIAGRAM_MAX_FILES_PER_GROUP", "3"))
MAX_GRAPH_EDGES = int(os.getenv("DIAGRAM_MAX_EDGES", "14"))
MAX_AI_FILE_NODES = int(os.getenv("DIAGRAM_MAX_AI_FILE_NODES", str(MAX_GRAPH_FILE_NODES)))
MAX_AI_EDGES = int(os.getenv("DIAGRAM_MAX_AI_EDGES", str(MAX_GRAPH_EDGES)))


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(int(os.getenv(name, str(default))), minimum)
    except ValueError:
        return default

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
    "routes_to": "路由到",
    "renders": "渲染",
    "reads_writes": "读写数据",
    "configures": "配置",
    "tests": "测试",
    "imports": "导入",
    "calls": "调用",
    "depends_on": "依赖",
    "related": "关联",
    "module_relates": "模块关联",
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


def _module_label(module: str) -> str:
    lower = module.lower()
    labels = {
        "frontend": "前端交互层",
        "backend": "后端解析服务",
        "tests": "测试与验证",
        "test": "测试与验证",
        "docs": "文档说明",
        "doc": "文档说明",
        "config": "配置与构建",
        "根目录": "配置与构建",
    }
    if lower in labels:
        return labels[lower]
    return f"{module} 模块"


def _signal(parsed: Any) -> int:
    ast_summary = getattr(parsed, "ast_summary", {}) or {}
    return sum(int(value or 0) for value in ast_summary.values())


def _importance_score(parsed: Any, root_path: Optional[str] = None) -> int:
    rel_path = _relative_path(getattr(parsed, "path", "") or "", root_path).lower()
    name = Path(rel_path).name
    score = _signal(parsed)
    if name in {"app.py", "main.py", "main.ts", "app.vue", "vite.config.ts", "package.json"}:
        score += 80
    if any(part in rel_path for part in ("api/", "routes/", "input.py", "diagram.py", "project_graph.py")):
        score += 60
    if any(part in rel_path for part in ("semantic/", "llm", "parser/", "processor", "handler")):
        score += 45
    if any(part in rel_path for part in ("frontend/src", "components/", "app.vue")):
        score += 40
    if any(part in rel_path for part in ("test", "benchmark", "docs/", "extracted_src")):
        score -= 120
    return score


def _is_support_file(parsed: Any, root_path: Optional[str] = None) -> bool:
    rel_path = _relative_path(getattr(parsed, "path", "") or "", root_path).lower()
    name = Path(rel_path).name
    return (
        name.endswith(".d.ts")
        or any(part in rel_path for part in ("tests/", "test_", "_test.", "benchmark/", "docs/", "extracted_src/"))
    )


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
    if details:
        return "，".join(details)
    file_path = getattr(parsed, "path", "") or ""
    language = getattr(parsed, "language", "") or "源码"
    role, _, role_hint = _classify_file(Path(file_path).name, language)
    return f"{role_hint}，{language} 文件" if role_hint else "项目主体源码文件"


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
    total_files = len(files)
    max_files = _env_int("LLM_ARCHITECTURE_MAX_FILES", 24)
    max_explanation_chars = _env_int("LLM_ARCHITECTURE_MAX_EXPLANATION_CHARS", 120)
    if max_files:
        files = files[:max_files]
    for file_info in files:
        file_info["explanation"] = str(file_info.get("explanation") or "")[:max_explanation_chars]
    return {
        "goal": "为非技术人员解释跨语言项目结构",
        "files": files,
        "metadata": {
            "total_files": total_files,
            "sent_files": len(files),
            "truncated": len(files) < total_files,
        },
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
    return sorted(groups_by_name.items(), key=lambda item: (-sum(_importance_score(parsed, root_path) for parsed in item[1]), item[0]))[
        :MAX_GRAPH_GROUPS
    ]


def _select_representative_files(ranked_groups: Sequence[Tuple[str, List[Any]]], root_path: Optional[str]) -> Set[str]:
    selected: Set[str] = set()
    grouped = [
        (name, sorted(files, key=lambda parsed: (-_importance_score(parsed, root_path), -_signal(parsed), getattr(parsed, "path", ""))))
        for name, files in ranked_groups
    ]

    for _, files in grouped:
        for parsed in files[:MAX_FILES_PER_GROUP]:
            if _is_support_file(parsed, root_path):
                continue
            if len(selected) >= MAX_GRAPH_FILE_NODES:
                return selected
            selected.add(getattr(parsed, "path", "") or "")

    remaining = [
        parsed
        for _, files in grouped
        for parsed in files
        if (getattr(parsed, "path", "") or "") not in selected and not _is_support_file(parsed, root_path)
    ]
    for parsed in sorted(remaining, key=lambda item: (-_importance_score(item, root_path), -_signal(item), getattr(item, "path", ""))):
        if len(selected) >= MAX_GRAPH_FILE_NODES:
            break
        selected.add(getattr(parsed, "path", "") or "")
    if len(selected) < MAX_GRAPH_FILE_NODES:
        support_files = [
            parsed
            for _, files in grouped
            for parsed in files
            if (getattr(parsed, "path", "") or "") not in selected
        ]
        for parsed in sorted(support_files, key=lambda item: (-_importance_score(item, root_path), -_signal(item), getattr(item, "path", ""))):
            if len(selected) >= MAX_GRAPH_FILE_NODES:
                break
            selected.add(getattr(parsed, "path", "") or "")
    return selected


def _static_edges(nodes: List[Dict[str, Any]], group_ids: Set[str]) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    module_nodes = [node for node in nodes if node.get("nodeKind") == "module"]
    file_nodes = [node for node in nodes if node.get("isFile")]
    api_nodes = [node for node in file_nodes if node.get("shape") == "api"]
    ui_nodes = [node for node in file_nodes if node.get("shape") == "ui"]
    data_nodes = [node for node in file_nodes if node.get("shape") == "database"]
    config_nodes = [node for node in file_nodes if node.get("shape") == "config"]
    test_nodes = [node for node in file_nodes if node.get("shape") == "test"]
    service_nodes = [node for node in file_nodes if node.get("shape") == "service"]

    def add(source: str, target: str, relation_type: str, style: str = "solid", label: str = "") -> None:
        if source == target or len(edges) >= MAX_GRAPH_EDGES:
            return
        edge = {
            "source": source,
            "target": target,
            "type": relation_type,
            "label": label or RELATION_LABELS.get(relation_type, relation_type),
            "style": style,
        }
        if edge not in edges:
            edges.append(edge)

    for source in module_nodes:
        source_label = str(source.get("label") or source.get("id"))
        for target in module_nodes:
            if source["id"] == target["id"]:
                continue
            target_label = str(target.get("label") or target.get("id"))
            if "前端" in source_label and ("后端" in target_label or "接口" in target_label):
                source_hub = _group_hub(file_nodes, source["id"])
                target_hub = _group_hub(file_nodes, target["id"])
                if source_hub and target_hub:
                    add(source_hub["id"], target_hub["id"], "module_relates", label="前端调用后端")
            if "后端" in source_label and ("语义" in target_label or "图谱" in target_label):
                source_hub = _group_hub(file_nodes, source["id"])
                target_hub = _group_hub(file_nodes, target["id"])
                if source_hub and target_hub:
                    add(source_hub["id"], target_hub["id"], "module_relates", label="后端协作")
            if "测试" in source_label and "后端" in target_label:
                source_hub = _group_hub(file_nodes, source["id"])
                target_hub = _group_hub(file_nodes, target["id"])
                if source_hub and target_hub:
                    add(source_hub["id"], target_hub["id"], "tests", style="dashed")

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

    _connect_isolated_files(edges, file_nodes)
    return edges[:MAX_GRAPH_EDGES]


def _group_hub(file_nodes: Sequence[Dict[str, Any]], group_id: str) -> Optional[Dict[str, Any]]:
    group_files = [node for node in file_nodes if node.get("groupId") == group_id]
    if not group_files:
        return None
    priority = {"api": 0, "service": 1, "ui": 2, "database": 3, "config": 4, "test": 5}
    return sorted(group_files, key=lambda node: (priority.get(str(node.get("shape")), 9), str(node.get("path"))))[0]


def _connect_isolated_files(edges: List[Dict[str, Any]], file_nodes: Sequence[Dict[str, Any]]) -> None:
    degree: Dict[str, int] = {node["id"]: 0 for node in file_nodes}

    def recount_degree() -> None:
        for node_id in degree:
            degree[node_id] = 0
        for edge in edges:
            if edge.get("source") in degree:
                degree[str(edge["source"])] += 1
            if edge.get("target") in degree:
                degree[str(edge["target"])] += 1

    def add_related(source: str, target: str, relation_type: str = "related", label: str = "") -> bool:
        if len(edges) >= MAX_GRAPH_EDGES or source == target:
            return False
        edge = {
            "source": source,
            "target": target,
            "type": relation_type,
            "label": label or RELATION_LABELS[relation_type],
            "style": "dashed",
        }
        if edge in edges:
            return False
        edges.append(edge)
        degree[source] = degree.get(source, 0) + 1
        degree[target] = degree.get(target, 0) + 1
        return True

    recount_degree()

    by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for node in file_nodes:
        by_group[str(node.get("groupId") or "")].append(node)

    for group_files in by_group.values():
        if len(group_files) < 2:
            continue
        hub = _group_hub(group_files, str(group_files[0].get("groupId") or ""))
        if not hub:
            continue
        for node in group_files:
            if len(edges) >= MAX_GRAPH_EDGES:
                return
            if node["id"] == hub["id"] or degree.get(node["id"], 0) > 0:
                continue
            add_related(hub["id"], node["id"])

    primary_hub = _group_hub(file_nodes, "group_backend") or (file_nodes[0] if file_nodes else None)
    if not primary_hub:
        return
    for node in file_nodes:
        if len(edges) >= MAX_GRAPH_EDGES:
            return
        if degree.get(node["id"], 0) > 0:
            continue
        target = primary_hub
        if target["id"] == node["id"]:
            target = next((candidate for candidate in file_nodes if candidate["id"] != node["id"]), None)
        if target:
            add_related(node["id"], target["id"], "module_relates", "模块关联")


def _build_static_diagram(
    parsed_list: Sequence[Any],
    root_path: Optional[str],
    explanations: Dict[str, str],
) -> Dict[str, Any]:
    ranked_groups = _rank_groups(parsed_list, root_path)
    selected_files = _select_representative_files(ranked_groups, root_path)
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
        group_id = f"group_{_safe_id(group_name)}"
        group_label = _module_label(group_name)
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
                "module": group_label,
                "path": "" if group_name == "根目录" else f"{group_name}/",
                "shape": "box",
                "color": group_color,
                "isFile": False,
                "nodeKind": "module",
            }
        )

        ranked_files = sorted(group_files, key=lambda parsed: (-_signal(parsed), getattr(parsed, "path", "")))
        for parsed in ranked_files:
            file_path = getattr(parsed, "path", "") or ""
            if file_path not in selected_files:
                continue
            rel_path = _relative_path(file_path, root_path)
            language = getattr(parsed, "language", "") or "源码"
            role, shape, role_hint = _classify_file(rel_path, language)
            description = _file_description(parsed, explanations.get(file_path)) or role_hint
            nodes.append(
                {
                    "id": f"file_{group_index}_{_safe_id(rel_path)}",
                    "label": Path(rel_path).name,
                    "filename": Path(rel_path).name,
                    "type": role,
                    "language": language,
                    "description": description,
                    "groupId": group_id,
                    "module": group_label,
                    "path": rel_path,
                    "shape": shape,
                    "color": group_color,
                    "isFile": True,
                    "nodeKind": "file",
                    "size": int(getattr(parsed, "size", 0) or 0),
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
            "total_files": len(parsed_list),
            "displayed_files": len([node for node in nodes if node.get("isFile")]),
            "truncated": len([node for node in nodes if node.get("isFile")]) < len(parsed_list),
            "node_limit": MAX_GRAPH_FILE_NODES,
            "edge_limit": MAX_GRAPH_EDGES,
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
    else:
        for fallback_group in fallback.get("groups", []):
            fallback_group_id = str(fallback_group.get("id") or "")
            if fallback_group_id and fallback_group_id not in group_ids and len(groups) < MAX_GRAPH_GROUPS:
                groups.append(fallback_group)
                group_ids.add(fallback_group_id)

    nodes: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    file_node_count = 0

    def add_node(node: Dict[str, Any], index: int) -> None:
        nonlocal file_node_count
        node_id = _safe_id(str(node.get("id") or node.get("path") or node.get("label") or f"node_{index}"))
        if node_id in seen_ids:
            return
        path = str(node.get("path") or "")
        if path and path not in allowed_paths and not path.endswith("/"):
            return
        is_file = bool(node.get("isFile", bool(path and not path.endswith("/"))))
        if is_file and file_node_count >= MAX_AI_FILE_NODES:
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
                "filename": str(node.get("filename") or fallback_node.get("filename") or Path(path).name or ""),
                "type": str(node.get("type") or fallback_node.get("type") or "文件")[:32],
                "language": str(node.get("language") or fallback_node.get("language") or "")[:32],
                "description": str(node.get("description") or fallback_node.get("description") or "项目主体源码文件")[:260],
                "groupId": group_id,
                "module": str(node.get("module") or fallback_node.get("module") or "")[:48],
                "path": path,
                "shape": shape,
                "color": color,
                "isFile": bool(node.get("isFile", fallback_node.get("isFile", is_file))),
                "nodeKind": str(node.get("nodeKind") or fallback_node.get("nodeKind") or ("file" if path else "module")),
                "size": int(node.get("size") or fallback_node.get("size") or 0),
            }
        )
        if is_file:
            file_node_count += 1
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

    for fallback_node in fallback.get("nodes", []):
        if fallback_node.get("path") and fallback_node.get("path") in allowed_paths:
            add_node(fallback_node, len(nodes))

    if len(nodes) < 2:
        return None

    valid_ids = {node["id"] for node in nodes}
    edges: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str, str]] = set()

    def add_edge(
        source: str,
        target: str,
        relation_type: str,
        label: str = "",
        description: str = "",
        *,
        required: bool = False,
    ) -> None:
        if source not in valid_ids or target not in valid_ids or source == target or (not required and len(edges) >= MAX_AI_EDGES):
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

    for edge in ai_diagram.get("edges") or []:
        if not isinstance(edge, dict) or len(edges) >= MAX_AI_EDGES:
            continue
        source = _safe_id(str(edge.get("source") or edge.get("from") or ""))
        target = _safe_id(str(edge.get("target") or edge.get("to") or ""))
        if source not in valid_ids or target not in valid_ids or source == target:
            continue
        relation_type = str(edge.get("type") or "depends_on")
        if relation_type == "contains":
            continue
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
            "total_files": len(allowed_paths),
            "displayed_files": len([node for node in nodes if node.get("isFile")]),
            "truncated": len([node for node in nodes if node.get("isFile")]) < len(allowed_paths),
            "node_limit": MAX_AI_FILE_NODES,
            "edge_limit": MAX_AI_EDGES,
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
