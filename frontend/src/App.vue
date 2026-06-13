<template>
  <main class="app-shell">
    <section class="hero-panel" aria-labelledby="app-title">
      <div class="hero-copy">
        <p class="eyebrow">Code structure atlas</p>
        <h1 id="app-title">ReActFlow</h1>
        <p class="hero-summary">
          上传或指向一个项目，生成面向非技术人员的中文代码结构图，并在图谱旁边快速预览对应源码。
        </p>
      </div>

      <div class="status-strip" aria-label="当前项目状态">
        <div class="status-metric">
          <span>项目</span>
          <strong>{{ projectId ? '已载入' : '待解析' }}</strong>
        </div>
        <div class="status-metric">
          <span>节点</span>
          <strong>{{ graphData?.nodes.length ?? 0 }}</strong>
        </div>
        <div class="status-metric">
          <span>文件</span>
          <strong>{{ files.length }}</strong>
        </div>
      </div>
    </section>

    <section class="control-panel" aria-label="项目解析">
      <div class="mode-tabs" role="tablist" aria-label="输入方式">
        <button
          v-for="option in modeOptions"
          :key="option.value"
          type="button"
          :class="{ active: mode === option.value }"
          :aria-selected="mode === option.value"
          role="tab"
          @click="mode = option.value"
        >
          <span>{{ option.label }}</span>
          <small>{{ option.hint }}</small>
        </button>
      </div>

      <form class="input-row" @submit.prevent="submit">
        <label class="input-field">
          <span>{{ inputLabel }}</span>
          <input
            v-if="mode === 'zip'"
            type="file"
            accept=".zip,application/zip"
            @change="onFileChange"
          />
          <input
            v-else
            v-model="textInput"
            :placeholder="placeholder"
            type="text"
            autocomplete="off"
          />
        </label>
        <button class="primary-action" type="submit" :disabled="loading">
          {{ loading ? '解析中' : '开始解析' }}
        </button>
      </form>

      <div v-if="job" class="progress-panel" aria-live="polite">
        <div class="progress-line">
          <div>
            <span>{{ stageLabel(job.stage) }}</span>
            <strong>{{ job.message }}</strong>
          </div>
          <b>{{ job.progress }}%</b>
        </div>
        <progress :value="job.progress" max="100"></progress>
        <small>{{ job.current }} / {{ job.total }} 个步骤</small>
      </div>

      <div v-if="projectId" class="project-token">
        <span>Project ID</span>
        <code>{{ projectId }}</code>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </section>

    <section class="workspace-grid" aria-label="代码图谱工作区">
      <aside class="file-panel" aria-label="文件索引">
        <div class="panel-titlebar">
          <div>
            <span>文件索引</span>
            <strong>{{ filteredFiles.length }} / {{ files.length }}</strong>
          </div>
        </div>
        <label class="file-search">
          <span>搜索文件</span>
          <input v-model="fileQuery" type="search" placeholder="文件名、路径或语言" />
        </label>
        <div class="file-list">
          <button
            v-for="file in filteredFiles"
            :key="file.path"
            type="button"
            :class="{ selected: selectedPath === file.path }"
            @click="selectFile(file.path)"
          >
            <strong>{{ file.name }}</strong>
            <span>{{ file.path }}</span>
            <small>{{ file.language || 'unknown' }} · {{ formatSize(file.size) }}</small>
          </button>
          <div v-if="!files.length" class="empty-file-list">
            项目解析完成后会在这里显示文件。
          </div>
          <div v-else-if="!filteredFiles.length" class="empty-file-list">
            没有匹配的文件。
          </div>
        </div>
      </aside>

      <section class="diagram-panel" aria-label="项目结构图">
        <div class="panel-titlebar">
          <div>
            <span>结构图谱</span>
            <strong>{{ diagramSummary }}</strong>
          </div>
          <small>可拖拽、缩放，点击节点可打开源码。</small>
        </div>
        <Diagram
          v-if="graphData"
          :graphData="graphData"
          :selectedPath="selectedPath"
          :highlightQuery="fileQuery"
          @nodeSelected="onNodeSelected"
        />
        <div v-else class="empty-state">
          <strong>等待项目输入</strong>
          <span>提交 Zip、本地路径或仓库地址后，这里会展示后端生成的代码结构图。</span>
        </div>
      </section>

      <section class="source-panel" aria-label="源码预览">
        <div class="source-header">
          <div>
            <span>源码预览</span>
            <strong>{{ selectedPath || '未选择文件' }}</strong>
          </div>
          <div class="source-badges">
            <span v-if="sourceLanguage">{{ sourceLanguage }}</span>
            <span v-if="sourceTruncated">已截断</span>
            <span v-if="highlightedLanguage">{{ highlightedLanguage }}</span>
          </div>
        </div>
        <pre class="code-view"><code :class="highlightClass" v-html="highlightedSource"></code></pre>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github-dark.css'
