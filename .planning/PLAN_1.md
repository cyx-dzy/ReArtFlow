---
phase: 01-input-security
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/input/processor.py           # Abstract contract for all input sources
  - backend/input/zip_handler.py          # Handles zip upload & extraction
  - backend/input/github_handler.py       # Clones GitHub repos safely
  - backend/input/gitee_handler.py        # Clones Gitee repos safely
  - backend/input/local_handler.py        # Directly parses a local directory
  - backend/security/validation.py        # URL validation & SSRF protection utilities
  - backend/api/routes/input.py           # FastAPI route exposing the input API
autonomous: true
requirements:
  - INP-01
  - INP-02
  - INP-03
  - INP-04
  - SEC-01
  - SEC-02
  - SEC-03
user_setup: []        # No manual steps required; secrets are read from environment variables
must_haves:
  truths:
    - User can upload a local Zip file and the system extracts it correctly.
    - User can enter a GitHub URL and the system clones the repository.
    - User can enter a Gitee URL and the system clones the repository.
    - User can specify a local filesystem path and the system parses it directly.
    - System validates repository URLs to prevent SSRF and reads all secrets from environment variables only.
  artifacts:
    - path: "backend/input/zip_handler.py"
      provides: "zip upload handling & extraction"
    - path: "backend/input/github_handler.py"
      provides: "secure GitHub cloning"
    - path: "backend/input/gitee_handler.py"
      provides: "secure Gitee cloning"
    - path: "backend/input/local_handler.py"
      provides: "local path parsing entry point"
    - path: "backend/security/validation.py"
      provides: "URL validation, SSRF protection, env‑var secret loading"
    - path: "backend/api/routes/input.py"
      provides: "FastAPI endpoint `POST /input` that dispatches to the above handlers"
  key_links:
    - from: "backend/api/routes/input.py"
      to: "backend/input/processor.py"
      via: "instantiates concrete handler based on payload"
    - from: "backend/input/processor.py"
      to: "backend/security/validation.py"
      via: "calls `validate_repository_url` before any network request"
    - from: "backend/input/zip_handler.py"
      to: "stdlib zipfile"
      via: "uses `zipfile.ZipFile` to extract contents"
    - from: "backend/input/github_handler.py"
      to: "git CLI / GitPython"
      via: "executes `git clone` via subprocess after URL validation"
---

<objective>
Implement secure, multi‑source input handling for the AI Agent. 
Purpose: Enable users to provide code bases (zip, GitHub, Gitee, local path) while ensuring all secrets are sourced from environment variables and repository URLs are validated to prevent SSRF attacks. 
Output: A set of backend modules and a FastAPI route that together satisfy all Phase 1 requirements.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
</execution_context>

<context>
# No additional external context needed; all required information is captured in the above files.
</context>

<tasks>

<task type="auto">
  <name>Task 1 – Define input processor contract</name>
  <files>backend/input/processor.py</files>
  <action>
    Create an abstract base class `InputProcessor` with a single method `process(self, payload: dict) -> dict`.  
    Include type hints, comprehensive docstrings, and raise `NotImplementedError` for the method.  
    Export the class via `__all__ = ["InputProcessor"]`.
  </action>
  <verify>
    <automated>python - <<'PY'
from backend.input.processor import InputProcessor
assert hasattr(InputProcessor, 'process')
print("Contract exists")
PY
</automated>
  </verify>
  <done>`InputProcessor` defined, importable, and documented.</done>
</task>

<task type="auto">
  <name>Task 2 – Implement secure zip upload handler</name>
  <files>backend/input/zip_handler.py</files>
  <action>
    Implement `ZipInputProcessor` subclassing `InputProcessor`.  
    - Validate that the uploaded file is a zip archive (magic header).  
    - Extract to a temporary directory using `zipfile.ZipFile`.  
    - Return a dictionary `{ "source_type": "zip", "path": <extracted_dir> }`.  
    Ensure no path traversal is possible (use `os.path.normpath` & check containment).  
    Add explicit imports and a module‑level `__all__`.
  </action>
  <verify>
    <automated>pytest -q tests/backend/input/test_zip_handler.py</automated>
  </verify>
  <done>Zip uploads are safely extracted and the handler returns the expected dict.</done>
</task>

<task type="auto">
  <name>Task 3 – Implement secure GitHub & Gitee clone handlers</name>
  <files>backend/input/github_handler.py, backend/input/gitee_handler.py</files>
  <action>
    For each platform create a subclass (`GitHubInputProcessor`, `GiteeInputProcessor`).  
    - Call `backend.security.validation.validate_repository_url(url, allowed_hosts=["github.com","gitee.com"])` before any network operation.  
    - Use `subprocess.run(["git","clone",url, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)` inside a temporary directory.  
    - Return `{ "source_type": "github"|"gitee", "path": <cloned_dir> }`.  
    - Include robust error handling: raise a custom `InputError` with clear message on failure.
  </action>
  <verify>
    <automated>pytest -q tests/backend/input/test_git_handlers.py</automated>
  </verify>
  <done>GitHub and Gitee URLs are cloned only after validation; failures produce clear errors.</done>
