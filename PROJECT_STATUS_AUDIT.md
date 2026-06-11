# ReActFlow 当前项目状态审计报告

生成时间：2026-06-10  
审计范围：`.planning` 规划文件、后端源码、前端源码、测试用例、构建与测试命令。  
结论口径：以当前代码实际可运行结果为准，而不是以 UAT 文档中的历史描述为准。

## 1. 总体结论

当前项目处于“原型功能已分层成形，但端到端链路尚未打通”的阶段。粗略完成度建议仍按 **35% - 40%** 评估，比 `.planning/STATE.md` 中的 35% 略有前进，但还不能视为 v1 可验收。

主要原因如下：

1. 后端 FastAPI 应用已注册 `/input`、`/parse`、`/semantic`、`/diagram/{project_id}`、`/health` 等路由，整体架构骨架存在。
2. 输入处理、解析器、语义层、图转换、前端 G6 展示都有代码实现，但大多仍是“可演示/可单测一部分”的状态。
3. 当前完整后端测试未通过：`8 passed, 3 failed, 1 error`。
4. 当前标准前端构建命令 `npm run build` 未通过，原因是缺少 `frontend/tsconfig.json`。
5. 规划文件中有多处历史 UAT 结论过于乐观，尤其 Phase 2 和 Phase 3；但 `.planning/STATE.md` 和 `.planning/ROADMAP.md` 的纠偏结论总体方向仍然接近真实状态。

最关键的实际阻塞是：

- Tree-sitter Python runtime 与 grammar 包版本不兼容，导致解析器测试和 `/parse` 接口失败。
- Phase 3 语义层只验证了 OpenAI mock 路径，真实 OpenAI 依赖未安装，fallback、chunking、接口测试均未充分覆盖。
- Phase 4 图谱和前端仍依赖 demo/占位数据，未连接真实解析与语义结果。
- 前端工程配置不完整，项目定义的生产构建命令不可用。

## 2. 我检查过的规划状态

`.planning` 目录包含：

- `PROJECT.md`：描述项目目标为多语言代码智能分析 AI Agent，输入层 -> 解析层 -> 语义层 -> 图谱层 -> 前端展示。
- `REQUIREMENTS.md`：列出 INP、PAR、AI、VIS、UI、DEP、SEC 等 v1 需求。
- `ROADMAP.md`：当前把 Phase 1/2/4 标为 In Progress，Phase 3 标为 Blocked，Phase 5/6 标为 Pending。
- `STATE.md`：记录项目停在 2026-05-11 的纠偏审计状态，进度 35%，Phase 3 阻塞。
- `PLAN_1.md` 到 `PLAN_4.md`：分别描述输入安全、解析、语义、图谱阶段计划。
- `1-UAT.md` 到 `4-UAT.md`：历史验收记录，其中 Phase 2 和 Phase 3 的 UAT 与当前代码/测试证据不完全一致。

规划目录中相对准确的部分：

- Phase 4 只能算 demo 级，这与当前代码一致。
- Phase 5 仍未完成真实文件树、搜索、代码解释联动，这与当前前端代码一致。
- Docker/部署未闭环，这与当前前端构建失败一致。

规划目录中过时或不准确的部分：

- `.planning/ROADMAP.md` 和 `STATE.md` 仍说 Phase 2 是 placeholder；当前代码已经接入 `tree_sitter_*` grammar 包并做 AST 计数，不再只是纯 placeholder。但当前实现运行失败，且仍未达到 20+ 语言、异步任务、schema 校验等计划要求。
- `.planning/2-UAT.md` 声称解析测试通过、性能达标；当前实测失败。
- `.planning/3-UAT.md` 声称 OpenAI/Qianwen、缓存、接口都通过；当前测试目录实际只覆盖了 OpenAI mock 的 happy path。

## 3. 当前源码结构概况

代码规模粗略统计：

- `backend`：24 个文件。
- `frontend/src`：3 个文件。
- `tests`：7 个测试文件。
- `.planning`：16 个规划/研究/状态文件。

后端主要模块：

