"""FastAPI route for handling input submissions.

Accepts a JSON payload describing the input type (zip, github, gitee, local) and delegates
to the appropriate ``InputProcessor`` implementation.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from ...input.processor import InputProcessor
from ...input.zip_handler import ZipInputProcessor
from ...input.github_handler import GitHubInputProcessor
from ...input.gitee_handler import GiteeInputProcessor
from ...input.local_handler import LocalPathInputProcessor
from pathlib import Path

router = APIRouter()

# Mapping from ``type`` field to processor class
PROCESSOR_MAP = {
    "zip": ZipInputProcessor,
    "github": GitHubInputProcessor,
    "gitee": GiteeInputProcessor,
    "local": LocalPathInputProcessor,
}

@router.post("/input", status_code=status.HTTP_200_OK)
def handle_input(payload: Dict[str, Any]):
    """Handle an input submission.

    Expected payload structure::
        {
            "type": "zip" | "github" | "gitee" | "local",
            "payload": { ... }   # processor‑specific fields
        }
    """
    input_type = payload.get("type")
    if input_type not in PROCESSOR_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported input type: {input_type}")

    processor_cls = PROCESSOR_MAP[input_type]
    processor: InputProcessor = processor_cls()
    try:
        result = processor.process(payload.get("payload", {}))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # --- New behavior: generate a project_id, parse the extracted source, generate diagram, and store it ---
    import uuid
    from backend.api.routes.diagram import _DIAGRAM_STORE
    from backend.parser import parse_project
    from backend.semantic.llm_client import LLMClient
    from backend.semantic.formatter import to_mermaid, to_g6

    project_id = uuid.uuid4().hex
    # Store a minimal placeholder initially
    _DIAGRAM_STORE[project_id] = {"nodes": [{"id": "root", "label": project_id}], "edges": []}

    # Process the extracted path (result from ZipInputProcessor)
    extracted_path = result.get("path")
    if extracted_path:
        try:
            parsed_files = parse_project(extracted_path)
            client = LLMClient()
            merged_diagram = {"nodes": [], "edges": []}
            for pf in parsed_files:
                # Each ParsedFile has attributes: path, language
                # Read file content; if unavailable, treat as empty
                try:
                    with open(pf.path, "r", encoding="utf-8") as f:
                        code = f.read()
                except Exception:
                    code = ""
                language = pf.language if hasattr(pf, "language") else ""
                if code:
                    try:
                        llm_res = client.generate_explanation(code, language)
                        diagram = llm_res.get("diagram", {})
                        # Merge nodes (dedupe by id) and edges
                        for n in diagram.get("nodes", []):
                            if n not in merged_diagram["nodes"]:
                                merged_diagram["nodes"].append(n)
                        for e in diagram.get("edges", []):
                            if e not in merged_diagram["edges"]:
                                merged_diagram["edges"].append(e)
                    except Exception as exc:
                        # LLM failed – create a simple node based on filename
                        node_id = uuid.uuid4().hex[:8]
                        merged_diagram["nodes"].append({"id": node_id, "label": Path(pf.path).name})
                else:
                    # No code – still add a node representing the file
                    node_id = uuid.uuid4().hex[:8]
                    merged_diagram["nodes"].append({"id": node_id, "label": Path(pf.path).name})
        except Exception as exc:
            # If any step fails, keep the placeholder and log the error
            import logging
            logging.getLogger(__name__).error("Diagram generation failed: %s", exc)
        else:
            # Store the merged diagram for the project
            if merged_diagram["nodes"]:
                _DIAGRAM_STORE[project_id] = merged_diagram

    # Return the project identifier to the caller
    return {"project_id": project_id, "message": "Input processed and project created"}

