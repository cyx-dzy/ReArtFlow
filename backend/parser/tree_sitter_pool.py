"""Thread-local Tree-sitter parser pool.

Uses official Tree-sitter grammar packages installed as separate Python modules.
"""

import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    from tree_sitter import Language, Node, Parser  # type: ignore
    import tree_sitter_c as ts_c  # type: ignore
    import tree_sitter_cpp as ts_cpp  # type: ignore
    import tree_sitter_go as ts_go  # type: ignore
    import tree_sitter_java as ts_java  # type: ignore
    import tree_sitter_javascript as ts_javascript  # type: ignore
    import tree_sitter_python as ts_python  # type: ignore
    import tree_sitter_rust as ts_rust  # type: ignore
    import tree_sitter_typescript as ts_typescript  # type: ignore
except ModuleNotFoundError:
    Language = None  # type: ignore
    Node = None  # type: ignore
    Parser = None  # type: ignore
    ts_c = None  # type: ignore
    ts_cpp = None  # type: ignore
    ts_go = None  # type: ignore
    ts_java = None  # type: ignore
    ts_javascript = None  # type: ignore
    ts_python = None  # type: ignore
    ts_rust = None  # type: ignore
    ts_typescript = None  # type: ignore

EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
}

DISPLAY_LANGUAGE_MAP = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "tsx": "TSX",
    "java": "Java",
    "go": "Go",
    "rust": "Rust",
    "c": "C",
    "cpp": "C++",
}

LANGUAGE_FACTORY_MAP = {
    "python": lambda: Language(ts_python.language()),
    "javascript": lambda: Language(ts_javascript.language()),
    "typescript": lambda: Language(ts_typescript.language_typescript()),
    "tsx": lambda: Language(ts_typescript.language_tsx()),
    "java": lambda: Language(ts_java.language()),
    "go": lambda: Language(ts_go.language()),
    "rust": lambda: Language(ts_rust.language()),
    "c": lambda: Language(ts_c.language()),
    "cpp": lambda: Language(ts_cpp.language()),
}

FUNCTION_NODE_TYPES = {
    "python": {"function_definition"},
    "javascript": {"function_declaration", "generator_function_declaration", "method_definition", "arrow_function", "function"},
    "typescript": {"function_declaration", "generator_function_declaration", "method_definition", "arrow_function", "function"},
    "tsx": {"function_declaration", "generator_function_declaration", "method_definition", "arrow_function", "function"},
    "java": {"method_declaration", "constructor_declaration"},
    "go": {"function_declaration", "method_declaration"},
    "rust": {"function_item"},
    "c": {"function_definition"},
    "cpp": {"function_definition"},
}

