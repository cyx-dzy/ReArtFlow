# ROADMAP

## Phases

- [ ] **Phase 1: Input & Security Handling** - Enable secure source input (zip, GitHub, Gitee, local) with validation.
- [ ] **Phase 2: Multi-language Code Parsing** - Extract code structure and metadata across 20+ languages with parallel processing.
- [ ] **Phase 3: AI Semantic Understanding** - Generate Chinese explanations and dependency reasoning via LLM.
- [ ] **Phase 4: Diagram Generation** - Convert JSON graph to Mermaid and interactive AntV G6 diagrams with proper Chinese rendering.
- [ ] **Phase 5: Frontend UI** - Provide Vue3 SPA for interactive diagram navigation, search, and code‑explanation linking.
- [ ] **Phase 6: Deployment & Operations** - Containerized deployment with Docker Compose, horizontal scaling, and health checks.

## Phase Details

### Phase 1: Input & Security Handling
**Goal**: Users can provide code sources securely and the system processes them safely.
**Depends on**: Nothing (first phase)
**Requirements**: INP-01, INP-02, INP-03, INP-04, SEC-01, SEC-02, SEC-03
**Success Criteria** (what must be TRUE):
  1. User can upload a local Zip file and the system extracts it correctly.
  2. User can enter a GitHub URL and the system clones the repository.
  3. User can enter a Gitee URL and the system clones the repository.
  4. User can specify a local filesystem path and the system parses it directly.
  5. System validates repository URLs to prevent SSRF and reads all secrets from environment variables only.
**Effort**: Medium
**Plans**: TBD

### Phase 2: Multi-language Code Parsing
**Goal**: System extracts a rich, language‑agnostic code model from the provided sources.
**Depends on**: Phase 1
**Requirements**: PAR-01, PAR-02, PAR-03, PAR-04
**Success Criteria**:
  1. Parser supports at least 20 mainstream languages (including Python, JavaScript/TypeScript, Java, Go, Rust, C/C++).
  2. For each file the parser extracts functions, classes, imports and call relationships.
  3. Metadata fields `size`, `mtime` and `parse_time_ms` are recorded for every file.
  4. Files are parsed in parallel, achieving ≥30% reduction in total parse time versus sequential parsing.
  5. The output JSON conforms to the agreed schema for downstream services.
**Effort**: High
**Plans**: TBD

### Phase 3: AI Semantic Understanding
**Goal**: Users receive clear Chinese explanations and dependency reasoning for the extracted code model.
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria**:
  1. LLM produces coherent Chinese description for each extracted function/module.
  2. Dependency reasoning is generated in natural language and accurately reflects the call graph.
  3. Model selection can be switched between OpenAI/Sonnet and Haiku via configuration without code changes.
  4. Semantic generation latency stays below 2 seconds per 100 lines of code.
**Effort**: Medium
**Plans**: TBD

### Phase 4: Diagram Generation
**Goal**: Users can view an interactive visual diagram of the code dependencies.
**Depends on**: Phase 3
**Requirements**: VIS-01, VIS-02, VIS-03
**Success Criteria**:
  1. JSON dependency graph is correctly transformed into valid Mermaid syntax.
  2. Mermaid diagrams render Chinese characters using Noto Sans SC / Source Han Sans fonts without garbling.
  3. AntV G6 renders an equivalent interactive diagram that supports zoom, pan and node selection.
  4. The diagram can be fetched via the API and displayed in the frontend without errors.
**Effort**: Medium
**Plans**: TBD

### Phase 5: Frontend UI
**Goal**: Users can explore the generated diagrams, search, and view code‑explanation links.
**Depends on**: Phase 4
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria**:
  1. Vue3 + Vite SPA loads and displays the diagram page.
  2. File‑structure tree allows navigation and clicking a node shows the associated source code and AI explanation.
  3. Search functionality highlights matching nodes and clicking a result jumps to the node view.
  4. UI is responsive and works across major browsers (Chrome, Firefox, Edge).
**Effort**: High
**Plans**: TBD
**UI hint**: yes

### Phase 6: Deployment & Operations
**Goal**: System can be deployed reliably and scaled horizontally.
**Depends on**: Phase 5
**Requirements**: DEP-01, DEP-02, DEP-03
**Success Criteria**:
  1. Docker Compose starts both backend (FastAPI) and frontend services without errors.
  2. Multiple backend instances can be launched and load‑balanced via the provided configuration.
  3. Health‑check endpoint `/health` returns HTTP 200 within 1 second.
  4. All secrets are supplied through environment variables; no hard‑coded credentials exist in the repository.
**Effort**: Low/Medium
**Plans**: TBD