</task>

<task type="auto">
  <name>Task 4 – Implement local path handler</name>
  <files>backend/input/local_handler.py</files>
  <action>
    Implement `LocalPathInputProcessor` subclass.  
    - Verify the provided path exists and is a directory.  
    - Perform a shallow sanity check (read permission).  
    - Return `{ "source_type": "local", "path": <abs_path> }`.  
    No external network calls are performed.
  </action>
  <verify>
    <automated>pytest -q tests/backend/input/test_local_handler.py</automated>
  </verify>
  <done>Local directory paths are accepted, validated, and returned.</done>
</task>

<task type="auto">
  <name>Task 5 – Central FastAPI route wiring</name>
  <files>backend/api/routes/input.py</files>
  <action>
    Add a `POST /input` endpoint that:
    1. Receives JSON `{ "type": "zip"|"github"|"gitee"|"local", "payload": {...} }`.
    2. Instantiates the appropriate processor (`ZipInputProcessor`, etc.) based on `"type"`.
    3. Calls `process(payload)` and returns the resulting dict with status 200.
    4. Catches `InputError` and returns status 400 with JSON error details.
    Ensure the route is included in the FastAPI app (`app.include_router(input_router)`).
  </action>
  <verify>
    <automated>curl -s -X POST http://localhost:8000/input -H "Content-Type: application/json" -d '{"type":"zip","payload":{"filename":"test.zip"}}' -o /dev/null && echo "OK"</automated>
  </verify>
  <done>FastAPI `/input` endpoint correctly dispatches to each processor and returns JSON.</done>
</task>

<task type="auto">
  <name>Task 6 – Security validation utilities</name>
  <files>backend/security/validation.py</files>
  <action>
    Implement:
    - `validate_repository_url(url: str, allowed_hosts: List[str]) -> None` that parses the URL, ensures scheme is HTTPS, host is in `allowed_hosts`, and rejects suspicious patterns (e.g., `..`, `127.0.0.1`, `file://`).  
    - `load_secret(name: str) -> str` helper that reads from `os.getenv` and raises `RuntimeError` if missing.
    Add unit tests for both helpers covering valid/invalid cases.
  </action>
  <verify>
    <automated>pytest -q tests/backend/security/test_validation.py</automated>
  </verify>
  <done>Security helpers enforce URL validation and secret loading without hard‑coded values.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary                | Description                               |
|------------------------|-------------------------------------------|
| Frontend → Backend API | Untrusted user payload (zip file, URLs) |
| Backend → External Git   | Network request to GitHub/Gitee          |
| Backend → File System  | Extraction of zip & local directory access|

## STRIDE Threat Register

| Threat ID | Category | Component               | Disposition | Mitigation Plan |
|-----------|----------|--------------------------|-------------|-----------------|
| T-01      | Spoofing | `/input` endpoint       | mitigate    | Validate repository URLs, enforce HTTPS, reject non‑allowed hosts. |
| T-02      | Tampering| Zip extraction         | mitigate    | Use safe extraction (`os.path.normpath`) to prevent path traversal. |
| T-03      | Information Disclosure | Secrets handling | mitigate | Load all secrets exclusively from environment variables via `load_secret`. |
| T-04      | Denial of Service | Git clone subprocess | mitigate | Timeout subprocess, limit clone depth, validate URL before cloning. |
</threat_model>

<verification>
- Run all unit tests (`pytest -q`).  
- Manually test the FastAPI route with cURL for each input type.  
- Verify that no environment variable is hard‑coded (grep for literal strings).  
- Ensure the Docker image (once built) does not contain secret values (`docker run ... env`).
</verification>

<success_criteria>
- ✅ Zip upload extracts correctly and returns a valid path.  
- ✅ GitHub URL clones the repo securely after validation.  
- ✅ Gitee URL clones the repo securely after validation.  
- ✅ Local path is accepted and returned.  
- ✅ All secret values are read from `os.getenv`; no hard‑coded credentials exist.  
- ✅ SSRF protection blocks malicious URLs.  
- ✅ Automated tests for each handler pass (`pytest` ≥ 80 % coverage of input module).  
- ✅ FastAPI `/input` endpoint returns 200 on success and 400 on validation failure.
</success_criteria>

<output>
After completion, create `.planning/phases/01-input-security/01-01-PLAN.md` (this file) and add a corresponding `01-01-PLAN-SUMMARY.md` summarising the implemented artifacts.
</output>