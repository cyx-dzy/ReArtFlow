"""
FastAPI route for exposing diagram data.

- GET /diagram/{project_id}: return Mermaid string and G6 JSON for the given project.
- For demo purposes we store diagram data in an in‑memory dict.
  In a real system this would be persisted (DB, cache, etc.).
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from backend.diagram.project_graph import (
    PROJECT_DIAGRAM_STORE,
    format_diagram_response,
    get_project_diagram,
    store_project_diagram,
)

_DIAGRAM_STORE = PROJECT_DIAGRAM_STORE

router = APIRouter()

@router.get("/diagram/{project_id}")
def get_diagram(project_id: str):
    """Return Mermaid text and G6 JSON for *project_id*.

    If the project has no stored diagram we return a minimal placeholder
    with a single node so the client can still render something.
    """
    record = get_project_diagram(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Project diagram not found: {project_id}")
    return format_diagram_response(record)

@router.post("/diagram/{project_id}")
def store_diagram(project_id: str, payload: Dict):
    """Store a diagram dict for later retrieval.

    Expected payload shape: same as LLM ``diagram`` field, e.g. ``{"nodes": [...], "edges": [...]}``.
    """
    if not isinstance(payload, dict) or "nodes" not in payload:
        raise HTTPException(status_code=400, detail="Invalid diagram payload")
    record = store_project_diagram(project_id, payload, source_type="manual")
    return {"status": record["status"], "project_id": project_id}
