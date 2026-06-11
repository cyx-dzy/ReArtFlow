# ReActFlow

ReActFlow 是一个面向代码仓库理解的流程图生成工具。它可以接收本地目录、Zip 文件、GitHub 仓库或 Gitee 仓库，先用静态解析提取源码结构，再按需调用大模型补充中文说明，最终在前端展示可点击的 AntV G6 流程图。

## 当前能力

- 输入来源：Zip、本地目录、GitHub、Gitee。
- 后端解析：FastAPI 接收输入，解压或克隆项目，并发解析源码文件。
- 图谱生成：根据文件、语言、函数、类、导入、调用等结构生成 Mermaid 与 G6 数据。
- 前端交互：Vue 3 页面支持上传项目、查看解析进度、搜索文件、点击节点查看源码。
- AI 增强：默认使用千问百炼兼容接口，给高价值源码文件补充中文解释。
- 成本控制：流程图主体由静态解析生成，LLM 只处理有限数量和有限字符数的文件。

## 项目结构

```text
ReActFlow/
├─ backend/
│  ├─ api/          # FastAPI 应用与路由
│  ├─ diagram/      # 图谱存储、Mermaid/G6 转换
│  ├─ input/        # Zip、本地路径、GitHub、Gitee 输入处理
│  ├─ parser/       # 多语言源码解析
│  └─ semantic/     # LLM 客户端、提示词、缓存
├─ frontend/        # Vue 3 + AntV G6 前端
├─ tests/           # pytest 测试
├─ .planning/       # GSD 工作流文档
└─ docker-compose.yml
```

## 本地启动

### 1. 后端

```powershell
cd D:\project\ReActFlow
.\.venv\Scripts\Activate.ps1
$env:LLM_PROVIDER="qianwen"
$env:QIANWEN_API_KEY="你的千问百炼 API Key"
$env:LLM_MODEL="qwen-plus"
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

如果只想测试静态流程图，不调用大模型，可以不设置 API Key，或显式限制：

```powershell
$env:LLM_MAX_FILES="0"
uvicorn backend.api.app:app --reload --host 127.0.0.1 --port 8000
```

### 2. 前端

```powershell
cd D:\project\ReActFlow\frontend
npm install
npm run dev
```

浏览器访问：

```text
http://localhost:5173
```

## 重要环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_PROVIDER` | `qianwen` | 可选 `qianwen`、`deepseek`、`openai` |
| `QIANWEN_API_KEY` | 空 | 千问百炼 API Key |
| `LLM_MODEL` | `qwen-plus` | 千问默认模型 |
| `LLM_MAX_FILES` | `20` | 单次项目最多调用 LLM 的文件数 |
| `LLM_MAX_CHARS_PER_FILE` | `4000` | 每个文件最多送入 LLM 的字符数 |
| `LLM_MAX_TOTAL_CHARS` | `60000` | 单次项目最多送入 LLM 的总字符数 |
| `INPUT_JOB_WORKERS` | `2` | 后台解析任务并发数 |

## 成本控制策略

ReActFlow 参考 GitDiagram 的思路：先获取仓库结构并过滤噪声，再把图谱生成拆成可观察的阶段，并缓存/限制大模型调用。当前实现采用更保守的本地策略：

- 不把整个项目直接发送给大模型。
- 流程图主体来自静态解析结果。
- 只挑选函数、类、导入、调用等结构信号更强的前 `LLM_MAX_FILES` 个文件做 AI 解释。
- 对单文件和单项目设置字符预算。
- 没有 API Key 或 `LLM_MAX_FILES=0` 时自动跳过 AI，仍可生成基础图谱。

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

## API 简述

- `POST /input/zip/jobs`：上传 Zip 并创建后台解析任务。
- `POST /input/jobs`：提交本地路径、GitHub 或 Gitee 输入并创建后台解析任务。
- `GET /input/jobs/{job_id}`：查询任务阶段、进度和结果。
- `GET /diagram/{project_id}`：获取 Mermaid 与 G6 图谱。
- `GET /projects/{project_id}/files`：列出项目文件。
- `GET /projects/{project_id}/files/content?path=...`：读取指定文件内容。
