---
name: Phase 4 UAT
description: User Acceptance Tests for Diagram Generation
type: uat
---

# Phase 4 UAT

## Current Assessment

当前第 4 阶段仅达到 **demo 级验证**，不能视为正式验收通过。原因如下：

- 当前 `/diagram/{project_id}` 接口可返回可渲染数据，但仍依赖 demo / 占位式上游数据链路。
- 当前前端可渲染交互图，但尚未接入完整后端工作流。
- 当前图谱转换存在边生成正确性问题，影响结果可信度。
- 当前第 3 阶段语义层阻塞，导致第 4 阶段无法基于稳定真实数据完成闭环验收。

## Verification Snapshot

| Test ID | Description | Expected Result | Actual Result | Status |
|---------|-------------|----------------|---------------|--------|
| 1 | 调用 `/diagram/{project_id}` 接口返回 Mermaid 文本，中文显示正常 | Mermaid 文本，中文不乱码 | ⚠️ 可返回 demo 级 Mermaid 与 G6 数据，但不代表完整真实链路已打通 | Partial |
| 2 | 前端 Diagram 组件成功渲染 AntV G6 图，支持缩放和平移 | 图可交互操作 | ✅ 当前 demo 图可渲染并支持拖拽/缩放 | Partial |
| 3 | 图谱转换逻辑对标准 `{source, target}` 边输入保持正确节点引用 | 不生成不存在的源节点 | ❌ 已发现 edge source 生成逻辑错误，需修复后复验 | Blocked |
| 4 | 性能基准：在 10k 行代码的依赖图上转换时间 < 2 秒 | 转换时间 < 2s | 未完成验证 | Pending |
| 5 | Docker Compose 能启动后端服务并暴露 `/diagram` 端点 | `docker compose up` 正常运行，端口可访问 | ⚠️ 当前前端构建链未闭环，Compose 不应视为已验收 | Blocked |
| 6 | 图谱数据来自真实解析 + 语义链路，而非 demo/占位数据 | 端到端链路稳定可用 | ❌ 上游 Phase 2/3 尚未完成，无法通过 | Blocked |

## Audit Evidence

- 路由注册与规划路径不一致，影响端到端联调。
- Phase 2 当前为占位解析器，不是实际 Tree-sitter 结果。
- Phase 3 当前存在导入失败与返回路径问题。
- 当前 Phase 4 能力应视为前端渲染 demo + 图谱接口原型。

## Exit Criteria Before Re-verify

- 修复 API 路由注册问题，确保公开路径与规划一致。
- 用真实 Tree-sitter 解析替换占位解析实现。
- 修复语义层导入问题与 `generate_explanation()` 返回路径。
- 修复图谱 edge 转换 bug。
- 打通前端真实后端数据流并补齐 Docker 前端构建链。

---
> 结论：第 4 阶段当前状态应为 **In Progress（demo only）**，而不是 Ready to verify / Accepted。

## Repair Verification Update 2026-06-11

当前第 4 阶段已从 demo-only 推进到局部真实闭环：

- `POST /input` 的 local 路径输入已能生成真实项目图。
- `GET /diagram/{project_id}` 对已生成项目返回 Mermaid 与 G6，对未知项目返回 404。
- 前端已从硬编码 demo 页面改为 Zip、本地路径、GitHub、Gitee 四类输入，并渲染后端返回的 G6 数据。
- 后端测试：`18 passed, 1 skipped`。
- 前端构建：`npm run build` 通过。
- 手动 HTTP 验证：以 `D:\project\ReActFlow\backend` 为输入，生成 103 nodes / 102 edges，且不包含旧 demo 文本 `模块一`。

仍未完成正式 Phase 4 验收的项目：

- Browser 插件对 localhost 导航返回 `ERR_BLOCKED_BY_CLIENT`，本轮未完成可视化截图验收。
- Zip 上传、GitHub、Gitee 输入仍需浏览器/手动链路验证。
- DeepSeek 真实 API 需使用有效 `DEEPSEEK_API_KEY` 并设置 `RUN_DEEPSEEK_INTEGRATION=1` 单独复验。
- Docker Compose 尚未复验。
- 图谱当前主要是解析器结构摘要，后续还需增强为更精确的 symbol/call graph。
