# ROADMAP

## Phases

- [ ] **Phase 1: Input & Security Handling** - Status: In Progress. Basic handlers exist, but route registration and end-to-end integration do not yet match the planned API.
- [ ] **Phase 2: Multi-language Code Parsing** - Status: In Progress. Current parser is a placeholder and does not yet provide real Tree-sitter-based structure extraction.
- [ ] **Phase 3: AI Semantic Understanding** - Status: Blocked. Semantic layer currently fails under missing optional imports and has a primary return-path bug.
- [ ] **Phase 4: Diagram Generation** - Status: In Progress. Diagram API and frontend rendering exist at demo level, but correctness and delivery gaps remain.
- [ ] **Phase 5: Frontend UI** - Status: Pending. Demo rendering exists, but search, file tree, and code-explanation linkage are not yet implemented end-to-end.
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
