# ROADMAP

## Phases

- [ ] **Phase 1: Input & Security Handling** - Status: In Progress. Basic handlers exist, but route registration and end-to-end integration do not yet match the planned API.
- [ ] **Phase 2: Multi-language Code Parsing** - Status: In Progress. Parser now prefers Tree-sitter and falls back to deterministic summaries when grammar ABI versions are incompatible.
- [ ] **Phase 3: AI Semantic Understanding** - Status: In Progress. Qianwen is now the default provider with real API verification; DeepSeek remains configurable.
- [ ] **Phase 4: Diagram Generation** - Status: In Progress. Local/Zip input now generates retrievable real G6/Mermaid diagram data; GitHub/Gitee manual browser verification remains.
- [ ] **Phase 5: Frontend UI** - Status: Ready for Visual Black-Box Retest. Frontend now has input controls, job progress polling, graph rendering, file list, search, node click linkage, source viewing, and a polished graph-workbench layout.
- [ ] **Phase 6: Deployment & Operations** - Status: Pending. Health endpoint exists, but Docker/frontend delivery and scaling are not ready.

## Phase Details

### Phase 1: Input & Security Handling
**Goal**: Users can provide code sources securely and the system processes them safely.
**Depends on**: Nothing (first phase)
**Requirements**: INP-01, INP-02, INP-03, INP-04, SEC-01, SEC-02, SEC-03
**Current Status**: In Progress
**Reality Check**:
  1. Zip, GitHub, Gitee, and local input handlers exist in code.
  2. Security validation utilities also exist in code.
  3. Actual API registration does not match planning paths exactly, so the phase is not yet verifiably complete.
**Effort**: Medium
**Plans**: Reconcile router registration with planned public endpoints and rerun input-path verification.

### Phase 2: Multi-language Code Parsing
**Goal**: System extracts a rich, language-agnostic code model from the provided sources.
**Depends on**: Phase 1
**Requirements**: PAR-01, PAR-02, PAR-03, PAR-04
**Current Status**: In Progress
**Reality Check**:
  1. Current implementation identifies language mainly by file extension.
  2. Current implementation is a simplified placeholder rather than a real Tree-sitter parser.
  3. Function/class/import/call extraction is not yet delivered to requirement level.
  4. Metadata and parallel scaffolding exist, but the core parser requirement is still unmet.
**Effort**: High
**Plans**: Replace placeholder parser with real Tree-sitter-backed extraction and then re-evaluate Phase 2 completion.

### Phase 3: AI Semantic Understanding
**Goal**: Users receive clear Chinese explanations and dependency reasoning for the extracted code model.
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03
**Current Status**: Blocked
**Reality Check**:
  1. `backend/semantic/llm_client.py` contains import-time dependency issues.
  2. `generate_explanation()` has a primary-path return bug that can prevent successful results from being returned.
  3. Until the semantic layer is made stable, downstream phases cannot be considered production-ready.
**Effort**: Medium
**Plans**: Fix import behavior and return-path bug before claiming Phase 3 progress.

### Phase 4: Diagram Generation
**Goal**: Users can view an interactive visual diagram of the code dependencies.
**Depends on**: Phase 3
**Requirements**: VIS-01, VIS-02, VIS-03
**Current Status**: In Progress
**Reality Check**:
  1. `GET /diagram/{project_id}` currently returns demo-usable graph data.
  2. Frontend rendering exists and can display an interactive graph.
  3. Graph conversion still has correctness issues and cannot be treated as fully verified.
  4. Because Phase 3 is blocked, current diagram output should be treated as demo-level rather than completed feature work.
**Effort**: Medium
**Plans**: Fix graph conversion bugs and reconnect diagram generation to a real parser + stable semantic pipeline.

### Phase 5: Frontend UI
**Goal**: Users can explore the generated diagrams, search, and view code-explanation links.
**Depends on**: Phase 4
**Requirements**: UI-01, UI-02, UI-03
**Current Status**: Pending
**Reality Check**:
  1. Vue3 + Vite scaffolding exists.
  2. Current `App.vue` is still demo-oriented and not wired to the full backend workflow.
  3. File tree, explanation linkage, search, highlight, and source navigation are not yet complete.
**Effort**: High
**Plans**: Convert demo UI into a real data-driven application after backend correctness issues are resolved.

### Phase 6: Deployment & Operations
**Goal**: System can be deployed reliably and scaled horizontally.
**Depends on**: Phase 5
**Requirements**: DEP-01, DEP-02, DEP-03
**Current Status**: Pending
**Reality Check**:
  1. `/health` endpoint exists.
  2. `docker-compose.yml` references a frontend build path that is not currently complete for delivery.
  3. Horizontal scaling is not yet implemented or verified.