import Diagram from './components/Diagram.vue'

type InputMode = 'zip' | 'local' | 'github' | 'gitee'

type GraphData = {
  groups?: Array<{ id: string; label: string; description?: string; color?: string }>
  nodes: Array<{
    id: string
    label: string
    type?: string
    path?: string
    description?: string
    shape?: string
    color?: string
    groupId?: string
    language?: string
  }>
  edges: Array<{ source: string; target: string; label?: string; type?: string; style?: string }>
}

type ProjectFile = {
  path: string
  name: string
  size: number
  language: string
}

type InputJob = {
  job_id: string
  status: 'queued' | 'running' | 'ready' | 'error'
  stage: string
  message: string
  current: number
  total: number
  progress: number
  project_id?: string
  result?: {
    project_id: string
    status: string
    g6?: GraphData
  }
  error?: string
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const modeOptions: Array<{ value: InputMode; label: string; hint: string }> = [
  { value: 'zip', label: 'Zip', hint: '上传压缩包' },
  { value: 'local', label: '本地路径', hint: '后端可访问' },
  { value: 'github', label: 'GitHub', hint: '公开仓库' },
  { value: 'gitee', label: 'Gitee', hint: '公开仓库' }
]

const mode = ref<InputMode>('zip')
const textInput = ref('')
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const error = ref('')
const projectId = ref('')
const graphData = ref<GraphData | null>(null)
const files = ref<ProjectFile[]>([])
const fileQuery = ref('')
const selectedPath = ref('')
const sourceContent = ref('')
const sourceLanguage = ref('')
const sourceTruncated = ref(false)
const job = ref<InputJob | null>(null)

const inputLabel = computed(() => (mode.value === 'zip' ? '选择项目 Zip 包' : '输入项目来源'))

const placeholder = computed(() => {
  if (mode.value === 'local') return '例如 D:\\project\\ReActFlow\\backend'
  if (mode.value === 'github') return 'https://github.com/owner/repo'
  return 'https://gitee.com/owner/repo'
})

const diagramSummary = computed(() => {
  if (!graphData.value) return '尚未生成'
  return `${graphData.value.nodes.length} 个节点 · ${graphData.value.edges.length} 条关系`
})

const filteredFiles = computed(() => {
  const query = fileQuery.value.trim().toLowerCase()
  if (!query) return files.value
  return files.value.filter((file) =>
    [file.name, file.path, file.language].some((value) => String(value || '').toLowerCase().includes(query))
  )
})

const highlightedLanguage = computed(() => normalizeLanguage(sourceLanguage.value, selectedPath.value))
const highlightClass = computed(() => (highlightedLanguage.value ? `language-${highlightedLanguage.value}` : 'language-plaintext'))

const highlightedSource = computed(() => {
  const code = sourceContent.value || '从图谱节点或文件索引中选择一个文件。'
  const language = highlightedLanguage.value
  try {
    if (language && hljs.getLanguage(language)) {
      return hljs.highlight(code, { language, ignoreIllegals: true }).value
    }
    return hljs.highlightAuto(code).value
  } catch {
    return escapeHtml(code)
  }
})

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

async function submit() {
  loading.value = true
  error.value = ''
  job.value = null
  resetProjectView()
  try {
    const createdJob = mode.value === 'zip' ? await submitZipJob() : await submitJsonJob()
    job.value = createdJob
    await pollJob(createdJob.job_id)
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc)
  } finally {
    loading.value = false
  }
}