- `backend/api/app.py`：FastAPI 入口，注册 input、semantic、parse、diagram router。
- `backend/input/*`：Zip、GitHub、Gitee、本地路径输入处理。
- `backend/security/validation.py`：仓库 URL 校验与环境变量 secret 加载。
- `backend/parser/*`：Tree-sitter 文件解析、并发目录解析、Pydantic 输出模型。
- `backend/semantic/*`：LLM client、prompt、cache、Mermaid/G6 formatter。
- `backend/diagram/converter.py`：JSON -> Mermaid 转换工具。

前端主要模块：

- `frontend/src/App.vue`：静态 demo 页面，直接传入固定 graphData。
- `frontend/src/components/Diagram.vue`：AntV G6 渲染组件，支持拖拽画布、缩放、拖拽节点。
- `frontend/vite.config.ts`：Vite 配置，但缺少 TypeScript 项目配置文件。

## 4. 实测结果

### 4.1 后端测试

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

结果：

```text
3 failed, 8 passed, 1 warning, 1 error
```

失败/错误明细：

1. `tests/parser/test_tree_sitter_pool.py::test_parse_file_returns_expected_fields`
   - 错误：`ValueError: Incompatible Language version 15. Must be between 13 and 14`
   - 判断：`tree-sitter==0.23.2` 与 `tree-sitter-python==0.25.0` / `tree-sitter-javascript==0.25.0` 等 grammar 包版本不兼容。

2. `tests/api/test_parse_endpoint.py::test_parse_endpoint_returns_parsed_files`
   - 结果：预期 200，实际 500。
   - 根因：同一个 Tree-sitter 版本兼容问题导致 `/parse` 调用失败。

3. `tests/backend/test_converter.py::test_json_to_mermaid_escaping`
   - 结果：测试期望 `node1[Node\[Special\];]`，实际生成 `node1[Node\[Special\]\;]`。
   - 判断：实现与测试对于 `]` 和 `;` 的转义口径不一致，需要确定 Mermaid 目标语法后统一。

4. `tests/performance/test_diagram_perf.py::test_json_to_mermaid_performance`
   - 错误：缺少 `benchmark` fixture。
   - 判断：项目未安装 `pytest-benchmark`，但性能测试依赖它。

### 4.2 前端构建

命令：

```powershell
npm run build
```

结果：

```text
error TS5083: Cannot read file 'D:/project/ReActFlow/frontend/tsconfig.json'.
```

判断：项目标准构建命令不可用，缺少 `tsconfig.json`。

补充验证：

```powershell
npx vite build
```

结果：Vite 可构建成功，但有 chunk 体积警告：

```text
dist/assets/index-*.js  1,372.82 kB │ gzip: 414.70 kB
(!) Some chunks are larger than 500 kB after minification.
```

判断：前端 demo 可被 Vite 打包，但 TypeScript 标准构建链未闭合，且 G6 bundle 体积偏大。

### 4.3 依赖状态

当前虚拟环境中：

- 已安装：`tree-sitter==0.23.2`、`tree-sitter-python==0.25.0`、`tree-sitter-javascript==0.25.0`、`pytest==9.0.3`、`fastapi==0.136.0`、`langchain==0.2.0`。
- 未安装：`openai`、`redis`、`langchain-openai`、`pytest-benchmark`。

影响：

- 真实 OpenAI 调用路径不能工作，除非额外安装 `openai`。
- Redis 缓存路径不能工作，除非额外安装 `redis`。
- 性能测试不能运行，除非额外安装 `pytest-benchmark`。

## 5. 各阶段实际完成情况

### Phase 1：Input & Security Handling

实际状态：**部分完成，偏原型可用。**

已完成：

- 有抽象输入处理器 `InputProcessor`。
- 有 Zip 解压处理器，并测试通过基础解压场景。
- 有 GitHub/Gitee 处理器，clone 前会校验 HTTPS 和 host 白名单。
- 有本地路径处理器。
- 有 URL 安全校验工具，测试覆盖了 HTTPS、host、路径穿越等基础情况。
- `/input` 路由已注册。

主要差距：

