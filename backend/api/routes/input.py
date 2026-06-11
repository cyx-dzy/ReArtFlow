"""FastAPI routes for project input and background generation jobs."""

import logging
import os
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, status

from ...diagram.project_graph import build_diagram_from_parsed_files, format_diagram_response, store_project_diagram
from ...input.gitee_handler import GiteeInputProcessor
from ...input.github_handler import GitHubInputProcessor
from ...input.local_handler import LocalPathInputProcessor
from ...input.processor import InputProcessor
from ...input.zip_handler import ZipInputProcessor
from ...parser import parse_project
from ...semantic.llm_client import LLMClient

router = APIRouter()
logger = logging.getLogger(__name__)

PROCESSOR_MAP = {
    "zip": ZipInputProcessor,
    "github": GitHubInputProcessor,
    "gitee": GiteeInputProcessor,
    "local": LocalPathInputProcessor,
}

_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=int(os.getenv("INPUT_JOB_WORKERS", "2")))
_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


def _provider_has_key(provider: str) -> bool:
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "qianwen": bool(os.getenv("QIANWEN_API_KEY")),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
    }.get(provider, False)


def _update_job(
    job_id: Optional[str],
    *,
    status_value: Optional[str] = None,
    stage: Optional[str] = None,
    message: Optional[str] = None,
    current: Optional[int] = None,
    total: Optional[int] = None,
    project_id: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    if not job_id:
        return
    with _JOBS_LOCK:
        job = _JOBS.setdefault(
            job_id,
            {
                "job_id": job_id,
                "status": "queued",
                "stage": "queued",
                "message": "等待处理",
                "current": 0,
                "total": 1,
                "project_id": None,
                "result": None,
                "error": None,
                "created_at": time.time(),
                "updated_at": time.time(),
            },
        )
        if status_value is not None:
            job["status"] = status_value
        if stage is not None:
            job["stage"] = stage
        if message is not None:
            job["message"] = message
        if current is not None:
            job["current"] = current
        if total is not None:
            job["total"] = max(total, 1)
        if project_id is not None:
            job["project_id"] = project_id
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        job["updated_at"] = time.time()


def _get_job(job_id: str) -> Dict[str, Any]:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        payload = dict(job)
    total = max(int(payload.get("total") or 1), 1)
    current = min(int(payload.get("current") or 0), total)
    payload["progress"] = round(current / total * 100)
    return payload


def _collect_explanations(parsed_files, job_id: Optional[str] = None) -> Dict[str, str]:
    provider = os.getenv("LLM_PROVIDER", "qianwen").lower()
    if not _provider_has_key(provider):
        logger.info("Skipping LLM explanations: provider=%s has no API key", provider)
        _update_job(job_id, stage="ai_skipped", message=f"未配置 {provider} API Key，跳过 AI 解释")
        return {}

    max_files = max(int(os.getenv("LLM_MAX_FILES", "20")), 0)
    max_chars_per_file = max(int(os.getenv("LLM_MAX_CHARS_PER_FILE", "4000")), 200)
    max_total_chars = max(int(os.getenv("LLM_MAX_TOTAL_CHARS", "60000")), max_chars_per_file)
    if max_files == 0:
        logger.info("Skipping LLM explanations because LLM_MAX_FILES=0")
        _update_job(job_id, stage="ai_skipped", message="LLM_MAX_FILES=0，跳过 AI 解释")
        return {}

    def rank_file(parsed) -> tuple[int, int, str]:
        summary = getattr(parsed, "ast_summary", {}) or {}
        signal = sum(int(value or 0) for value in summary.values())
        size = int(getattr(parsed, "size", 0) or 0)
        return (-signal, size, getattr(parsed, "path", ""))

    selected_files = sorted(parsed_files, key=rank_file)[:max_files]
    client = LLMClient()
    explanations: Dict[str, str] = {}
    used_chars = 0
    total = len(selected_files)
    logger.info(
        "Starting LLM explanations provider=%s model=%s selected_files=%s max_total_chars=%s",
        provider,
        client.model,
        total,
        max_total_chars,
    )
    for index, parsed in enumerate(selected_files, start=1):
        try:
            code = Path(parsed.path).read_text(encoding="utf-8", errors="ignore")
            if not code.strip():
                continue
            remaining = max_total_chars - used_chars
            if remaining <= 0:
                logger.info("Stopping LLM explanations: total character budget exhausted")
                break
            snippet = code[: min(max_chars_per_file, remaining)]
            used_chars += len(snippet)
            _update_job(
                job_id,
                stage="ai",
                message=f"AI 正在解释 {index}/{total}: {Path(parsed.path).name}",
                current=index,
                total=total,
            )
            logger.info("LLM explanation %s/%s path=%s chars=%s", index, total, parsed.path, len(snippet))
            result = client.generate_explanation(snippet, parsed.language)
            explanation = result.get("explanation")
            if isinstance(explanation, str):
                explanations[parsed.path] = explanation
        except Exception as exc:
            logger.warning("LLM explanation failed for %s: %s", parsed.path, exc)
    logger.info("Finished LLM explanations generated=%s used_chars=%s", len(explanations), used_chars)
    return explanations


def _create_project_from_processed_input(result: Dict[str, Any], job_id: Optional[str] = None) -> Dict[str, Any]:
    project_id = uuid.uuid4().hex
    source_path = result.get("path", "")
    source_type = result.get("source_type", "")
    errors = []

    if not source_path:
        raise HTTPException(status_code=400, detail="Input processor did not return a source path")

    try:
        logger.info("Project job started project_id=%s source_type=%s source_path=%s", project_id, source_type, source_path)
        _update_job(job_id, status_value="running", stage="parse", message="正在扫描源码文件", project_id=project_id)

        def on_parse_progress(done: int, total: int, file_path: str) -> None:
            if done == 0:
                message = f"发现 {total} 个可解析源码文件"
            else:
                message = f"正在解析 {done}/{total}: {Path(file_path).name}"
            logger.info("Parse progress project_id=%s %s/%s %s", project_id, done, total, file_path)
            _update_job(job_id, stage="parse", message=message, current=done, total=total)

        parsed_files = parse_project(source_path, progress_callback=on_parse_progress)
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
        response = {"project_id": project_id, "status": record["status"], "errors": errors}
        _update_job(job_id, status_value="error", stage="error", message="解析失败", result=response, error=str(exc))
        return response

    _update_job(job_id, stage="ai", message="源码解析完成，准备进行 AI 增强", current=0, total=1)
    explanations = _collect_explanations(parsed_files, job_id=job_id)
    _update_job(job_id, stage="diagram", message="正在生成流程图", current=1, total=1)
    logger.info("Building diagram project_id=%s files=%s explanations=%s", project_id, len(parsed_files), len(explanations))
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
    logger.info("Project job completed project_id=%s nodes=%s edges=%s", project_id, len(diagram["nodes"]), len(diagram["edges"]))
    _update_job(job_id, status_value="ready", stage="done", message="流程图生成完成", current=1, total=1, result=response)
    return response


def _run_job(job_id: str, input_type: str, payload: Dict[str, Any]) -> None:
    tmp_path = payload.pop("_tmp_path", None)
    try:
        logger.info("Input job started job_id=%s input_type=%s", job_id, input_type)
        _update_job(job_id, status_value="running", stage="input", message="正在处理输入")
        processor_cls = PROCESSOR_MAP[input_type]
        result = processor_cls().process(payload)
        _update_job(job_id, stage="extract", message="输入处理完成，准备解析项目")
        _create_project_from_processed_input(result, job_id=job_id)
    except Exception as exc:
        logger.exception("Input job failed job_id=%s", job_id)
        _update_job(job_id, status_value="error", stage="error", message="任务失败", error=str(exc))
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@router.post("/input", status_code=status.HTTP_200_OK)
def handle_input(payload: Dict[str, Any]):
    input_type = payload.get("type")
    if input_type not in PROCESSOR_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported input type: {input_type}")

    processor_cls = PROCESSOR_MAP[input_type]
    processor: InputProcessor = processor_cls()
    try:
        result = processor.process(payload.get("payload", {}))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@router.post("/input/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_input_job(payload: Dict[str, Any]):
    input_type = payload.get("type")
    if input_type not in PROCESSOR_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported input type: {input_type}")
    job_id = uuid.uuid4().hex
    _update_job(job_id, status_value="queued", stage="queued", message="任务已创建", current=0, total=1)
    _JOB_EXECUTOR.submit(_run_job, job_id, input_type, dict(payload.get("payload", {})))
    return _get_job(job_id)


@router.post("/input/zip/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_zip_job(request: Request):
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Uploaded zip body is empty")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as handle:
        handle.write(body)
        tmp_path = handle.name

    job_id = uuid.uuid4().hex
    _update_job(job_id, status_value="queued", stage="queued", message="zip 已上传，等待解压", current=0, total=1)
    _JOB_EXECUTOR.submit(_run_job, job_id, "zip", {"file_path": tmp_path, "_tmp_path": tmp_path})
    return _get_job(job_id)


@router.get("/input/jobs/{job_id}", status_code=status.HTTP_200_OK)
def get_input_job(job_id: str):
    return _get_job(job_id)
