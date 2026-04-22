"""FastAPI endpoint for bulk code parsing.

POST /parse expects a JSON payload:
    {"source_path": "<absolute-or-relative-path>"}
The endpoint calls ``backend.parser.parse_project`` and returns the list of parsed
files (as Pydantic models, which FastAPI automatically serialises to JSON).
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path

from ..parser import parse_project

router = APIRouter()

@router.post("/parse")
def parse_route(payload: dict):
    source_path = payload.get("source_path")
    if not source_path:
        raise HTTPException(status_code=400, detail="Missing 'source_path' in request payload")
    try:
        # Resolve path relative to current working directory for convenience
        resolved = str(Path(source_path).resolve())
        result = parse_project(resolved)
        # FastAPI will convert the list of Pydantic models to JSON automatically
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

__all__ = ["router"]