function resetProjectView() {
  projectId.value = ''
  graphData.value = null
  files.value = []
  fileQuery.value = ''
  selectedPath.value = ''
  sourceContent.value = ''
  sourceLanguage.value = ''
  sourceTruncated.value = false
}

async function submitZipJob() {
  if (!selectedFile.value) {
    throw new Error('请选择一个 zip 文件。')
  }
  const body = await selectedFile.value.arrayBuffer()
  const response = await fetch(`${API_BASE}/input/zip/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/zip' },
    body
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<InputJob>
}

async function submitJsonJob() {
  const value = textInput.value.trim()
  if (!value) {
    throw new Error('请输入项目来源。')
  }
  const payload = mode.value === 'local' ? { dir_path: value } : { repo_url: value }
  const response = await fetch(`${API_BASE}/input/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: mode.value, payload })
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json() as Promise<InputJob>
}

async function pollJob(jobId: string) {
  while (true) {
    await wait(1000)
    const response = await fetch(`${API_BASE}/input/jobs/${jobId}`)
    if (!response.ok) throw new Error(await readError(response))
    const nextJob = (await response.json()) as InputJob
    job.value = nextJob
    if (nextJob.status === 'error') {
      throw new Error(nextJob.error || nextJob.message || '解析失败。')
    }
    if (nextJob.status === 'ready') {
      await applyJobResult(nextJob)
      return
    }
  }
}

async function applyJobResult(doneJob: InputJob) {
  const result = doneJob.result
  projectId.value = result?.project_id || doneJob.project_id || ''
  graphData.value = result?.g6 || null
  if (!graphData.value && projectId.value) {
    await loadDiagram(projectId.value)
  }
  if (projectId.value) {
    await loadFiles(projectId.value)
  }
}

async function loadDiagram(id: string) {
  const response = await fetch(`${API_BASE}/diagram/${id}`)
  if (!response.ok) {
    const message = await readError(response)
    throw new Error(message)
  }
  const diagram = await response.json()
  graphData.value = diagram.g6
}

async function loadFiles(id: string) {
  const response = await fetch(`${API_BASE}/projects/${id}/files`)
  if (!response.ok) {
    const message = await readError(response)
    throw new Error(message)
  }
  const payload = await response.json()
  files.value = payload.files || []
}

async function selectFile(path: string) {
  if (!projectId.value) return
  const response = await fetch(`${API_BASE}/projects/${projectId.value}/files/content?path=${encodeURIComponent(path)}`)
  if (!response.ok) {
    const message = await readError(response)
    throw new Error(message)
  }
  const payload = await response.json()
  selectedPath.value = payload.path
  sourceContent.value = payload.content
  sourceLanguage.value = payload.language || ''
  sourceTruncated.value = Boolean(payload.truncated)
}

function onNodeSelected(node: { path?: string }) {
  if (node.path) {
    selectFile(node.path).catch((exc) => {
      error.value = exc instanceof Error ? exc.message : String(exc)
    })
  }
}

function stageLabel(stage: string) {
  const labels: Record<string, string> = {
    queued: '排队中',
    input: '处理输入',
    extract: '提取项目',
    parse: '解析源码',
    ai: 'AI 增强',
    ai_skipped: '跳过 AI',
    diagram: '生成图谱',
    done: '已完成',
    error: '解析失败'
  }
  return labels[stage] || stage
}

