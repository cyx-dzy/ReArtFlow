# ReActFlow

ReActFlow 是一个面向非技术人员的跨语言项目结构理解工具。它可以接收 Zip、本地目录、GitHub 或 Gitee 仓库，把项目源码解析成“模块化结构图谱”，再用中文解释每个文件的职责、模块边界以及文件之间的关系。目标不是给工程师做 AST 浏览器，而是让产品、运营、管理者、初级开发者也能快速看懂一个跨语言项目大概由哪些部分组成、谁调用谁、哪些文件负责入口、接口、页面、配置、数据和测试。

当前版本的图谱体验参考 GitDiagram 的表达方式，但默认更偏向“简单直观的项目流程图”：不同模块会被放进独立的白色背景板中，文件节点按功能使用不同颜色和形状展示，例如数据库或存储类文件会使用圆柱形，接口、页面、配置、测试和服务类文件会使用不同的卡片样式。默认图谱只保留关键文件和少量主干关系，避免大型项目生成后线条过密或节点堆叠。

## 核心能力

- 多来源输入：支持上传 Zip、读取后端可访问的本地目录、拉取 GitHub 仓库、拉取 Gitee 仓库。
- 静态源码解析：使用 Tree-sitter 和文件启发式规则识别 Python、JavaScript、TypeScript、TSX、Java、Go、Rust、C、C++ 等源码。
- AI 结构理解：可调用千问等 LLM，根据精简后的项目快照推断模块、文件职责和文件关系。
- 静态兜底图谱：没有 API Key、关闭 AI 或模型调用失败时，仍然可以生成可用的本地启发式图谱。
- 模块化流程图：将文件按模块分区，在白色网格画布上展示，模块背景板不可拖动，文件节点可选开启拖拽。
- 关系精简控制：默认只展示关键文件和主流程关系，对展示节点数、每个模块文件数、边数量设置上限，避免大型项目图谱过度拥挤。
- 源码预览：点击图谱节点后可在右侧预览源码，支持 Atom One Dark 风格代码高亮、行号和全屏预览；打开源码预览不会重新布局或刷新流程图。
- 文件搜索：取消常驻文件索引，改为弹窗搜索，给结构图谱留出更大的展示面积。
- 任务进度：输入解析以后台任务运行，前端显示排队、解析、AI 增强、生成图谱等阶段进度。

## 适用场景

- 给非技术同事讲解一个项目的整体结构。
- 快速了解陌生仓库的入口、模块、页面、接口、数据层和配置层。
- 分析跨语言项目中前端、后端、脚本、配置、测试之间的关系。
- 在没有完整文档的情况下，为项目生成一份可视化的结构说明。
- 作为代码审查、交接、需求沟通前的项目导览工具。

## 项目架构

```text
ReActFlow
├─ backend/                    # FastAPI 后端
│  ├─ api/                     # HTTP API 入口和路由
│  │  ├─ app.py                # FastAPI 应用入口
│  │  ├─ parse_endpoint.py     # 基础解析接口
│  │  └─ routes/
│  │     ├─ input.py           # Zip、本地目录、GitHub、Gitee 输入任务
│  │     ├─ diagram.py         # 图谱和源码文件查询接口
│  │     └─ semantic.py        # 单文件语义增强接口
│  ├─ diagram/                 # 项目级结构图谱构建
│  │  ├─ project_graph.py      # 模块、节点、边、限制和兜底关系
│  │  └─ converter.py          # 图谱转换相关工具
│  ├─ input/                   # 不同输入来源处理器
│  ├─ parser/                  # Tree-sitter 解析与文件模型
│  ├─ semantic/                # LLM 客户端、缓存、Prompt 和 Mermaid/G6 格式化
│  └─ security/                # 输入校验与安全限制
├─ frontend/                   # Vue 3 前端
│  ├─ src/App.vue              # 主页面、输入任务、源码预览、搜索
│  └─ src/components/Diagram.vue # AntV G6 图谱渲染组件
├─ tests/                      # 后端测试
├─ docs/                       # 设计和验收文档
└─ requirements.txt            # Python 依赖
```

## 工作流程

1. 用户在前端选择输入来源：Zip、本地路径、GitHub 或 Gitee。
2. 后端创建后台任务，开始处理输入源。
3. 输入处理器解压、读取或克隆项目，并过滤无关资源文件。
4. 解析器遍历源码文件，提取路径、语言、文件大小、AST 摘要和基础结构信息。
5. 后端构建项目快照，把高价值文件和结构摘要压缩成适合 LLM 理解的 JSON。
6. 如果启用 AI，LLM 会返回模块、文件节点和多类型关系边。
7. 后端对 AI 输出做校验：过滤不存在的文件、无效节点、无效边和过量内容。
8. 如果 AI 不可用或输出不足，静态图谱生成器会补齐模块、节点和关系。
9. 前端用 AntV G6 渲染结构图谱，并提供节点点击、搜索、源码预览和全屏源码查看。

