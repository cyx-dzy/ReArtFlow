---
phase: "Phase 3"
plan: "01"
type: execute
wave: 1
depends_on: []                 # Phase 2 must be completed first
files_modified:
  - backend/semantic/__init__.py          # Public API for AI semantic layer
  - backend/semantic/llm_client.py        # Wrapper supporting OpenAI & Qianwen APIs
  - backend/semantic/prompt_templates.py   # Prompt & CoT templates (Chinese)
  - backend/semantic/cache.py              # Redis / file‑based response cache
  - backend/api/routes/semantic.py         # FastAPI endpoint /semantic
  - backend/semantic/tests/test_semantic.py
autonomous: true
requirements:
  - AI-01
  - AI-02
  - AI-03
must_haves:
  truths:
    - "LLM wrapper can call either OpenAI (gpt‑4o / gpt‑4‑turbo) or Qianwen (千问) API based on configuration."
    - "Prompt templates use few‑shot examples + chain‑of‑thought, and request JSON output via function‑calling (for easy downstream parsing)."
    - "Responses are cached (Redis primary, file‑fallback) keyed by hash(source_code + model_id + prompt_version)."
    - "Generated Chinese explanations are formatted as Mermaid diagram strings and AntV G6 JSON objects, ready for frontend consumption."
    - "All external calls respect token limits: code is chunked to ≤ 2 k tokens, overlapping windows ensure context continuity."
  artifacts:
    - path: "backend/semantic/llm_client.py"
      provides: "Unified LLM client supporting OpenAI and Qianwen, with model selection logic."
    - path: "backend/semantic/prompt_templates.py"
      provides: "Reusable Chinese prompt templates (few‑shot, CoT, function‑call schema)."
    - path: "backend/semantic/cache.py"
      provides: "Cache layer (Redis + JSON file) for LLM responses."
    - path: "backend/api/routes/semantic.py"
      provides: "FastAPI POST /semantic endpoint exposing AI semantic service."
  key_links:
    - from: "backend/api/routes/semantic.py"
      to: "backend/semantic/llm_client.py"
      via: "calls LLM client for code explanation"
    - from: "backend/semantic/llm_client.py"
      to: "backend/semantic/cache.py"
      via: "checks / writes cache before/after remote calls"
---

<objective>
Implement the AI semantic understanding layer (Phase 3). Its purpose is to take the structured parsing output from Phase 2, feed the source code (or AST summary) into a large language model, and obtain Chinese natural‑language explanations plus a mind‑map representation.

Key features:
- Support **OpenAI** (gpt‑4o, gpt‑4‑turbo) and **Qianwen** (千问) APIs via a unified wrapper.
- Use **few‑shot + chain‑of‑thought** prompts that request JSON‑structured output (function‑calling) containing `explanation` and `diagram` fields.
- Enforce **token‑limit handling**: chunk source code, overlapping windows, and summarise before calling the LLM.
- Implement **caching** (Redis primary, fall back to local JSON files) to avoid duplicate calls and reduce cost.
- Return results in two formats: **Mermaid** diagram strings with Chinese labels, and **AntV G6** JSON graph objects.
- Expose a FastAPI endpoint `POST /semantic` that accepts a parsed file list (from Phase 2) and returns the enriched data.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.planning/research/SEMANTIC.md
</execution_context>

<context>
- The LLM client must be configurable via environment variables:
  * `OPENAI_API_KEY` for OpenAI
  * `QIANWEN_API_KEY` for Qianwen
  * `LLM_PROVIDER` = `openai` | `qianwen`
  * `LLM_MODEL` = model name (e.g., `gpt-4o`, `gpt-4-turbo`, `glm-4-0520`) 
- The system should support graceful fallback: if the preferred provider fails, automatically retry with the secondary provider.
</context>

<tasks>

<task type="auto">
  <name>Task 1 – Design unified LLM client</name>
  <files>backend/semantic/llm_client.py</files>
  <action>
    1. Define a class `LLMClient` with methods `generate_explanation(code: str, language: str) -> dict`.
    2. Read env vars (`LLM_PROVIDER`, `LLM_MODEL`) and route the request to either OpenAI (`openai.ChatCompletion.create`) or Qianwen (`requests.post` to its endpoint). Include proper auth headers.
    3. Implement a fallback: on any non‑2xx response, switch to the other provider and retry once.
    4. Use function‑calling schema so the model returns JSON with fields `explanation` (Chinese text) and `diagram` (structured dict).
    5. Add inline documentation and type hints.
  </action>
  <verify>
    <automated>pytest -q tests/semantic/test_llm_client.py</automated>
  </verify>
  <done>LLM client can call both OpenAI and Qianwen, respects provider config, and returns a parsed JSON dict.</done>
</task>

