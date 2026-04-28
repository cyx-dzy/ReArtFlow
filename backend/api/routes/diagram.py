"""
FastAPI route for exposing diagram data.

- GET /diagram/{project_id}: return Mermaid string and G6 JSON for the given project.
- For demo purposes we store diagram data in an in‑memory dict.
  In a real system this would be persisted (DB, cache, etc.).
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

# Simple in‑memory store: project_id -> diagram dict (same shape as LLM output)
_DIAGRAM_STORE: Dict[str, Dict] = {}

router = APIRouter()

@router.get("/diagram/{project_id}")
def get_diagram(project_id: str):
    """Return Mermaid text and G6 JSON for *project_id*.

    If the project has no stored diagram we return a minimal placeholder
    with a single node so the client can still render something.
    """
    diagram = _DIAGRAM_STORE.get(project_id)
    if diagram is None:
        # placeholder diagram – a single node with the project id
        diagram = {"nodes": [{"id": "root", "label": project_id}], "edges": []}
        _DIAGRAM_STORE[project_id] = diagram
    # Convert using existing utilities
    from backend.semantic import to_mermaid, to_g6
    mermaid = to_mermaid(diagram)
    g6 = to_g6(diagram)
    return {"mermaid": mermaid, "g6": g6}

@router.post("/diagram/{project_id}")
def store_diagram(project_id: str, payload: Dict):
    """Store a diagram dict for later retrieval.

    Expected payload shape: same as LLM ``diagram`` field, e.g. ``{"nodes": [...], "edges": [...]}``.
    """
    if not isinstance(payload, dict) or "nodes" not in payload:
        raise HTTPException(status_code=400, detail="Invalid diagram payload")
    _DIAGRAM_STORE[project_id] = payload
    return {"status": "stored", "project_id": project_id}