## 图谱设计

ReActFlow 的图谱面向“理解项目结构”，因此会主动减少噪声，而不是把所有文件都塞进画布。

- 文件数量上限：默认最多展示 14 个关键文件节点。
- 每个模块上限：默认每个模块最多展示 3 个代表文件。
- 关系数量上限：默认最多展示 8 条主流程关系边。
- 默认排除测试、benchmark、示例源码、`.d.ts` 等支撑文件，优先保留入口、路由、输入处理、解析、图谱、语义/LLM 和前端入口文件。
- 模块背景：模块使用白色背景板承载文件节点，背景板不是业务节点，也不能被拖动。
- 节点形状：数据库/存储文件使用圆柱形，其他文件使用功能卡片。
- 关系类型：支持路由、渲染、读写数据、配置、测试、导入、调用、依赖、关联、模块关联等；前端会进一步筛选主流程边并隐藏边标签，降低线条重叠。
- 孤立节点处理：如果某些展示文件没有关系，后端会用同模块主文件或跨模块主干文件补充兜底关系。

相关限制可以通过环境变量调整：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DIAGRAM_MAX_FILE_NODES` | `14` | 静态图谱最多展示的文件节点数 |
| `DIAGRAM_MAX_FILES_PER_GROUP` | `3` | 每个模块最多展示的文件数 |
| `DIAGRAM_MAX_EDGES` | `8` | 静态图谱最多展示的关系边数 |
| `DIAGRAM_MAX_AI_FILE_NODES` | 同 `DIAGRAM_MAX_FILE_NODES` | AI 图谱最多展示的文件节点数 |
| `DIAGRAM_MAX_AI_EDGES` | 同 `DIAGRAM_MAX_EDGES` | AI 图谱最多展示的关系边数 |

## 技术栈

后端：

- FastAPI：提供输入、任务、图谱、源码查询和语义接口。
- Uvicorn：本地 ASGI 服务。
- Tree-sitter：跨语言源码结构解析。
- Requests / HTTPX：HTTP 调用和测试客户端。
- Pytest：后端单元测试和集成测试。

前端：

- Vue 3：主应用 UI。
- TypeScript：类型约束。
- Vite：开发服务器和构建工具。
- AntV G6：结构图谱渲染。
- highlight.js：源码高亮，当前使用 Atom One Dark 风格。

AI：

- 默认提供千问接入路径。
- 代码中也保留了 `openai`、`deepseek` 等 provider 名称的扩展入口。
- LLM 不是必须依赖，关闭或失败时会自动使用静态图谱。

## 本地启动

### 1. 准备 Python 环境

```powershell
cd D:\project\ReActFlow
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果项目中已经存在 `.venv`，可以直接激活并跳过创建步骤。

### 2. 准备前端依赖

```powershell
cd D:\project\ReActFlow\frontend
npm install
```

### 3. 启动后端

启用千问 AI 增强：

```powershell
cd D:\project\ReActFlow
.\.venv\Scripts\Activate.ps1
$env:LLM_PROVIDER="qianwen"
$env:LLM_MODEL="qwen-plus"
$env:QIANWEN_API_KEY="你的千问 API Key"
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

只使用静态图谱，不调用大模型：

```powershell
cd D:\project\ReActFlow
.\.venv\Scripts\Activate.ps1
$env:LLM_MAX_FILES="0"
$env:LLM_ARCHITECTURE_ENABLED="0"
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

### 4. 启动前端

```powershell
cd D:\project\ReActFlow\frontend
npm run dev
```

打开：

```text
http://localhost:5173
```

## 常用环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_PROVIDER` | `qianwen` | LLM 提供方，目前主要使用千问 |
| `QIANWEN_API_KEY` | 空 | 千问 API Key。请只放在本地环境变量中，不要提交到仓库 |
| `LLM_MODEL` | `qwen-plus` | 默认调用模型 |
| `QIANWEN_MODEL_FALLBACKS` | 空 | 当前模型失败后的候选模型，多个模型用英文逗号分隔；默认不额外重试，避免大项目架构图生成长时间阻塞 |
| `LLM_MAX_FILES` | `20` | 单文件语义解释阶段最多送入 LLM 的文件数 |
| `LLM_MAX_CHARS_PER_FILE` | `4000` | 单个文件最多送入 LLM 的字符数 |
| `LLM_MAX_TOTAL_CHARS` | `60000` | 单项目语义解释最多送入 LLM 的总字符数 |
| `LLM_ARCHITECTURE_ENABLED` | `1` | 是否启用 LLM 项目级架构图谱生成 |
| `LLM_ARCHITECTURE_MAX_FILES` | `24` | 项目级架构图发送给 LLM 的最多文件数 |
| `LLM_ARCHITECTURE_MAX_EXPLANATION_CHARS` | `120` | 项目级架构图快照中每个文件解释的最大字符数 |
| `LLM_ARCHITECTURE_TIMEOUT` | `25` | 项目级架构图 LLM 请求超时时间，超时后回退静态图谱 |
| `INPUT_JOB_WORKERS` | `2` | 后台输入解析任务并发数 |
| `GIT_CLONE_TIMEOUT` | `120` | GitHub/Gitee 克隆仓库的超时时间 |