<task type="auto">
  <name>Task 2 – Create prompt templates</name>
  <files>backend/semantic/prompt_templates.py</files>
  <action>
    1. Provide three template strings:
       - `BASE_PROMPT` – generic instruction in Chinese to explain code.
       - `FEW_SHOT_EXAMPLES` – two short examples (function + explanation + diagram) to guide the model.
       - `FUNCTION_CALL_SCHEMA` – JSON schema for the expected output (`explanation`: string, `diagram`: object).
    2. Combine them into a final prompt used by `LLMClient`.
    3. Write a helper `render_prompt(code: str, language: str) -> list[Message]` that returns the list of messages for the API call.
  </action>
  <verify>
    <automated>pytest -q tests/semantic/test_prompt_templates.py</automated>
  </verify>
  <done>Prompt module supplies ready‑to‑use messages for both providers.</done>
</task>

<task type="auto">
  <name>Task 3 – Implement caching layer</name>
  <files>backend/semantic/cache.py</files>
  <action>
    1. Use `redis-py` to connect to Redis (host/port from env `REDIS_URL`).
    2. Provide `get_cached(key)` and `set_cached(key, value, ttl=86400)` helpers.
    3. Fallback to a local JSON file (`.cache/llm_responses.json`) if Redis is unavailable.
    4. Cache key = `hash(code + model_id + prompt_version)`. Store the entire JSON response.
    5. Add unit tests for both Redis‑available and Redis‑missing scenarios.
  </action>
  <verify>
    <automated>pytest -q tests/semantic/test_cache.py</automated>
  </verify>
  <done>Cache layer works and integrates with LLM client.</done>
</task>

<task type="auto">
  <name>Task 4 – FastAPI /semantic endpoint</name>
  <files>backend/api/routes/semantic.py</files>
  <action>
    1. Define `POST /semantic` accepting JSON payload `{ "parsed_files": [ {"path":..., "language":..., "code":...} ] }`.
    2. For each file, invoke `LLMClient.generate_explanation` (wrapped in `BackgroundTasks` to avoid blocking).
    3. Merge the returned `explanation` and `diagram` into the original file dict.
    4. Return the enriched list as JSON.
    5. Include proper error handling (400 for malformed input, 500 for internal errors). 
  </action>
  <verify>
    <automated>pytest -q tests/semantic/test_endpoint.py</automated>
  </verify>
  <done>FastAPI route works, returns Chinese explanations and diagram data.</done>
</task>

<task type="auto">
  <name>Task 5 – Generate Mermaid & AntV G6 outputs</name>
  <files>backend/semantic/formatter.py</files>
  <action>
    1. Implement `to_mermaid(diagram_dict) -> str` that converts the model‑returned diagram dict into a Mermaid graph string with Chinese node labels.
    2. Implement `to_g6(diagram_dict) -> dict` that converts the same dict into AntV G6 JSON format.
    3. Ensure Unicode characters render correctly (no escaping needed). 
    4. Add tests verifying a sample diagram produces valid Mermaid syntax and a G6 JSON structure.
  </action>
  <verify>
    <automated>pytest -q tests/semantic/test_formatter.py</automated>
  </verify>
  <done>Formatter utilities generate both output formats.
</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries
| Boundary                | Description                                    |
|------------------------|------------------------------------------------|
| LLM API calls          | External network request to OpenAI or Qianwen  |
| Cache storage          | Redis or local file system (potential data leakage) |
| FastAPI `/semantic`   | Accepts client‑provided code snippets (untrusted) |

## STRIDE Register
| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-03-01   | Spoofing | LLM API auth | mitigate | Strictly enforce API keys from env vars; never log keys.
| T-03-02   | Tampering | Cache data | mitigate | Sign cached entries with HMAC (optional) or restrict file permissions.
| T-03-03   | DoS       | LLM request burst | mitigate | Rate‑limit per user IP; enforce per‑minute call caps.
| T-03-04   | Information Disclosure | FastAPI input | mitigate | Validate `code` length, enforce size limits (≤ 5 MB per file).
| T-03-05   | Elevation of Privilege | Env vars | mitigate | Run service under non‑root user; restrict env var exposure.
</threat_model>

<verification>
- Run full test suite (`pytest -q`) – expect **7+ new tests** to pass.
- Manually start FastAPI (`uvicorn backend.api.routes.semantic:app --reload`) and POST a small parsed file payload; verify JSON includes `explanation` (Chinese) and `mermaid`/`g6` fields.
- Verify cache hit: repeat the same request and ensure the LLM is not called (check logs for "cache hit").
- Run a sanity check that provider fallback works: temporarily unset `OPENAI_API_KEY` and confirm request falls back to Qianwen.
</verification>

<success_criteria>
- ✔ LLM client successfully calls **both OpenAI and Qianwen** APIs based on configuration.
- ✔ Prompt template produces correct function‑calling JSON schema.
- ✔ Responses are cached; repeated identical requests hit the cache.
- ✔ FastAPI `/semantic` endpoint returns enriched data within 2 seconds for typical payloads (< 100 files).
- ✔ Generated Mermaid strings render correctly with Chinese characters.
- ✔ All unit, integration, and performance tests pass (≥ 80 % coverage).
</success_criteria>

<output>
After completion, create `.planning/phases/03-semantic/03-01-PLAN.md` (this file) and a corresponding `03-01-PLAN-SUMMARY.md` summarising implementation outcomes.
</output>