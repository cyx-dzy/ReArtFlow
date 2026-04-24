"""FastAPI route for AI semantic service.

POST /semantic expects a JSON payload with a list of parsed files (from Phase 2), each containing at least:
    {"path":..., "language":..., "code":...}
The route calls the unified LLM client, caches results, and returns the enriched list with Chinese explanations and diagram data.
"""

from fastapi import APIRouter, HTTPException
from fastapi.background import BackgroundTasks
from typing import List, Dict, Any

from ...semantic import LLMClient, to_mermaid, to_g6

router = APIRouter()

@router.post("/semantic")
def semantic_route(payload: Dict[str, Any], background: BackgroundTasks):
    parsed_files = payload.get("parsed_files")
    if not isinstance(parsed_files, list) or not parsed_files:
        raise HTTPException(status_code=400, detail="Missing or invalid 'parsed_files' list")
    client = LLMClient()
    enriched: List[Dict] = []
    for item in parsed_files:
        code = item.get("code")
        language = item.get("language")
        if not code or not language:
            raise HTTPException(status_code=400, detail="Each file must contain 'code' and 'language'")
        try:
            result = client.generate_explanation(code, language)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        # Add formatted outputs
        diagram = result.get("diagram", {})
        item["explanation"] = result.get("explanation", "")
        item["mermaid"] = to_mermaid(diagram)
        item["g6"] = to_g6(diagram)
        enriched.append(item)
    return {"enriched_files": enriched}