function normalizeLanguage(language: string, path: string) {
  const value = language.toLowerCase()
  const suffix = path.split('.').pop()?.toLowerCase() || ''
  const aliases: Record<string, string> = {
    python: 'python',
    py: 'python',
    javascript: 'javascript',
    js: 'javascript',
    typescript: 'typescript',
    ts: 'typescript',
    tsx: 'typescript',
    jsx: 'javascript',
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    markdown: 'markdown',
    md: 'markdown',
    html: 'xml',
    vue: 'xml',
    css: 'css',
    scss: 'css',
    bash: 'bash',
    sh: 'bash',
    shell: 'bash',
    go: 'go',
    java: 'java',
    rust: 'rust',
    rs: 'rust',
    cpp: 'cpp',
    c: 'c'
  }
  return aliases[value] || aliases[suffix] || ''
}

function formatSize(size: number) {
  if (!Number.isFinite(size) || size <= 0) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function escapeHtml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function readError(response: Response) {
  try {
    const payload = await response.json()
    return payload.detail || payload.message || response.statusText
  } catch {
    return response.statusText
  }
}
</script>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  background: #0f172a;
}

:global(button),
:global(input) {
  font: inherit;
}

.app-shell {
  min-height: 100vh;
  color: #e5eef8;
  background:
    radial-gradient(circle at 18% 2%, rgba(45, 212, 191, 0.16), transparent 28rem),
    linear-gradient(135deg, #111827 0%, #162032 48%, #0f172a 100%);
  font-family: "Inter", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
  padding: 24px;
}

.hero-panel,
.control-panel,
.workspace-grid {
  width: min(1760px, 100%);
  margin: 0 auto;
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
  padding: 8px 0 22px;
}

.eyebrow,
.panel-titlebar span,
.source-header span {
  color: #7dd3fc;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  margin: 4px 0;
  font-size: clamp(34px, 5vw, 64px);
  line-height: 0.95;
}

.hero-summary {
  max-width: 760px;
  margin: 0;
  color: #b8c5d6;
  font-size: 17px;
  line-height: 1.7;
}

.status-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(108px, 1fr));
  gap: 10px;
}

.status-metric {
  min-height: 72px;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
}

.status-metric span,
.project-token span,
.progress-panel small,
.panel-titlebar small {
  color: #93a4b8;
  font-size: 12px;
}

.status-metric strong {
  display: block;
  margin-top: 8px;
  color: #f8fafc;
  font-size: 22px;
}

.control-panel {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.82);
  box-shadow: 0 28px 90px rgba(0, 0, 0, 0.22);
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.mode-tabs button,
.primary-action,
.file-list button {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 180ms ease, background 180ms ease, transform 180ms ease;
}

.mode-tabs button {
  display: grid;
  gap: 4px;
  min-height: 64px;
  padding: 12px 14px;
  color: #dbeafe;
  text-align: left;
  background: rgba(30, 41, 59, 0.68);
}

.mode-tabs button small {
  color: #94a3b8;
}

.mode-tabs button:hover,
.mode-tabs button.active {
  border-color: #2dd4bf;
  background: rgba(20, 184, 166, 0.13);
}

.mode-tabs button:focus-visible,
.primary-action:focus-visible,
.file-list button:focus-visible,
input:focus-visible {
  outline: 3px solid rgba(45, 212, 191, 0.35);
  outline-offset: 2px;
}

.input-row {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 150px;
  gap: 12px;
  align-items: end;
}

.input-field,
.file-search {
  display: grid;
  gap: 8px;
}

.input-field span,
.file-search span {
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 700;
}

input {
  min-height: 46px;
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 8px;
  padding: 0 14px;
  color: #f8fafc;
  background: rgba(2, 6, 23, 0.58);
}

input[type="file"] {
  padding: 10px 14px;
  color: #cbd5e1;
}

input::placeholder {
  color: #64748b;
}

.primary-action {
  min-height: 46px;
  color: #042f2e;
  font-weight: 800;
  background: #5eead4;
  border-color: #5eead4;
}

.primary-action:hover {
  transform: translateY(-1px);
}

.primary-action:disabled {
  cursor: wait;
  opacity: 0.58;
  transform: none;
}

.progress-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(251, 191, 36, 0.28);
  border-radius: 8px;
  background: rgba(120, 53, 15, 0.18);
}