- GitHub/Gitee/local handler 缺少对应自动化测试。
- `git clone` 未设置 timeout，存在卡死风险。
- Zip 防路径穿越使用字符串 `startswith` 判断，遇到相同前缀目录名时不够严谨，建议改成 `Path.resolve().relative_to()` 或等价安全判断。
- `/input` 路由职责过重：它不仅处理输入，还立即解析、调用 LLM、合并 diagram，并且失败时保留 placeholder。这会让错误被吞掉，端到端可信度下降。
- 本地路径没有限制在允许的工作目录/沙箱内。

完成度建议：**55% - 65%**。

### Phase 2：Multi-language Code Parsing

实际状态：**有真实 Tree-sitter 方向实现，但当前不可运行，未验收。**

已完成：

- `backend/parser/tree_sitter_pool.py` 已接入 `tree_sitter` 和多种 grammar 包。
- 支持扩展名：`.py`、`.js`、`.jsx`、`.ts`、`.tsx`、`.java`、`.go`、`.rs`、`.c`、`.cpp`。
- 能设计上统计 `functions`、`classes`、`imports`、`calls`。
- `parse_project()` 使用 `ThreadPoolExecutor` 并发解析文件。
- `ParsedFile` 模型包含 `path`、`size`、`mtime`、`parse_time_ms`、`language`、`ast_summary`。
- `/parse` 路由已注册。

当前阻塞：

- Tree-sitter runtime 与 grammar 版本不兼容，导致实际解析失败。
- `/parse` 因解析失败返回 500。

与计划差距：

- 计划要求 20+ 主流语言，当前只有约 9 个语言 key/10 个扩展名。
- 计划要求异步任务 `task_id` + 轮询，当前是同步 `POST /parse` 直接返回列表。
- 计划提到 `backend/schemas/parse_output.json`，当前仓库没有这个 schema 文件。
- 当前只做 AST 节点计数，没有抽取具体函数名、类名、import 详情和调用关系边。
- 没有文件大小限制、解析超时、错误文件隔离等安全/稳定性机制。
- 性能基准依赖当前解析器，但解析器已因版本问题不可运行。

完成度建议：**30% - 40%**。它比旧文档说的 placeholder 更进一步，但现在仍不能作为可靠解析层使用。

### Phase 3：AI Semantic Understanding

实际状态：**核心代码有雏形，但真实能力未闭环。**

已完成：

- `LLMClient` 支持根据 `LLM_PROVIDER` 选择 `openai` 或 `qianwen`。
- prompt 模板包含中文 system prompt、few-shot examples、function-call schema。
- 有文件缓存 fallback，Redis 逻辑也写了可选路径。
- `generate_explanation()` 当前主路径会缓存并返回结果，旧规划中提到的“成功路径不 return”问题已经不存在。
- 有 `/semantic` 路由，能接收 `parsed_files` 并返回 `explanation`、`mermaid`、`g6`。
- 有一个 OpenAI mock 测试通过。

主要差距：

- `requirements.txt` 没有声明 `openai`、`redis`、`langchain-openai`。
- 当前环境未安装 `openai`，真实 OpenAI 路径不可用。
- 没有实现计划中的 provider fallback：OpenAI 失败后自动切 Qianwen，或反向 retry。
- 没有实现 token chunking、overlap、预摘要等大文件策略。
- `/semantic` 接口虽声明 `BackgroundTasks` 参数，但实际同步执行 LLM 调用。
- 缺少 semantic endpoint、cache、prompt schema、Qianwen 路径、错误场景的测试。
- 默认 provider 是 `openai`，没有 API key 时正常会失败；这适合真实调用，但不适合 demo 链路稳定展示。

完成度建议：**25% - 35%**。

### Phase 4：Diagram Generation

实际状态：**demo 级可用，非真实链路验收。**

已完成：

- `backend/diagram/converter.py` 有 JSON -> Mermaid 转换。
- `backend/semantic/formatter.py` 有 `to_mermaid()` 和 `to_g6()`。
- `/diagram/{project_id}` GET/POST 已注册。
- GET 缺省会返回带中文节点的示例图。
- 前端 `Diagram.vue` 可以用 AntV G6 渲染传入的 graphData。
- `npx vite build` 能打包 demo。

