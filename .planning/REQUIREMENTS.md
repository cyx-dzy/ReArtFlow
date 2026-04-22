---
name: 项目需求
description: 多语言代码智能分析 AI Agent 的需求清单
type: project
---

# Requirements: 多语言代码智能分析 AI Agent

**Defined:** 2026-04-22
**Core Value:** 为非技术人员快速了解跨语言项目结构，提供中文思维导图展示代码调用关系。

## v1 Requirements

### 输入处理 (Input Handling)

- [ ] **INP-01**: 支持上传本地 Zip 包并自动解压
- [ ] **INP-02**: 支持通过 GitHub 链接克隆仓库
- [ ] **INP-03**: 支持通过 Gitee 链接克隆仓库
- [ ] **INP-04**: 支持本地路径直接解析

### 代码解析 (Parsing)

- [ ] **PAR-01**: 使用 Tree‑sitter 支持至少 20 种主流语言（包括 Python、JavaScript/TypeScript、Java、Go、Rust、C/C++）
- [ ] **PAR-02**: 抽取函数、类、import、调用关系等结构信息
- [ ] **PAR-03**: 为每个文件记录 `size`、`mtime`、`parse_time_ms` 等元数据
- [ ] **PAR-04**: 并行解析文件以提升整体解析速度

### AI 语义理解 (AI Semantic)

- [ ] **AI-01**: 调用 LLM（OpenAI / 本地模型）对抽取的结构生成中文解释
- [ ] **AI-02**: 基于函数调用图推理依赖关系并生成自然语言描述
- [ ] **AI-03**: 支持可插拔的模型选项（默认使用 Sonnet，预算模式使用 Haiku）

### 图谱生成 (Diagram Generation)

- [ ] **VIS-01**: 将统一的 JSON 依赖图转换为 Mermaid 文本
- [ ] **VIS-02**: 支持 AntV G6 渲染交互式思维导图
- [ ] **VIS-03**: 正确显示中文字符，使用 Noto Sans SC / Source Han Sans 字体

### 前端展示 (Frontend UI)

- [ ] **UI-01**: 使用 Vue3 + Vite 构建单页应用
- [ ] **UI-02**: 提供文件结构树、代码‑解释联动功能
- [ ] **UI-03**: 支持搜索、节点高亮、点击跳转源码视图

### 部署 & 运维 (Deployment & Ops)

- [ ] **DEP-01**: 提供 Docker Compose 包含 `backend`（FastAPI）和 `frontend`
- [ ] **DEP-02**: 支持水平扩展，后端可多实例部署
- [ ] **DEP-03**: 配置健康检查端点

### 安全/隐私 (Security & Privacy)

- [ ] **SEC-01**: 所有密钥、API token 均通过环境变量或 Secret Manager 管理，代码中不硬编码
- [ ] **SEC-02**: 对用户输入的仓库链接进行基本校验防止 SSRF
- [ ] **SEC-03**: 对外部 API 调用使用 HTTPS，验证证书

## v2 Requirements

### 高级功能 (Advanced Features)

- **AI-04**: 支持本地部署的 CodeLlama‑34B 进行离线推理
- **VIS-04**: 提供导出为 PNG、SVG、PDF 等格式的功能
- **UI-04**: 支持多语言 UI（中文、英文）切换

## Out of Scope

| Feature | Reason |
|---------|--------|
| 实时协作编辑 | 超出当前核心目标，复杂度高 |
| 多用户权限体系 | 首版聚焦单用户使用 |
| 视频解析 | 与代码分析关系不大 |
| 移动端原生 App | 先实现 Web 版，移动端后期考虑 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INP-01 | Phase 1 | Pending |
| INP-02 | Phase 1 | Pending |
| INP-03 | Phase 1 | Pending |
| INP-04 | Phase 1 | Pending |
| PAR-01 | Phase 2 | Pending |
| PAR-02 | Phase 2 | Pending |
| PAR-03 | Phase 2 | Pending |
| PAR-04 | Phase 2 | Pending |
| AI-01 | Phase 3 | Pending |
| AI-02 | Phase 3 | Pending |
| AI-03 | Phase 3 | Pending |
| VIS-01 | Phase 4 | Pending |
| VIS-02 | Phase 4 | Pending |
| VIS-03 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| DEP-01 | Phase 6 | Pending |
| DEP-02 | Phase 6 | Pending |
| DEP-03 | Phase 6 | Pending |
| SEC-01 | Phase 1 | Pending |
| SEC-02 | Phase 1 | Pending |
| SEC-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✅

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 after initial definition*