CLASS_NODE_TYPES = {
    "python": {"class_definition"},
    "javascript": {"class_declaration"},
    "typescript": {"class_declaration"},
    "tsx": {"class_declaration"},
    "java": {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"},
    "go": set(),
    "rust": {"struct_item", "enum_item", "trait_item", "impl_item"},
    "c": {"struct_specifier", "union_specifier", "enum_specifier"},
    "cpp": {"class_specifier", "struct_specifier", "enum_specifier"},
}

IMPORT_NODE_TYPES = {
    "python": {"import_statement", "import_from_statement"},
    "javascript": {"import_statement"},
    "typescript": {"import_statement"},
    "tsx": {"import_statement"},
    "java": {"import_declaration"},
    "go": {"import_declaration", "import_spec"},
    "rust": {"use_declaration"},
    "c": {"preproc_include"},
    "cpp": {"preproc_include"},
}

CALL_NODE_TYPES = {
    "python": {"call"},
    "javascript": {"call_expression", "new_expression"},
    "typescript": {"call_expression", "new_expression"},
    "tsx": {"call_expression", "new_expression"},
    "java": {"method_invocation", "object_creation_expression"},
    "go": {"call_expression"},
    "rust": {"call_expression", "macro_invocation"},
    "c": {"call_expression"},
    "cpp": {"call_expression"},
}

_thread_local = threading.local()
_language_cache: Dict[str, Any] = {}


def _require_runtime() -> None:
    if Parser is None:
        raise RuntimeError(
            "Tree-sitter runtime is not installed. Install the project virtualenv dependencies to enable parsing."
        )


def _load_language(language_name: str):
    _require_runtime()
    if language_name not in _language_cache:
        factory = LANGUAGE_FACTORY_MAP.get(language_name)
        if factory is None:
            raise ValueError(f"Unsupported Tree-sitter language: {language_name}")
        _language_cache[language_name] = factory()
    return _language_cache[language_name]


def _get_parser(language_name: str):
    _require_runtime()
    parsers = getattr(_thread_local, "parsers", None)
    if parsers is None:
        parsers = {}
        _thread_local.parsers = parsers
    if language_name not in parsers:
        parser = Parser(_load_language(language_name))
        parsers[language_name] = parser
    return parsers[language_name]


def _detect_language_key(file_path: str) -> Optional[str]:
    return EXTENSION_LANGUAGE_MAP.get(Path(file_path).suffix.lower())


def _count_tree(node: "Node", interested_types: Iterable[str]) -> int:
    interested = set(interested_types)
    total = 0
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in interested:
            total += 1
        stack.extend(reversed(current.children))
    return total


def _build_ast_summary(root_node: "Node", language_key: str) -> Dict[str, int]:
    return {
        "functions": _count_tree(root_node, FUNCTION_NODE_TYPES.get(language_key, set())),
        "classes": _count_tree(root_node, CLASS_NODE_TYPES.get(language_key, set())),
        "imports": _count_tree(root_node, IMPORT_NODE_TYPES.get(language_key, set())),
        "calls": _count_tree(root_node, CALL_NODE_TYPES.get(language_key, set())),
    }


def _regex_ast_summary(source: str, language_key: str) -> Dict[str, int]:
    if language_key == "python":
        return {
            "functions": len(re.findall(r"^\s*def\s+\w+\s*\(", source, flags=re.MULTILINE)),
            "classes": len(re.findall(r"^\s*class\s+\w+", source, flags=re.MULTILINE)),
            "imports": len(re.findall(r"^\s*(?:from\s+\S+\s+import|import\s+\S+)", source, flags=re.MULTILINE)),
            "calls": len(re.findall(r"\b\w+(?:\.\w+)?\s*\(", source)),
        }

    if language_key in {"javascript", "typescript", "tsx"}:
        return {
            "functions": len(
                re.findall(
                    r"\bfunction\s+\w+\s*\(|\b\w+\s*=\s*\([^)]*\)\s*=>|\b\w+\s*:\s*\([^)]*\)\s*=>",
                    source,
                )
            ),
            "classes": len(re.findall(r"\bclass\s+\w+", source)),
            "imports": len(re.findall(r"^\s*import\s+", source, flags=re.MULTILINE)),
            "calls": len(re.findall(r"\b\w+(?:\.\w+)?\s*\(", source)),
        }

    if language_key == "java":
        return {
            "functions": len(
                re.findall(
                    r"\b(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+\w+\s*\(",
                    source,
                )
            ),
            "classes": len(re.findall(r"\b(?:class|interface|enum|record)\s+\w+", source)),
            "imports": len(re.findall(r"^\s*import\s+", source, flags=re.MULTILINE)),
            "calls": len(re.findall(r"\b\w+(?:\.\w+)?\s*\(", source)),
        }

    if language_key == "go":
        return {
            "functions": len(re.findall(r"^\s*func\s+(?:\([^)]+\)\s*)?\w+\s*\(", source, flags=re.MULTILINE)),
            "classes": 0,
            "imports": len(re.findall(r"^\s*import\s+", source, flags=re.MULTILINE)),
            "calls": len(re.findall(r"\b\w+(?:\.\w+)?\s*\(", source)),
        }

    if language_key == "rust":
        return {
            "functions": len(re.findall(r"^\s*fn\s+\w+\s*\(", source, flags=re.MULTILINE)),
            "classes": len(re.findall(r"^\s*(?:struct|enum|trait|impl)\s+\w+", source, flags=re.MULTILINE)),
            "imports": len(re.findall(r"^\s*use\s+", source, flags=re.MULTILINE)),
            "calls": len(re.findall(r"\b\w+!?\s*\(", source)),
        }

    return {
        "functions": len(re.findall(r"\b\w+\s+\w+\s*\([^;]*\)\s*\{", source)),
        "classes": len(re.findall(r"\b(?:class|struct|union|enum)\s+\w+", source)),
        "imports": len(re.findall(r"^\s*#\s*include\s+", source, flags=re.MULTILINE)),
        "calls": len(re.findall(r"\b\w+(?:->\w+|::\w+|\.\w+)?\s*\(", source)),
    }


def parse_file(file_path: str) -> Dict[str, Any]:
    language_key = _detect_language_key(file_path)
    if not language_key:
        raise ValueError(f"Unsupported file type for Tree-sitter parsing: {file_path}")

    start = time.perf_counter()
    path = Path(file_path)
    source_bytes = path.read_bytes()
    try:
        parser = _get_parser(language_key)
        tree = parser.parse(source_bytes)
        ast_summary = _build_ast_summary(tree.root_node, language_key)
    except Exception:
        source = source_bytes.decode("utf-8", errors="ignore")
        ast_summary = _regex_ast_summary(source, language_key)
    elapsed_ms = (time.perf_counter() - start) * 1000

    stat = os.stat(file_path)
    return {
        "path": str(Path(file_path).absolute()),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "parse_time_ms": elapsed_ms,
        "language": DISPLAY_LANGUAGE_MAP[language_key],
        "ast_summary": ast_summary,
    }


__all__ = ["parse_file", "_get_parser"]