主要差距：

- 图数据存在内存 `_DIAGRAM_STORE`，无持久化。
- 未与真实 parse + semantic 结果稳定打通。
- GET 未命中时会生成示例图，容易掩盖项目不存在/处理失败的问题。
- Mermaid 转义测试失败，转换规则需要统一。
- 性能测试因缺少 `pytest-benchmark` 未运行。
- `docs/diagram.md` 描述的接口返回结构与当前 `GET /diagram/{project_id}` 实际返回 `{mermaid, g6}` 不一致。

完成度建议：**35% - 45%**。

### Phase 5：Frontend UI

实际状态：**仅 demo 展示。**

已完成：

- Vue3 + Vite 项目存在。
- AntV G6 组件存在。
- 静态图谱可以渲染。

主要差距：

- `App.vue` 仍是“Diagram 交互测试页”，使用硬编码 graphData。
- 没有输入上传/仓库链接表单。
- 没有调用 `/input`、`/parse`、`/semantic`、`/diagram` 的真实 API 客户端。
- 没有文件树、搜索、节点高亮、代码解释联动、源代码跳转。
- 缺少 `tsconfig.json`，`npm run build` 失败。
- 没有前端测试。

完成度建议：**15% - 25%**。

### Phase 6：Deployment & Operations

实际状态：**后端容器雏形存在，整体部署未验收。**

已完成：

- 有后端 `Dockerfile`。
- 有 `docker-compose.yml`，包含 backend 和 frontend 服务。
- 有 `/health` endpoint。

主要差距：

- `docker-compose.yml` 的 frontend 使用 `context: ./frontend`，但 `frontend` 下没有 Dockerfile，Compose 前端构建大概率失败。
- 前端标准构建命令本身失败。
- 没有水平扩展配置或验证。
- 没有生产静态资源服务方案。
- 没有 CI/CD、健康检查配置、日志/监控配置。

完成度建议：**20% - 30%**。

## 6. v1 需求完成度矩阵

| 需求 | 当前判断 | 说明 |
|---|---:|---|
| INP-01 Zip 上传/解压 | Partial | handler 和测试存在，但 API 真实上传文件流程未完整实现 |
| INP-02 GitHub clone | Partial | handler 存在，缺少测试和 timeout |
| INP-03 Gitee clone | Partial | handler 存在，缺少测试和 timeout |
| INP-04 本地路径解析 | Partial | handler 存在，缺少沙箱限制和测试 |
| SEC-01 Secret 管理 | Partial | helper 存在，但未系统性接入和测试 |
| SEC-02 SSRF 防护 | Partial | URL 基础校验存在，覆盖有限 |
| SEC-03 HTTPS 外部 API | Partial | repo URL 强制 HTTPS；LLM API 路径未完整验证 |
| PAR-01 20+ 语言 Tree-sitter | Not done | 当前约 9 种语言 key，且运行时失败 |
| PAR-02 抽取函数/类/import/调用关系 | Partial | 只做计数，不产生详细关系模型 |
| PAR-03 文件元数据 | Partial | 模型和代码有字段，但解析器当前失败 |
| PAR-04 并行解析 | Partial | ThreadPoolExecutor 存在，但性能未通过验证 |
| AI-01 LLM 中文解释 | Partial | mock 测试通过，真实依赖/API key 未闭环 |
| AI-02 依赖关系自然语言描述 | Not done | 没有基于真实调用图的推理链路 |
| AI-03 可插拔模型 | Partial | OpenAI/Qianwen 分支存在，无 fallback/完整依赖 |
| VIS-01 JSON -> Mermaid | Partial | 有实现，但转义测试失败 |
| VIS-02 AntV G6 交互图 | Partial | demo 可渲染，未接真实后端 |
| VIS-03 中文显示 | Partial | demo 中文可传递，字体方案未落实 |
| UI-01 Vue3 + Vite SPA | Partial | 项目存在，但标准构建失败 |
| UI-02 文件树/代码解释联动 | Not done | 未实现 |
| UI-03 搜索/高亮/跳转源码 | Not done | 未实现 |
| DEP-01 Docker Compose | Partial | compose 存在，但 frontend 构建链不完整 |
| DEP-02 水平扩展 | Not done | 未实现/未验证 |
| DEP-03 健康检查 | Done | `/health` 存在 |

