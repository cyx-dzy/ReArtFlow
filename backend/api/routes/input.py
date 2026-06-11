"""FastAPI route for handling input submissions.

Accepts a JSON payload describing the input type (zip, github, gitee, local) and delegates
to the appropriate ``InputProcessor`` implementation.
"""

import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, status

from ...diagram.project_graph import build_diagram_from_parsed_files, format_diagram_response, store_project_diagram
from ...input.processor import InputProcessor
from ...input.zip_handler import ZipInputProcessor
from ...input.github_handler import GitHubInputProcessor
from ...input.gitee_handler import GiteeInputProcessor
from ...input.local_handler import LocalPathInputProcessor
from ...parser import parse_project
from ...semantic.llm_client import LLMClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Mapping from ``type`` field to processor class
PROCESSOR_MAP = {
    "zip": ZipInputProcessor,
    "github": GitHubInputProcessor,
    "gitee": GiteeInputProcessor,
    "local": LocalPathInputProcessor,
}


def _provider_has_key(provider: str) -> bool:
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "qianwen": bool(os.getenv("QIANWEN_API_KEY")),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
    }.get(provider, False)


def _collect_explanations(parsed_files) -> Dict[str, str]:
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    if not _provider_has_key(provider):
        return {}

    client = LLMClient()
    explanations: Dict[str, str] = {}
    for parsed in parsed_files:
        try:
            code = Path(parsed.path).read_text(encoding="utf-8", errors="ignore")
            if not code.strip():
                continue
            result = client.generate_explanation(code[:12000], parsed.language)
            explanation = result.get("explanation")
            if isinstance(explanation, str):
                explanations[parsed.path] = explanation
        except Exception as exc:
            logger.warning("LLM explanation failed for %s: %s", parsed.path, exc)
    return explanations


def _create_project_from_processed_input(result: Dict[str, Any]) -> Dict[str, Any]:
    project_id = uuid.uuid4().hex
    source_path = result.get("path", "")
    source_type = result.get("source_type", "")
    errors = []

    if not source_path:
        raise HTTPException(status_code=400, detail="Input processor did not return a source path")

    try:
        parsed_files = parse_project(source_path)
    except Exception as exc:
        logger.exception("Project parsing failed")
        errors.append(str(exc))
        diagram = {"nodes": [{"id": "project", "label": "解析失败", "type": "error"}], "edges": []}
        record = store_project_diagram(
            project_id,
            diagram,
            status="error",
            source_type=source_type,
            source_path=source_path,
            errors=errors,
        )
        return {"project_id": project_id, "status": record["status"], "errors": errors}

    explanations = _collect_explanations(parsed_files)
    diagram = build_diagram_from_parsed_files(parsed_files, root_path=source_path, explanations=explanations)
    record = store_project_diagram(
        project_id,
        diagram,
        status="ready",
        source_type=source_type,
        source_path=source_path,
        errors=errors,
    )
    response = format_diagram_response(record)
    response["message"] = "Input processed and diagram generated"
    return response


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

    return _create_project_from_processed_input(result)


@router.post("/input/zip", status_code=status.HTTP_200_OK)
async def handle_zip_upload(request: Request):
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Uploaded zip body is empty")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as handle:
            handle.write(body)
            tmp_path = handle.name
        result = ZipInputProcessor().process({"file_path": tmp_path})
        return _create_project_from_processed_input(result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

