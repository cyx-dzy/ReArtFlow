---
phase: "Phase 2"
plan: "01"
type: execute
wave: 1
depends_on: []                 # Phase 1 must be completed first
files_modified:
  - backend/parser/__init__.py
  - backend/parser/tree_sitter_pool.py
  - backend/parser/models.py
autonomous: true
requirements:
  - PAR-01
  - PAR-02
  - PAR-03
  - PAR-04
must_haves:
  truths:
    - "Parser supports at least 20 mainstream languages (Python, JavaScript/TypeScript, Java, Go, Rust, C/C++, …)."
    - "For every source file the parser extracts functions, classes, imports and call relationships."
    - "Each parsed file includes metadata fields `size`, `mtime` and `parse_time_ms`."
    - "File parsing is performed in parallel, giving ≥30 % total‑parse‑time reduction versus sequential parsing."
    - "The JSON output conforms exactly to the downstream schema defined in `backend/schemas/parse_output.json`."
  artifacts:
    - path: "backend/parser/__init__.py"
      provides: "Public API `parse_project(source_path: str) -> List[ParsedFile]`"
    - path: "backend/parser/tree_sitter_pool.py"
      provides: "Thread‑local `Parser` pool and helper `parse_file(path: str) -> ParsedFile`"
    - path: "backend/parser/models.py"
      provides: "`ParsedFile` Pydantic model with fields `path`, `size`, `mtime`, `parse_time_ms`, `language`, `ast_summary`"
  key_links:
    - from: "backend/parser/__init__.py"
      to: "backend/parser/tree_sitter_pool.py"
      via: "`parse_file` import"
      pattern: "from .tree_sitter_pool import parse_file"
    - from: "backend/parser/__init__.py"
      to: "backend/schemas/parse_output.json"
      via: "JSON serialization of `ParsedFile` list"
      pattern: "json.dumps([pf.dict() for pf in parsed_files])"
---

<objective>
Implement the multi‑language code parsing layer (Phase 2) that extracts language‑agnostic structure and required metadata from all supported source files, and returns a validated JSON model ready for downstream AI‑semantic and diagram services.
</objective>

<execution_context>
@/root/project/ReArtFlow/.planning/PROJECT.md
@/root/project/ReArtFlow/.planning/REQUIREMENTS.md
@/root/project/ReArtFlow/.planning/ROADMAP.md
@/root/project/ReArtFlow/.planning/research/PARSE.md
</execution_context>

<context>
# Existing architecture
The backend is a FastAPI service (see PROJECT.md). Parsing must be exposed via a non‑blocking endpoint that returns a task‑ID and allows polling for results.

# Tree‑sitter bindings
`py-tree-sitter` is the recommended Python binding (research confirms thread‑safety when each thread owns its own `Parser` instance).

# Concurrency model
Use `concurrent.futures.ThreadPoolExecutor` (research §5) with a configurable worker count (default = CPU cores * 2).

# JSON schema
`backend/schemas/parse_output.json` defines the required output format (paths, size, mtime, parse_time_ms, language, ast‑summary). The schema is validated with Pydantic (already used elsewhere in the project).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build language library and expose thread‑local parser pool</name>
  <files>backend/parser/tree_sitter_pool.py</files>
  <action>
    1. Add a `build_languages()` helper that calls `Language.build_library("build/my‑languages.so", [...paths to vendor parsers...])`. Include the 20 + official grammars listed in the research table (Python, JavaScript/TS, Java, Go, Rust, C/C++, …).  
    2. Create a module‑level `ThreadLocal` object that on first access instantiates a `Parser` and sets its language via `Language("build/my‑languages.so", <lang>)`.  
    3. Provide a `parse_file(path: str) -> ParsedFile` function that:
       - Reads the file bytes, records `size` (`os.stat().st_size`) and `mtime` (`os.stat().st_mtime`).
       - Starts a high‑resolution timer, parses with the thread‑local `Parser`, stops timer → `parse_time_ms`.
       - Walks the CST to collect function, class, import and call nodes (using `tree_sitter.Query` patterns defined per language).
       - Returns a `ParsedFile` instance (see Task 2 model).
    4. Add a small unit test `tests/parser/test_tree_sitter_pool.py` that parses a tiny Python fixture and asserts the three metadata fields are present and non‑negative.
  </action>
  <verify>
    <automated>pytest tests/parser/test_tree_sitter_pool.py -q</automated>
  </verify>
  <done>
    A thread‑local parser pool exists, language library built, and `parse_file` returns a fully‑populated `ParsedFile` for at least one language.
  </done>
</task>

