from pathlib import Path

from backend.diagram.project_graph import build_architecture_snapshot, build_diagram_from_parsed_files
from backend.parser.models import ParsedFile
from backend.semantic import to_mermaid


def _parsed(path: Path, language: str = "Python") -> ParsedFile:
    return ParsedFile(
        path=str(path),
        size=100,
        mtime=1.0,
        parse_time_ms=1.0,
        language=language,
        ast_summary={"functions": 2, "classes": 1, "imports": 1, "calls": 3},
    )


def test_project_graph_builds_module_and_role_overview(tmp_path: Path):
    backend = tmp_path / "backend"
    frontend = tmp_path / "frontend"
    backend.mkdir()
    frontend.mkdir()
    files = [
        _parsed(backend / "api.py"),
        _parsed(backend / "models.py"),
        _parsed(frontend / "App.vue", "TSX"),
    ]

    graph = build_diagram_from_parsed_files(files, root_path=str(tmp_path))

    labels = {node["label"] for node in graph["nodes"]}
    shapes = {node["label"]: node["shape"] for node in graph["nodes"]}
    edge_types = {edge["type"] for edge in graph["edges"]}

    assert "项目总览" in labels
    assert "backend 模块" in labels
    assert "frontend 模块" in labels
    assert shapes["models.py"] == "database"
    assert shapes["api.py"] == "api"
    assert shapes["App.vue"] == "ui"
    assert "contains" in edge_types
    assert len(graph["nodes"]) <= 42
    assert len(graph["edges"]) <= 72

    mermaid = to_mermaid(graph)
    assert "subgraph" in mermaid
    assert "读写数据" in mermaid or "包含" in mermaid


def test_architecture_snapshot_is_llm_friendly(tmp_path: Path):
    backend = tmp_path / "backend"
    backend.mkdir()
    model_file = backend / "models.py"
    parsed = _parsed(model_file)

    snapshot = build_architecture_snapshot([parsed], root_path=str(tmp_path), explanations={str(model_file): "用户数据模型"})

    assert snapshot["goal"] == "为非技术人员解释跨语言项目结构"
    assert snapshot["files"][0]["path"] == "backend/models.py"
    assert snapshot["files"][0]["shape"] == "database"
    assert "reads_writes" in snapshot["relation_types"]


def test_project_graph_accepts_valid_ai_relationships_and_filters_bad_paths(tmp_path: Path):
    backend = tmp_path / "backend"
    frontend = tmp_path / "frontend"
    backend.mkdir()
    frontend.mkdir()
    api = _parsed(backend / "api.py")
    model = _parsed(backend / "models.py")
    ui = _parsed(frontend / "App.vue", "TSX")
    ai_diagram = {
        "title": "示例项目",
        "summary": "前端调用接口，接口读写数据。",
        "groups": [
            {"id": "backend", "label": "后端模块", "description": "接口与数据", "color": "#38bdf8"},
            {"id": "frontend", "label": "前端模块", "description": "用户界面", "color": "#f472b6"},
        ],
        "nodes": [
            {"id": "api", "label": "接口入口", "type": "接口层", "shape": "api", "groupId": "backend", "path": "backend/api.py"},
            {
                "id": "models",
                "label": "数据模型",
                "type": "数据层",
                "shape": "database",
                "groupId": "backend",
                "path": "backend/models.py",
            },
            {"id": "app", "label": "用户界面", "type": "界面层", "shape": "ui", "groupId": "frontend", "path": "frontend/App.vue"},
            {"id": "fake", "label": "不存在", "type": "文件", "shape": "document", "path": "missing.py"},
        ],
        "edges": [
            {"source": "app", "target": "api", "type": "routes_to", "label": "请求接口"},
            {"source": "api", "target": "models", "type": "reads_writes", "label": "读写数据"},
            {"source": "fake", "target": "api", "type": "depends_on", "label": "无效关系"},
        ],
    }

    graph = build_diagram_from_parsed_files([api, model, ui], root_path=str(tmp_path), ai_diagram=ai_diagram)

    node_ids = {node["id"] for node in graph["nodes"]}
    edge_types = {edge["type"] for edge in graph["edges"]}
    assert "fake" not in node_ids
    assert {"routes_to", "reads_writes"}.issubset(edge_types)
    assert graph["metadata"]["source"] == "ai"
