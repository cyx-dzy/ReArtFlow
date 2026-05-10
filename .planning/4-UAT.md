---
name: Phase 4 UAT
description: User Acceptance Tests for Diagram Generation
type: uat
---

# Phase 4 UAT

| Test ID | Description | Expected Result | Actual Result | Status |
|---------|-------------|----------------|---------------|--------|
| 1 | 调用 `/diagram/{project_id}` 接口返回 Mermaid 文本，中文显示正常 | Mermaid 文本，中文不乱码 | ✅ 已返回包含多个文件节点的 diagram（Mermaid 与 G6 JSON） | ✅ |
| 2 | 前端 Diagram 组件成功渲染 AntV G6 图，支持缩放和平移 | 图可交互操作 | ✅ 已渲染并可拖拽/缩放；发现根节点文案原为无意义ID，已修复为“项目根节点”（frontend/src/App.vue:14，frontend/render_test.html:43） | ✅ |
| 3 | 性能基准：在 10k 行代码的依赖图上转换时间 < 2 秒 | 转换时间 < 2s |  | ☐ |
| 4 | Docker Compose 能启动后端服务并暴露 `/diagram` 端点 | `docker compose up` 正常运行，端口可访问 |  | ☐ |

> **注意**：已在 `backend/api/app.py` 中实现 `/diagram/{project_id}` 接口。请使用 `uvicorn backend.api.app:app --host 0.0.0.0 --port 8000` 启动后端后重新测试。