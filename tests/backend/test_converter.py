import pytest
from backend.diagram.converter import json_to_mermaid


def test_json_to_mermaid_basic():
    data = {
        "nodes": [
            {"id": "modA", "label": "模块A"},
            {"id": "modB", "label": "模块B"},
            {"id": "modC", "label": "模块C"},
        ],
        "edges": [
            {"id": "modA", "target": "modB"},
            {"id": "modB", "target": "modC"},
        ],
    }
    mermaid = json_to_mermaid(data)
    # Verify node definitions
    assert "modA[模块A]" in mermaid
    assert "modB[模块B]" in mermaid
    assert "modC[模块C]" in mermaid
    # Verify edge definitions
    assert "modA --> modB" in mermaid
    assert "modB --> modC" in mermaid


def test_json_to_mermaid_escaping():
    data = {
        "nodes": [
            {"id": "node1", "label": "Node[Special];"},
        ],
        "edges": [],
    }
    mermaid = json_to_mermaid(data)
    # The label characters [, ], ; should be escaped in the generated Mermaid string
    assert "node1[Node\\[Special\\];]" in mermaid


def test_json_to_mermaid_empty_input():
    mermaid = json_to_mermaid({})
    assert mermaid.strip() == "flowchart TD"
