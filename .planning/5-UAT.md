---
name: Phase 5 UAT
description: User Acceptance Tests for Frontend UI
type: uat
---

# Phase 5 UAT

## Current Assessment

Phase 5 basic functionality is ready for user black-box testing. This pass intentionally does not focus on visual polish.

2026-06-12 update: black-box feedback about missing progress visibility and high token cost has been addressed.

## Implemented Scope

- Frontend supports Zip, local path, GitHub URL, and Gitee URL submission controls.
- Frontend renders backend-generated G6 graph data.
- Frontend loads project file list from `/projects/{project_id}/files`.
- Frontend can search files by path/language.
- Frontend can open source content from `/projects/{project_id}/files/content`.
- Clicking a diagram node with a `path` selects and loads the corresponding source file.
- Search and selected file state are reflected in diagram node highlighting.
- Frontend now creates background parsing jobs and polls `/input/jobs/{job_id}` for real-time progress.
- Backend emits detailed logs for input processing, parsing progress, AI explanation selection, and diagram generation.
- AI explanation defaults to Qianwen (`qwen-plus`) and is bounded by file and character budgets.

## Verification Snapshot

| Test ID | Description | Actual Result | Status |
|---------|-------------|---------------|--------|
| 1 | Backend exposes project file list | Covered by automated tests | Pass |
| 2 | Backend reads selected source content | Covered by automated tests | Pass |
| 3 | Backend rejects file path traversal | Covered by automated tests | Pass |
| 4 | Frontend production build | `npm run build` passed | Pass |
| 5 | Full backend test suite | `22 passed, 2 skipped` | Pass |
| 6 | Zip background job progress | Covered by automated tests and large zip pre-check | Pass |
| 7 | Qianwen real API integration | `4 passed, 1 skipped` with `RUN_QIANWEN_INTEGRATION=1` | Pass |
| 8 | User black-box browser test | Awaiting user test | Pending |

## Known Limits Before Black-Box Test

- Browser plugin in this environment returned `ERR_BLOCKED_BY_CLIENT` for localhost, so visual screenshot verification was not completed here.
- UI has now received a visual polish pass, but user-side browser black-box review is still pending.
- GitHub/Gitee real network clone still depends on external network availability.
- Qianwen is now the default AI provider. DeepSeek support remains available by setting `LLM_PROVIDER=deepseek`.
- In-app Browser plugin startup was retried on 2026-06-12; the plugin file exists, but local dev server process startup is unstable in the restricted shell, so UI automation was not completed in this pass.

## Visual Polish Pass 2026-06-12

Implemented:

- Rebuilt the Vue shell into a dark graph-workbench layout with a hero/status band, parser controls, file index, graph canvas, and source preview visible as one cohesive workspace.
- Replaced damaged Chinese UI copy with readable Chinese labels, empty states, errors, progress stages, and helper text.
- Improved input controls with labeled fields, clearer tab states, keyboard focus rings, larger touch targets, and responsive mobile/tablet breakpoints.
- Restyled job progress with stage, message, percent, and progress bar treatment so large-project parsing feels active instead of frozen.
- Upgraded the G6 diagram surface with dark grid canvas, larger rounded nodes, type-aware node styling, selected/search highlights, edge labels, hover state, and resize handling.
- Updated the browser title from `ReArtFlow Diagram Test` to `ReActFlow`.

Verification:

- `npm run build` -> passed, with only the known G6 chunk-size warning.
- Frontend mojibake scan across `frontend/src` and `frontend/index.html` -> no matches.
- Local Vite dev server responded with HTTP 200 at `http://127.0.0.1:5173`.

Open verification gap:

- In-app Browser connection failed during screenshot/DOM verification with a native pipe disconnect after reconnect. Visual browser QA still needs a user-side black-box pass.

## AI Architecture Relationship Pass 2026-06-13

Implemented:

- Added an AI architecture graph pass after file-level explanations. It sends a compact project snapshot to the configured LLM, defaulting to Qianwen.
- The AI graph response is expected to contain structured `groups`, `nodes`, and `edges`, including file paths, node shapes, module colors, descriptions, and relationship types.
- Backend validation filters AI nodes that reference nonexistent paths, drops edges whose endpoints are invalid, and adds `项目 -> 模块 -> 文件` containment edges so the graph remains connected.
- Static fallback graph now classifies files into API, UI, database, config, test, service, and document roles, with different `shape` values.
- Frontend G6 rendering now draws database files as cylinder-style nodes and uses different shapes/colors for API, UI, config, test, service, module, and system nodes.
- Relationship rendering now supports colored and dashed edges for routes, rendering, read/write, config, tests, imports, calls, dependencies, service, and storage semantics.

Verification:

- `.\.venv\Scripts\python.exe -m pytest -q` -> 28 passed, 2 skipped.
- `npm run build` -> passed, with only the known G6 chunk-size warning.

Open verification gap:

- A real Qianwen end-to-end repository run still requires `QIANWEN_API_KEY` and user-side black-box review.

## Pre-Black-Box Zip Test 2026-06-11

Test input: `Chinese-Traditional-Culture.zip`

Result:

- Zip upload endpoint returned 200.
- Generated project id: `3b2b80a75cc349c2bc6140c361ca667e`.
- Generated graph: 2042 nodes / 2041 edges.
- Project file list: 215 files.
- Source read sample: `backend/check_all_tables.py`, 641 characters, language `Python`.

Automation notes:

- Browser plugin could not be used in this local session because `browser-client.mjs` is missing from the installed Browser plugin package.
- Computer Use fallback was attempted, but initialization failed with an internal `@oai/sky` package export error.
- Because both UI automation plugins were unavailable, this pre-check used FastAPI `TestClient` against the same `/input/zip`, `/projects/{project_id}/files`, and `/projects/{project_id}/files/content` paths that the frontend calls.

## Black-Box Feedback Fix Verification 2026-06-12

GitDiagram reference:

- GitDiagram filters noisy dependency folders, uses repository snapshots instead of sending every file wholesale, stores generated artifacts, and uses quota state for cost control.
- ReActFlow adopted the same core direction for this phase: static graph first, limited LLM enrichment second.

Implemented cost controls:

- `node_modules`, `.git`, `.venv`, `dist`, `build`, `.next`, `.vite`, `coverage`, and cache folders are excluded from parser input.
- `LLM_MAX_FILES` limits how many files can call AI.
- `LLM_MAX_CHARS_PER_FILE` limits each AI request size.
- `LLM_MAX_TOTAL_CHARS` limits total AI input per project.
- If no API Key is configured, the system skips AI and still returns a static graph.

Large zip job pre-check:

- Test input: `Chinese-Traditional-Culture.zip`.
- Endpoint: `POST /input/zip/jobs`, polled through `GET /input/jobs/{job_id}`.
- AI disabled with `LLM_MAX_FILES=0`.
- Result: ready.
- Parsed project files after dependency filtering: 19.
- Generated graph: 73 nodes / 72 edges.
- Observed progress messages included `正在处理输入`, `正在扫描源码文件`, and `流程图生成完成`.

Verification commands:

- `.\.venv\Scripts\python.exe -m pytest -q` -> 22 passed, 2 skipped.
- `npm run build` -> passed, with only the known G6 chunk-size warning.
- Qianwen real API test -> 4 passed, 1 skipped.

## GitDiagram-Style Retest 2026-06-12

Implemented:

- Graph shape changed from file inventory to Chinese architecture overview.
- New graph metadata includes `groups`, compact `nodes`, and bounded `edges`.
- Node labels are Chinese-friendly: `项目概览`, `backend 子系统`, `frontend 子系统`, `核心文件`.
- Resource/data files are filtered from parsing and file browsing: images, CSV/Excel, archives, fonts, PDFs, and media.

Large zip retest:

- Test input: `Chinese-Traditional-Culture.zip`.
- AI disabled with `LLM_MAX_FILES=0`.
- Result: ready.
- Generated graph: 13 nodes / 12 edges / 3 groups.
- CSV/image nodes: none.

Verification commands:

- `.\.venv\Scripts\python.exe -m pytest -q` -> 25 passed, 2 skipped.
- `npm run build` -> passed, with only the known G6 chunk-size warning.
