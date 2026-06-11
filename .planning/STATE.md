---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: phase 1-4 repair implementation (2026-06-11)
last_updated: "2026-06-12T00:00:00+08:00"
last_activity: Phase 5 black-box feedback fixes: progress visibility, Qianwen switch, and cost control
progress:
  percent: 72
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-22)

**Core value:** 为非技术人员快速了解跨语言项目结构，提供中文思维导图展示代码调用关系。
**Current focus:** Phase 3 unblock + Phase 2 parser replacement

## Current Position

Phase: Between 2 and 4 (parser prototype complete, semantic layer blocked, diagram layer demo-only)
Plan: Corrective backfill in progress
Status: Blocked pending backend fixes
Last activity: Reconciled planning state against actual codebase behavior

Progress: [███░░░░░░░] 35%

## Reality Summary

- Phase 1 has basic input and validation scaffolding, but route registration and integration do not yet fully match the planned public API.
- Phase 2 is not yet a real Tree-sitter implementation; current parsing remains placeholder-level.
- Phase 3 is blocked by semantic-layer import/runtime issues and must be fixed before downstream work can be considered stable.
- Phase 4 has demo-capable diagram output and frontend rendering, but not production-ready correctness or delivery.

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: N/A
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1-4 (mixed prototype work) | 0 | 0 | N/A |

## Accumulated Context

### Decisions

- Planning state must reflect actual code behavior rather than intended phase progression.
- Phase 3 should be treated as the current hard blocker.
- Phase 4 should be documented as demo-level only until parser and semantic dependencies are stabilized.

### Pending Todos

- Fix API route registration to match planned public endpoints.
- Replace placeholder parser with real Tree-sitter-based extraction.
- Repair semantic layer import behavior and return-path bug.
- Fix diagram edge conversion bug.
- Re-verify Docker/frontend delivery path.

### Blockers/Concerns

- Semantic layer currently fails in common environments due to import/runtime issues.
- Parsing layer does not yet meet Phase 2 requirement depth.
- Frontend and Docker delivery path remain incomplete for production or UAT signoff.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Phase 5 | Search / file tree / explanation linkage | Deferred pending backend correctness | 2026-05-11 |
| Phase 6 | Horizontal scaling verification | Deferred pending working frontend container | 2026-05-11 |

## Session Continuity

Last session: 2026-05-11 corrective audit
Stopped at: planning state corrected to match actual repository status
Resume file: None

## Repair Update 2026-06-11

- Added `PHASE1_TO_PHASE4_REPAIR_PLAN.md` as the local execution plan.
- Backend tests now pass locally: `18 passed, 1 skipped`.
- Frontend `npm run build` now passes; the remaining warning is G6 bundle size.
- `/input` local path flow now creates a `project_id`, stores a real diagram, and `/diagram/{project_id}` returns stored Mermaid/G6 data.
- Manual HTTP verification against `D:\project\ReActFlow\backend` produced 103 nodes and 102 edges, with no legacy demo nodes such as `模块一`.
- Parser now prefers Tree-sitter and falls back to deterministic regex summaries when local Tree-sitter grammar ABI versions are incompatible.
- Semantic layer now has a DeepSeek text-provider path; real API verification passed with `RUN_DEEPSEEK_INTEGRATION=1` using default model `deepseek-chat`.
- Remaining work: browser-level Zip/GitHub/Gitee validation, Docker Compose recheck, richer symbol/call graph extraction, and optional Phase 5 search/file-tree/source-linking.

## Phase 5 Update 2026-06-11

- Added project file listing and source content APIs under `/projects/{project_id}/files`.
- Frontend now includes a basic file list, file search, source viewer, diagram node click linkage, and search-based node highlighting.
- Phase 5 intentionally avoids visual polish in this pass and focuses on black-box-testable functionality.
- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` -> 20 passed, 1 skipped; `npm run build` -> passed.
- Status: ready for user black-box testing of Phase 5 basics.

## Phase 5 Black-Box Feedback Fix 2026-06-12

- Added background input jobs: `POST /input/jobs`, `POST /input/zip/jobs`, and `GET /input/jobs/{job_id}`.
- Frontend now submits through job endpoints and polls progress every second, showing stage, percent, and current message.
- Backend now logs project input, parsing progress, LLM explanation selection, diagram generation, and job failures.
- Default AI provider is now Qianwen (`LLM_PROVIDER=qianwen`, default model `qwen-plus`).
- Qianwen real API integration test passed with user-provided key: `4 passed, 1 skipped`.
- Added LLM cost controls: `LLM_MAX_FILES`, `LLM_MAX_CHARS_PER_FILE`, and `LLM_MAX_TOTAL_CHARS`.
- Parser now ignores dependency/build directories such as `node_modules`, `.git`, `.venv`, `dist`, and `build`.
- Large zip pre-check with AI disabled now parses 19 project files instead of 789 dependency-heavy files and generates 73 nodes / 72 edges.
- Verified commands: `.\.venv\Scripts\python.exe -m pytest -q` -> 22 passed, 2 skipped; `npm run build` -> passed.