**Effort**: Low/Medium
**Plans**: Complete frontend containerization and only then verify Compose startup and scaling configuration.

## Repair Update 2026-06-11

- `POST /input` now runs input processing, project parsing, diagram construction, and stores graph data under a generated `project_id`.
- `POST /input/zip` accepts raw zip bytes without requiring `python-multipart`.
- `GET /diagram/{project_id}` now returns stored diagram data and returns 404 for unknown projects instead of demo placeholders.
- `frontend/src/App.vue` now submits real inputs and renders returned G6 graph data.
- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` -> 18 passed, 1 skipped; `npm run build` -> passed.
- Manual HTTP verification produced a real graph from the backend directory: 103 nodes / 102 edges.

## Phase 5 Update 2026-06-11

- Added `/projects/{project_id}/files` and `/projects/{project_id}/files/content`.
- Added frontend file list, search, selected source viewer, diagram node click linkage, and node highlighting by search/selection.
- This pass intentionally does not polish page aesthetics; it is for basic functional black-box testing.
- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` -> 20 passed, 1 skipped; `npm run build` -> passed.

## Phase 5 Black-Box Feedback Fix 2026-06-12

- Added async job endpoints for input parsing progress: `/input/jobs`, `/input/zip/jobs`, and `/input/jobs/{job_id}`.
- Frontend now displays real-time progress while parsing large Zip projects.
- Backend now logs input, parsing, AI, and diagram generation stages.
- Default AI provider switched to Qianwen (`qwen-plus`); real Qianwen API test passed.
- Token cost is controlled by dependency-directory filtering and LLM budgets (`LLM_MAX_FILES`, `LLM_MAX_CHARS_PER_FILE`, `LLM_MAX_TOTAL_CHARS`).
- GitDiagram reference used: filter noisy repo content, generate from compact repository structure, persist artifacts, and enforce quota/budget controls.
- Large `Chinese-Traditional-Culture.zip` pre-check now excludes `node_modules`, parses 19 project files, and generates 73 nodes / 72 edges.
- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` -> 22 passed, 2 skipped; `npm run build` -> passed.

## GitDiagram-Style Diagram Update 2026-06-12

- Diagram output now follows a Chinese GitDiagram-inspired overview style: project overview, subsystem groups, and key file nodes.
- Graph construction is bounded to avoid inventory-like diagrams: max 8 groups, 34 nodes, and 48 edges.
- Resource/data files such as images, CSV/Excel files, archives, fonts, PDFs, and media are excluded from parsing and file browsing.
- Large zip pre-check now produces 13 nodes / 12 edges / 3 groups, with no CSV/image nodes.
- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` -> 25 passed, 2 skipped; `npm run build` -> passed.

## Phase 5 Visual Polish Update 2026-06-12

- Reworked the frontend into a cohesive dark graph-workbench UI with parser controls, progress, file index, graph canvas, and source preview arranged for scanning and repeated use.
- Replaced damaged Chinese interface copy with readable labels, empty states, progress stages, and error text.
- Improved accessibility and responsiveness with visible labels, focus rings, larger controls, mobile/tablet breakpoints, and reduced-motion handling.
- Restyled the G6 graph canvas with dark grid background, type-aware nodes, selected/search highlights, hover states, better edge labels, and resize handling.
- Verified `npm run build` passes; local dev server returned HTTP 200. In-app Browser screenshot QA is still pending because the browser connection disconnected during verification.

## AI Architecture Relationship Update 2026-06-13

- Added a GitDiagram-style graph pipeline: static parsing builds a compact project snapshot, Qianwen can generate structured `groups` / `nodes` / `edges`, and the backend validates paths and edge endpoints before rendering.
- Diagram nodes now carry `shape`, `color`, `type`, `language`, `description`, and `groupId` metadata so modules can be grouped and files can be drawn as database/API/UI/config/test/service shapes.
- Relationship labels now include `routes_to`, `renders`, `reads_writes`, `configures`, `tests`, `imports`, `calls`, `depends_on`, `serves`, and `stores` instead of only call-like edges.
- Frontend G6 rendering now supports database cylinder nodes, API diamond nodes, UI ellipses, service circles, relation-colored edges, dashed config/test edges, and selected/search highlighting.
- Added `LLM_ARCHITECTURE_ENABLED` for turning the AI architecture pass on/off while preserving static fallback behavior.
- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` -> 28 passed, 2 skipped; `npm run build` -> passed with the known G6 chunk-size warning.