## 7. 最重要的风险

1. **测试红灯风险**
   - 当前不能以“已完成 Phase 2/4”作为后续开发基础，因为核心解析测试失败。

2. **规划与现实漂移**
   - Phase 2/3 UAT 曾记录通过，但当前测试和依赖状态不支持这些结论。后续应把 UAT 文档回填到真实状态。

3. **端到端链路不可观测**
   - `/input` 会在失败时保留 placeholder，`/diagram` 未命中时也返回示例图，这会让 demo 看起来正常，但掩盖真实处理失败。

4. **依赖版本未锁稳**
   - Tree-sitter runtime/grammar 已出现 ABI 版本不兼容；OpenAI/Redis/benchmark 依赖也缺失。

5. **前端交付链未闭合**
   - 缺 `tsconfig.json` 直接导致标准构建失败；Compose 前端也缺 Dockerfile。

## 8. 建议的下一步修复顺序

建议不要先扩功能，先把最小真实闭环打绿：

1. **修复依赖与测试基线**
   - 对齐 `tree-sitter` 与 `tree-sitter-*` grammar 版本。
   - 增加或移除/标记 `pytest-benchmark` 依赖。
   - 统一 Mermaid 转义规则，使实现和测试一致。
   - 目标：`.\.venv\Scripts\python.exe -m pytest -q` 全绿。

2. **修复前端标准构建**
   - 补 `frontend/tsconfig.json` 和必要的 Vue TS 配置。
   - 目标：`npm run build` 成功。

3. **收敛 Phase 2**
   - 明确 v1 是支持 9/10 个扩展名，还是必须 20+ 语言。
   - 为解析结果增加详细结构：函数名、类名、imports、调用边。
   - 增加 schema 或删除规划中不存在的 schema 要求。
   - 处理单文件失败隔离、文件大小限制、解析超时。

4. **收敛 Phase 3**
   - 把 `openai`、`redis`、`pytest-benchmark` 等真实依赖写入 requirements，或明确为 optional extras。
   - 增加 `/semantic` endpoint 测试、cache 测试、Qianwen/mock 测试。
   - 实现 provider fallback 或从计划中删除该要求。
   - 增加大文件 chunking 策略。

5. **打通最小端到端 demo**
   - 建议链路：本地目录 -> `/parse` -> mocked `/semantic` -> `/diagram` -> 前端真实 fetch。
   - 先不要依赖真实 LLM，先用 mock semantic 保证 UI 和后端数据模型闭环。

6. **更新 GSD 文档**
   - 将 `.planning/2-UAT.md`、`.planning/3-UAT.md` 改成当前真实状态。
   - 把 `.planning/ROADMAP.md` 中 Phase 2 从“placeholder”改成“Tree-sitter implementation present but blocked by dependency/runtime mismatch”。
   - 保留 Phase 4 demo-only 判断。

## 9. 当前可交付内容判断

如果现在对外展示，建议只称为：

> ReActFlow 当前是一个“多语言代码解析与图谱展示”的技术原型，已有 FastAPI/Vue/G6/Tree-sitter/LLM wrapper 的分层骨架，但真实端到端分析链路尚未完成，生产构建和测试基线尚未通过。

不建议称为：

- 已完成多语言 Tree-sitter 解析平台。
- 已完成 AI 语义理解层。
- 已完成可部署的 Docker Compose 全栈应用。
- 已完成 v1 UAT。

## 10. 本次审计没有修改的内容

本报告只新增当前文件：`PROJECT_STATUS_AUDIT.md`。  
没有修改业务代码、测试代码或 `.planning` 文件。  
工作区中已有的 `.gitignore` 修改与本次审计无关，我未覆盖它。
