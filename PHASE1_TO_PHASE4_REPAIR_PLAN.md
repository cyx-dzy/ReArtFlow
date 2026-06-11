# Phase 1-4 全流程修复计划

生成时间：2026-06-11

## 目标

把项目修到 Phase 1 到 Phase 4 的真实闭环可验收状态：

- 前端支持 Zip、本地路径、GitHub URL、Gitee URL 四类输入。
- 后端完成输入处理、代码解析、文本大模型说明、图谱生成与存储。
- 前端使用 AntV G6 渲染后端真实生成的流程图，而不是硬编码 demo 图。
- DeepSeek 作为主要文本大模型 provider，用于生成中文文字说明与结构化补充。
- 自动化测试尽量离线稳定；DeepSeek 真实 API 测试通过 `DEEPSEEK_API_KEY` 单独启用。

## 实施顺序

1. 修复测试与构建基线
   - 对齐 Tree-sitter runtime 与 grammar 版本兼容问题。
   - 修复 Mermaid 转换测试的转义口径。
   - 处理性能测试依赖 `pytest-benchmark` 的问题。
   - 补齐前端 TypeScript 配置，使 `npm run build` 可运行。

2. 打通后端 Phase 1 -> Phase 4 流水线
   - 统一输入处理入口，支持 `zip`、`local`、`github`、`gitee`。
   - 输入处理完成后生成 `project_id`。
   - 解析项目文件并生成确定性的基础结构图谱。
   - 将图谱存入项目图谱存储，供 `/diagram/{project_id}` 查询。
   - `/diagram/{project_id}` 对不存在项目返回明确错误，不再返回假 demo 图。

3. 加入 DeepSeek 文本语义支持
   - 新增 `LLM_PROVIDER=deepseek`。
   - 使用 `DEEPSEEK_API_KEY` 和 OpenAI-compatible DeepSeek API。
   - 大模型只负责中文解释和结构化补充，不使用多模态。
   - 无 API key 或调用失败时，后端仍能用解析器结构图完成 Phase 4 图谱生成。

4. 前端改为真实流程
   - `App.vue` 从硬编码 demo 改为输入表单、提交状态、错误状态和图谱展示。
   - Zip 使用 multipart 上传。
   - 本地路径/GitHub/Gitee 使用 JSON 输入。
   - 成功后通过 `project_id` 拉取 `/diagram/{project_id}` 并渲染 `g6` 数据。

5. 测试与文档
   - 后端测试覆盖输入处理、解析器、图谱转换、图谱接口、端到端离线闭环。
   - 前端至少通过 `npm run build`。
   - DeepSeek 真实 API 测试在设置 `DEEPSEEK_API_KEY` 时运行。
   - 更新 `.planning/STATE.md`、`.planning/ROADMAP.md`、`.planning/4-UAT.md`，让 GSD 状态反映真实结果。

## 验收标准

- `.\.venv\Scripts\python.exe -m pytest -q` 通过，或仅跳过明确需要真实外部 API 的集成测试。
- `npm run build` 在 `frontend` 目录通过。
- 前端可以提交至少一个本地路径或 Zip 示例项目，并渲染真实生成的流程图。
- `/diagram/{project_id}` 返回包含 `project_id`、`status`、`mermaid`、`g6` 的响应。
- 图谱节点来自真实输入项目中的文件/结构，而不是固定的 `模块一`、`模块二` 示例。