<task type="auto">
  <name>Task 2: Implement bulk parallel parsing service and metadata model</name>
  <files>
    backend/parser/__init__.py,
    backend/parser/models.py,
    backend/api/parse_endpoint.py
  </files>
  <action>
    1. Define a Pydantic model `ParsedFile` (path, size, mtime, parse_time_ms, language, ast_summary) in `models.py`. `ast_summary` can be a lightweight dict of counts (functions, classes, imports, calls).  
    2. In `backend/parser/__init__.py` expose `parse_project(source_path: str) -> List[ParsedFile]` that:
       - Walks the directory tree, filters files by extensions supported by the built language library.
       - Submits each file to a `ThreadPoolExecutor` using `parse_file`.
       - Collects results, sorts by path, and returns the list.
    3. Add a FastAPI endpoint `POST /parse` in `parse_endpoint.py`:
       - Accepts a JSON body `{ "source_path": "..."}`.
       - Calls `parse_project` inside `BackgroundTasks` to avoid blocking the event loop.
       - Returns `{ "task_id": "<uuid>" }` immediately.
       - Store intermediate results in an in‑memory dict keyed by `task_id`; expose a `GET /parse/{task_id}` to poll for the final JSON payload.
    4. Validate the final JSON against `backend/schemas/parse_output.json` using `pydantic.validate_model`.
    5. Add integration tests `tests/api/test_parse_endpoint.py` that:
       - Sends a small sample repository (included under `tests/fixtures/sample_repo`) to the endpoint.
       - Polls until status `completed`.
       - Asserts the response JSON contains `size`, `mtime`, `parse_time_ms` for every file and that at least 20 languages are reported when the fixture includes them.
  </action>
  <verify>
    <automated>pytest tests/api/test_parse_endpoint.py -q</automated>
  </verify>
  <done>
    Parallel parsing service returns a validated JSON array of `ParsedFile` objects for all files, and the FastAPI route works without blocking the event loop.
  </done>
</task>

<task type="auto">
  <name>Task 3: Benchmark parallel parsing performance and enforce speed criteria</name>
  <files>backend/benchmark/parse_perf.py</files>
  <action>
    1. Create a benchmarking script that:
       - Generates a synthetic repository of ~10 000 files across the 20 supported languages (use `tests/fixtures/large_repo_generator.py`).
       - Measures total wall‑clock time for `parse_project` with `max_workers=1` (sequential) and with `max_workers=cpu_count()*2` (parallel).
       - Prints both durations and the percentage speed‑up.
    2. Add an assertion that the parallel run must be at least 30 % faster than the sequential run; fail the script otherwise.
    3. Include this script in the CI pipeline (via `ci/benchmark.yml`) so that regression in parsing speed is caught early.
    4. Verify that the script exits with code 0 on the current codebase.
  </action>
  <verify>
    <automated>python backend/benchmark/parse_perf.py --assert-speedup 30</automated>
  </verify>
  <done>
    Benchmark confirms ≥30 % speed improvement; CI will fail if future changes drop below this threshold.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary                | Description                                    |
|------------------------|------------------------------------------------|
| User‑provided source   | Zip upload, GitHub/Gitee URLs, local path.      |
| Parsing subsystem      | Tree‑sitter library handling untrusted code.   |
| FastAPI endpoint       | Receives source identifiers & returns JSON.    |

## STRIDE Threat Register

| Threat ID | Category | Component               | Disposition | Mitigation Plan |
|-----------|----------|--------------------------|-------------|-----------------|
| T-02-01   | Spoofing | FastAPI `/parse` input  | mitigate    | Validate `source_path` format; reject absolute paths outside allowed sandbox directory; limit file count (max 10 000). |
| T-02-02   | Tampering| Tree‑sitter parser       | mitigate    | Run each parser in a separate thread with a hard timeout (`parser.set_timeout(5000)`); catch `TreeSitterError` and return structured error. |
| T-02-03   | DoS      | Parallel worker pool     | mitigate    | Cap `max_workers` to `cpu_count()*2`; enforce per‑file size limit (≤5 MB) before parsing; reject overly large archives. |
| T-02-04   | Information Disclosure | JSON output | accept | Output only metadata and AST summaries; no raw source code is emitted; restrict endpoint to authenticated callers. |
| T-02-05   | Elevation of Privilege | Environment | mitigate | Ensure parser runs with non‑root user in Docker container; no elevated OS capabilities required. |
</threat_model>

<verification>
Overall Phase Verification
- Run the full integration test suite (`pytest -q`) and ensure all new tests pass.
- Manually invoke the `/parse` endpoint with a real GitHub repo (e.g., `https://github.com/example/mini-project`) and verify:
  * JSON contains `size`, `mtime`, `parse_time_ms` for each file.
  * At least 20 languages are reported.
  * Total parse time is ≤ 70 % of the sequential baseline (as measured by the benchmark script).
- Execute the performance benchmark script; it must exit with status 0 confirming ≥30 % speed‑up.
</verification>

<success_criteria>
- ✔ Parser supports ≥20 languages (Python, JS/TS, Java, Go, Rust, C/C++, …).  
- ✔ Each file’s metadata (`size`, `mtime`, `parse_time_ms`) is present and correctly typed.  
- ✔ Parallel parsing yields ≥30 % reduction vs sequential parsing (benchmark confirmed).  
- ✔ JSON output matches `backend/schemas/parse_output.json` and is accepted by downstream AI‑semantic service.  
- ✔ No security violations: inputs validated, timeouts enforced, worker pool limited.  
- ✔ All new unit, integration, and benchmark tests pass (≥80 % total coverage).  
</success_criteria>

<output>
After completion, create `.planning/phases/02-parse/02-01-PLAN.md` (this file) and a corresponding `02-01-PLAN-SUMMARY.md` summarising the implementation outcome.
</output>