## API 说明

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 后端健康检查 |
| `POST` | `/parse` | 直接提交文件列表并返回解析结果 |
| `POST` | `/semantic` | 对解析后的文件进行语义增强 |
| `POST` | `/input` | 同步处理本地目录、GitHub、Gitee 等输入 |
| `POST` | `/input/zip` | 同步处理 Zip 输入 |
| `POST` | `/input/jobs` | 创建异步输入任务，支持本地目录、GitHub、Gitee |
| `POST` | `/input/zip/jobs` | 创建异步 Zip 输入任务 |
| `GET` | `/input/jobs/{job_id}` | 查询任务阶段、进度和最终结果 |
| `GET` | `/diagram/{project_id}` | 获取 Mermaid 和 G6 格式图谱 |
| `POST` | `/diagram/{project_id}` | 手动存储一个图谱 |
| `GET` | `/projects/{project_id}/files` | 查询项目文件列表 |
| `GET` | `/projects/{project_id}/files/content?path=...` | 查询指定文件内容 |

## 前端使用说明

1. 在顶部选择输入方式。
2. Zip 模式上传压缩包；本地路径模式输入后端可以访问的目录；GitHub/Gitee 模式输入仓库地址。
3. 点击“生成图谱”。
4. 等待进度条到 100%。
5. 在结构图谱中查看模块背景板、文件节点和关系边。
6. 点击文件节点打开源码预览。
7. 使用“搜索文件”快速定位目标文件。
8. 勾选“节点拖拽”后，可以手动调整文件节点位置；模块背景板不会作为节点被拖动。

## 测试和构建

运行后端测试：

```powershell
cd D:\project\ReActFlow
.\.venv\Scripts\python.exe -m pytest -q
```

只运行图谱相关测试：

```powershell
cd D:\project\ReActFlow
.\.venv\Scripts\python.exe -m pytest tests\backend\test_project_graph.py -q
```

构建前端：

```powershell
cd D:\project\ReActFlow\frontend
npm run build
```

运行千问真实 API 集成测试：

```powershell
cd D:\project\ReActFlow
$env:LLM_PROVIDER="qianwen"
$env:QIANWEN_API_KEY="你的千问 API Key"
$env:RUN_QIANWEN_INTEGRATION="1"
.\.venv\Scripts\python.exe -m pytest tests\semantic\test_llm_client.py -q
```

## 安全和资源过滤

ReActFlow 会尽量避免把无关或高噪声内容送入解析和 LLM：

- 默认跳过 `.git`、`node_modules`、`.venv`、`dist`、`build`、缓存目录等。
- 默认跳过图片、音视频、字体、压缩包、PDF、Office、数据库二进制等资源文件。
- Zip 和仓库输入会经过基础安全校验，避免路径穿越等风险。
- LLM 输入经过文件数量和字符数量限制，降低成本和超时风险。
- API Key 应通过环境变量提供，不应写入 README、测试数据或提交到仓库。

## 当前限制

- 图谱关系由静态规则和 LLM 输出共同决定，复杂项目中仍可能需要人工二次理解。
- 项目图谱目前存储在内存中，服务重启后需要重新生成。
- 超大型仓库会被主动抽样和裁剪，图谱展示的是代表性结构，不是完整文件清单。
- 前端的模块布局针对“非技术人员快速理解”优化，不是精确的依赖图排版工具。
- AI 增强依赖模型可用性、API Key、网络和上下文限制；失败时会自动回退到静态图谱。

## 项目愿景

ReActFlow 希望成为一个“代码项目导览器”：它不要求用户先理解框架、语言和目录习惯，而是把项目翻译成更接近业务沟通的模块地图。未来可以继续扩展的方向包括：

- 更稳定的多语言调用/依赖分析。
- 更细粒度的模块关系推理。
- 持久化项目图谱和历史版本对比。
- 面向团队交接的导出报告。
- 与更多代码托管平台和私有仓库认证方式集成。
