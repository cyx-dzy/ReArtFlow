# ReActFlow

ReActFlow 是一个面向非技术人员的跨语言项目结构理解工具。它可以接收本地目录、Zip、GitHub 或 Gitee 仓库，先用静态解析提取主体源码结构，再按需调用千问等大模型识别模块职责和文件关系，最后在前端展示可点击的中文架构图。

## 当前能力

- 输入来源：Zip、本地目录、GitHub、Gitee。
- 后端解析：FastAPI 接收输入，解压或克隆项目，并解析可识别的源码文件。
- 中文架构图：参考 GitDiagram 的紧凑图谱思路，输出项目概览、子系统、核心文件、节点形状和多种关系。
- 前端交互：Vue 3 + AntV G6 展示图谱，支持解析进度、文件搜索、节点点击联动源码预览。
- 成本控制：静态解析负责压缩上下文，LLM 只处理有限文件和结构化项目快照。
- 资源过滤：图片、CSV/Excel、PDF、压缩包、字体、音视频等非主体框架文件不会进入解析和文件浏览结果。
- 静态兜底：没有 API Key、模型失败或关闭 AI 时，仍可生成静态图谱。

## 本地启动

### 后端

```powershell
cd D:\project\ReActFlow
.\.venv\Scripts\Activate.ps1
$env:LLM_PROVIDER="qianwen"
$env:QIANWEN_API_KEY="你的千问百炼 API Key"
$env:LLM_MODEL="qwen-plus"
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

如果只想生成静态图谱，不调用大模型：

```powershell
$env:LLM_MAX_FILES="0"
$env:LLM_ARCHITECTURE_ENABLED="0"
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

### 前端

```powershell
cd D:\project\ReActFlow\frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_PROVIDER` | `qianwen` | 可选 `qianwen`、`deepseek`、`openai` |
| `QIANWEN_API_KEY` | 空 | 千问百炼 API Key |
| `LLM_MODEL` | `qwen-plus` | 当前优先访问的千问模型 |
| `QIANWEN_MODEL_FALLBACKS` | 见下方 | 当前模型失败后的千问候选模型，英文逗号分隔 |
| `LLM_MAX_FILES` | `20` | 单个项目最多对多少个高价值文件做 AI 单文件解释 |
| `LLM_MAX_CHARS_PER_FILE` | `4000` | 单文件最多送入 LLM 的字符数 |
| `LLM_MAX_TOTAL_CHARS` | `60000` | 单项目单文件解释阶段最多送入 LLM 的总字符数 |
| `LLM_ARCHITECTURE_ENABLED` | `1` | 是否让 LLM 生成整体模块和关系图谱；设为 `0` 时只使用静态图谱 |
| `INPUT_JOB_WORKERS` | `2` | 后台解析任务并发数 |

## 千问模型兜底

系统会先尝试当前 `LLM_MODEL`。如果当前模型访问失败或超时，会按下面顺序继续尝试：

```text
qwen3.7-plus,
qwen-math-turbo,
qwen3-vl-235b-a22b-thinking,
qwen3-vl-32b-thinking,
qwen-plus-2025-07-28,
qwen-max,
glm-5
```

所有模型都失败后，后端会跳过 AI 增强，继续生成静态图谱。可以用 `QIANWEN_MODEL_FALLBACKS` 覆盖默认顺序，多个模型用英文逗号分隔。

## 图谱生成流程

1. 输入处理：解压 Zip、读取本地目录或克隆仓库。
2. 静态解析：过滤 `node_modules`、`.git`、`dist`、`build`、资源文件等噪声内容。
3. 项目快照：把文件路径、语言、模块、角色、AST 摘要和可选中文解释整理成精简 JSON。
4. 千问图谱：请求模型输出 `groups`、`nodes`、`edges`，节点必须引用真实文件路径。
5. 安全校验：过滤不存在的路径、无效节点和无效边，并自动补齐 `项目 -> 模块 -> 文件` 的包含关系。
6. 前端展示：G6 根据 `shape`、`color`、`type`、`label` 渲染不同图形和关系。

## 测试

后端测试：

```powershell
cd D:\project\ReActFlow
.\.venv\Scripts\python.exe -m pytest -q
```

前端构建：

```powershell
cd D:\project\ReActFlow\frontend
npm run build
```

千问真实 API 集成测试：

```powershell
cd D:\project\ReActFlow
$env:LLM_PROVIDER="qianwen"
$env:QIANWEN_API_KEY="你的千问百炼 API Key"
$env:RUN_QIANWEN_INTEGRATION="1"
.\.venv\Scripts\python.exe -m pytest tests\semantic\test_llm_client.py -q
```

## API

- `POST /input/zip/jobs`：上传 Zip 并创建后台解析任务。
- `POST /input/jobs`：提交本地路径、GitHub 或 Gitee 输入并创建后台解析任务。
- `GET /input/jobs/{job_id}`：查询任务阶段、进度和结果。
- `GET /diagram/{project_id}`：获取 Mermaid 与 G6 图谱。
- `GET /projects/{project_id}/files`：列出项目文件。
- `GET /projects/{project_id}/files/content?path=...`：读取指定文件内容。
