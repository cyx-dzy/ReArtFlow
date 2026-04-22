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
    return result