.progress-line {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.progress-line div {
  display: grid;
  gap: 3px;
}

.progress-line span {
  color: #fbbf24;
  font-size: 12px;
  font-weight: 800;
}

.progress-line strong {
  color: #fff7ed;
}

.progress-line b {
  color: #fde68a;
  font-size: 20px;
}

progress {
  width: 100%;
  height: 10px;
  overflow: hidden;
  border: 0;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.65);
}

progress::-webkit-progress-bar {
  background: rgba(15, 23, 42, 0.65);
}

progress::-webkit-progress-value {
  border-radius: 999px;
  background: linear-gradient(90deg, #fbbf24, #2dd4bf);
}

.project-token {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.project-token code {
  color: #ccfbf1;
  background: rgba(20, 184, 166, 0.1);
  border: 1px solid rgba(45, 212, 191, 0.26);
  border-radius: 6px;
  padding: 4px 8px;
}

.error {
  margin: 0;
  color: #fecaca;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(250px, 320px) minmax(420px, 1fr) minmax(320px, 420px);
  gap: 16px;
  padding-top: 16px;
  align-items: start;
}

.file-panel,
.diagram-panel,
.source-panel {
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.74);
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.2);
}

.file-panel,
.source-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  height: 677px;
  overflow: hidden;
}

.diagram-panel {
  overflow: hidden;
}

.panel-titlebar,
.source-header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  padding: 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.panel-titlebar > div,
.source-header > div:first-child {
  display: grid;
  gap: 4px;
}

.panel-titlebar strong,
.source-header strong {
  color: #f8fafc;
  font-size: 15px;
}

.file-search {
  padding: 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.file-list {
  min-height: 0;
  overflow: auto;
  padding: 10px;
}

.file-list button {
  display: grid;
  gap: 5px;
  width: 100%;
  margin-bottom: 8px;
  padding: 11px;
  color: #dbeafe;
  text-align: left;
  background: rgba(30, 41, 59, 0.56);
}

.file-list button:hover,
.file-list button.selected {
  border-color: #5eead4;
  background: rgba(20, 184, 166, 0.13);
}

.file-list button strong,
.file-list button span,
.file-list button small {
  overflow-wrap: anywhere;
}

.file-list button span {
  color: #94a3b8;
  font-size: 12px;
}

.file-list button small {
  color: #7dd3fc;
  font-size: 11px;
}

.empty-file-list,
.empty-state {
  color: #94a3b8;
  text-align: center;
}

.empty-file-list {
  padding: 28px 12px;
  line-height: 1.6;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 620px;
  padding: 24px;
}

.empty-state strong {
  display: block;
  margin-bottom: 8px;
  color: #e2e8f0;
  font-size: 20px;
}

.source-panel {
  grid-template-rows: auto minmax(0, 1fr);
}

.source-header {
  align-items: start;
}

.source-header strong {
  overflow-wrap: anywhere;
}

.source-badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.source-badges span {
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 999px;
  padding: 3px 8px;
  color: #bfdbfe;
  background: rgba(14, 165, 233, 0.12);
  text-transform: none;
}

.code-view {
  margin: 0;
  min-height: 0;
  height: 100%;
  overflow: auto;
  background: #07111f;
}

.code-view code {
  display: block;
  min-height: 100%;
  padding: 16px;
  white-space: pre;
  font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.7;
}

@media (prefers-reduced-motion: reduce) {
  * {
    transition-duration: 0.01ms !important;
  }
}

@media (max-width: 1280px) {
  .workspace-grid {
    grid-template-columns: minmax(250px, 320px) minmax(420px, 1fr);
  }

  .source-panel {
    grid-column: 1 / -1;
    height: 520px;
  }
}

@media (max-width: 900px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .file-panel {
    height: 420px;
  }
}

@media (max-width: 780px) {
  .app-shell {
    padding: 16px;
  }

  .hero-panel,
  .input-row,
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .mode-tabs,
  .status-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .mode-tabs,
  .status-strip {
    grid-template-columns: 1fr;
  }

  .panel-titlebar,
  .source-header {
    display: grid;
  }
}
</style>
