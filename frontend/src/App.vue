<template>
  <main class="app-shell">
    <section class="top-workbench" aria-labelledby="app-title">
      <div class="brand-block">
        <p class="eyebrow">跨语言项目结构图谱</p>
        <h1 id="app-title">ReActFlow</h1>
      </div>

      <form class="input-console" aria-label="项目解析" @submit.prevent="submit">
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
            {{ option.label }}
          </button>
        </div>

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
          {{ loading ? '解析中' : '生成图谱' }}
        </button>
      </form>
    </section>

    <section v-if="job || projectId || error" class="status-row" aria-live="polite">
      <div v-if="job" class="progress-panel">
        <div>
          <span>{{ stageLabel(job.stage) }}</span>
          <strong>{{ job.message }}</strong>
        </div>
        <progress :value="job.progress" max="100"></progress>
        <b>{{ job.progress }}%</b>
      </div>
      <div v-if="projectId" class="project-token">
        <span>Project ID</span>
        <code>{{ projectId }}</code>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </section>

    <section class="graph-workspace" :class="{ 'drawer-open': sourceDrawerOpen }" aria-label="代码图谱工作区">
      <section class="diagram-stage" aria-label="项目结构图">
        <div class="stage-toolbar">
          <div>
            <span>结构图谱</span>
            <strong>{{ diagramSummary }}</strong>
          </div>
          <div class="toolbar-actions">
            <label class="drag-toggle">
              <input v-model="nodeDragEnabled" type="checkbox" />
              <span>节点拖拽</span>
            </label>
            <button type="button" class="ghost-action" @click="searchOpen = true">
              搜索文件
            </button>
            <button type="button" class="ghost-action" :disabled="!selectedPath" @click="sourceDrawerOpen = !sourceDrawerOpen">
              {{ sourceDrawerOpen ? '收起源码' : '源码预览' }}
            </button>
          </div>
        </div>

        <Diagram
          v-if="graphData"
          :graphData="graphData"
          :selectedPath="selectedPath"
          :highlightQuery="fileQuery"
          :nodeDragEnabled="nodeDragEnabled"
          @nodeSelected="onNodeSelected"
        />
        <div v-else class="empty-state">
          <strong>选择项目来源后生成结构图谱</strong>
          <span>Zip、本地目录、GitHub 和 Gitee 都可输入；无 API Key 时也会生成静态兜底图谱。</span>
        </div>
      </section>

      <aside class="source-drawer" :class="{ open: sourceDrawerOpen }" aria-label="源码预览">
        <button
          type="button"
          class="drawer-handle"
          aria-label="完整显示源码预览"
          title="完整显示源码预览"
          @click="sourcePreviewMaximized = true"
        >
          ⤢
        </button>
        <div class="source-header">
          <div>
            <span>源码预览</span>
            <strong>{{ selectedPath || '未选择文件' }}</strong>
          </div>
          <button type="button" class="icon-action" aria-label="关闭源码预览" @click="sourceDrawerOpen = false">
            ×
          </button>
        </div>
        <div class="source-badges">
          <span v-if="sourceLanguage">{{ sourceLanguage }}</span>
          <span v-if="sourceTruncated">已截断</span>
          <span v-if="highlightedLanguage">{{ highlightedLanguage }}</span>
        </div>
        <dl v-if="selectedNodeMeta" class="source-meta">
          <div>
            <dt>说明</dt>
            <dd>{{ selectedNodeMeta.description || '项目主体源码文件' }}</dd>
          </div>
          <div>
            <dt>模块</dt>
            <dd>{{ selectedNodeMeta.module || selectedNodeMeta.groupId || '未分组' }}</dd>
          </div>
          <div>
            <dt>大小</dt>
            <dd>{{ formatSize(selectedNodeMeta.size || 0) }}</dd>
          </div>
        </dl>
        <div class="code-view">
          <div class="code-rows" :class="highlightClass">
            <div v-for="(line, index) in highlightedRows" :key="index" class="code-row">
              <span class="line-number">{{ index + 1 }}</span>
              <code v-html="line || '&nbsp;'"></code>
            </div>
          </div>
        </div>
      </aside>
    </section>

    <div v-if="sourcePreviewMaximized" class="source-fullscreen" role="dialog" aria-modal="true" aria-label="完整源码预览">
      <section class="source-fullscreen-panel">
        <div class="source-header">
          <div>
            <span>完整源码预览</span>
            <strong>{{ selectedPath || '未选择文件' }}</strong>
          </div>
          <button type="button" class="icon-action" aria-label="关闭完整源码预览" @click="sourcePreviewMaximized = false">
            ×
          </button>
        </div>
        <div class="source-badges">
          <span v-if="sourceLanguage">{{ sourceLanguage }}</span>
          <span v-if="sourceTruncated">已截断</span>
          <span v-if="highlightedLanguage">{{ highlightedLanguage }}</span>
        </div>
        <div class="code-view fullscreen-code">
          <div class="code-rows" :class="highlightClass">
            <div v-for="(line, index) in highlightedRows" :key="index" class="code-row">
              <span class="line-number">{{ index + 1 }}</span>
              <code v-html="line || '&nbsp;'"></code>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div v-if="searchOpen" class="search-overlay" role="dialog" aria-modal="true" aria-label="文件搜索">
      <div class="search-panel">
        <div class="search-header">
          <div>
            <span>文件搜索</span>
            <strong>{{ filteredFiles.length }} / {{ files.length }}</strong>
          </div>
          <button type="button" class="icon-action" aria-label="关闭文件搜索" @click="searchOpen = false">×</button>
        </div>
        <label class="search-field">
          <span>搜索文件名、路径、语言或模块</span>
          <input ref="searchInput" v-model="fileQuery" type="search" placeholder="例如 App.vue、backend、Python" />
        </label>
        <div class="result-list">
          <button
            v-for="file in filteredFiles"
            :key="file.path"
            type="button"
            :class="{ selected: selectedPath === file.path }"
            @click="selectFileFromSearch(file.path)"
          >
            <strong>{{ file.name }}</strong>
            <span>{{ file.path }}</span>
            <small>{{ file.language || 'unknown' }} · {{ formatSize(file.size) }}</small>
          </button>
          <p v-if="!files.length">项目解析完成后可以在这里搜索所有源码文件。</p>
          <p v-else-if="!filteredFiles.length">没有匹配的文件。</p>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/atom-one-dark.css'
import Diagram from './components/Diagram.vue'

type InputMode = 'zip' | 'local' | 'github' | 'gitee'

type GraphData = {
  groups?: Array<{ id: string; label: string; description?: string; color?: string }>
  nodes: Array<{
    id: string
    label: string
    filename?: string
    type?: string
    path?: string
    description?: string
    shape?: string
    color?: string
    groupId?: string
    module?: string
    language?: string
    isFile?: boolean
    nodeKind?: string
    size?: number
  }>
  edges: Array<{ source: string; target: string; label?: string; type?: string; relation?: string; style?: string }>
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

const modeOptions: Array<{ value: InputMode; label: string }> = [
  { value: 'zip', label: 'Zip' },
  { value: 'local', label: '本地路径' },
  { value: 'github', label: 'GitHub' },
  { value: 'gitee', label: 'Gitee' }
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
const sourceDrawerOpen = ref(false)
const sourcePreviewMaximized = ref(false)
const nodeDragEnabled = ref(false)
const selectedNodeMeta = ref<GraphData['nodes'][number] | null>(null)
const searchOpen = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)
const job = ref<InputJob | null>(null)

const inputLabel = computed(() => (mode.value === 'zip' ? '选择项目 Zip 包' : '输入项目来源'))

const placeholder = computed(() => {
  if (mode.value === 'local') return '例如 D:\\project\\ReActFlow'
  if (mode.value === 'github') return 'https://github.com/owner/repo'
  return 'https://gitee.com/owner/repo'
})

const diagramSummary = computed(() => {
  if (!graphData.value) return '尚未生成'
  const fileNodes = graphData.value.nodes.filter((node) => node.isFile || node.path)
  return `${fileNodes.length} 个文件节点 · ${graphData.value.edges.length} 条关系`
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
  const code = sourceContent.value || '从图谱节点或文件搜索中选择一个文件。'
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

const highlightedRows = computed(() => highlightedSource.value.split(/\r?\n/))

watch(searchOpen, async (open) => {
  if (!open) return
  await nextTick()
  searchInput.value?.focus()
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
  selectedNodeMeta.value = null
  sourceDrawerOpen.value = false
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
  if (!response.ok) throw new Error(await readError(response))
  const diagram = await response.json()
  graphData.value = diagram.g6
}

async function loadFiles(id: string) {
  const response = await fetch(`${API_BASE}/projects/${id}/files`)
  if (!response.ok) throw new Error(await readError(response))
  const payload = await response.json()
  files.value = payload.files || []
}

async function selectFile(path: string) {
  if (!projectId.value) return
  selectedNodeMeta.value = findGraphNode(path)
  const response = await fetch(`${API_BASE}/projects/${projectId.value}/files/content?path=${encodeURIComponent(path)}`)
  if (!response.ok) throw new Error(await readError(response))
  const payload = await response.json()
  selectedPath.value = payload.path
  sourceContent.value = payload.content
  sourceLanguage.value = payload.language || ''
  sourceTruncated.value = Boolean(payload.truncated)
  sourceDrawerOpen.value = true
}

function selectFileFromSearch(path: string) {
  fileQuery.value = path
  searchOpen.value = false
  selectFile(path).catch((exc) => {
    error.value = exc instanceof Error ? exc.message : String(exc)
  })
}

function onNodeSelected(node: GraphData['nodes'][number]) {
  if (node.path && !node.path.endsWith('/')) {
    selectedNodeMeta.value = node
    selectFile(node.path).catch((exc) => {
      error.value = exc instanceof Error ? exc.message : String(exc)
    })
  }
}

function findGraphNode(path: string) {
  return graphData.value?.nodes.find((node) => node.path === path) || null
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
  background: #eef5fb;
}

:global(html),
:global(body),
:global(#app) {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}

:global(button),
:global(input) {
  font: inherit;
}

.app-shell {
  width: 100%;
  max-width: 100%;
  min-height: 100vh;
  overflow-x: hidden;
  color: #172033;
  background:
    radial-gradient(circle at 15% 0%, rgba(14, 165, 233, 0.14), transparent 30rem),
    linear-gradient(180deg, #f8fbff 0%, #eef5fb 100%);
  font-family: "Inter", "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
  padding: 16px;
}

.top-workbench,
.status-row,
.graph-workspace {
  width: min(1800px, 100%);
  margin: 0 auto;
}

.top-workbench {
  display: grid;
  grid-template-columns: minmax(180px, 260px) minmax(0, 1fr);
  gap: 16px;
  align-items: end;
}

.brand-block {
  display: grid;
  gap: 3px;
}

.eyebrow,
.stage-toolbar span,
.source-header span,
.search-header span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

h1 {
  margin: 0;
  color: #0f172a;
  font-size: 32px;
  line-height: 1;
}

.input-console {
  display: grid;
  grid-template-columns: 320px minmax(260px, 1fr) 112px;
  gap: 10px;
  align-items: end;
  padding: 12px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(14px);
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.mode-tabs button,
.primary-action,
.ghost-action,
.icon-action,
.result-list button {
  min-height: 44px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease, transform 180ms ease, box-shadow 180ms ease;
}

.mode-tabs button {
  border: 1px solid #d9e4ef;
  color: #475569;
  background: #f8fafc;
}

.mode-tabs button.active,
.mode-tabs button:hover {
  border-color: #0ea5e9;
  color: #075985;
  background: #e0f2fe;
}

.input-field,
.search-field {
  display: grid;
  gap: 6px;
}

.input-field span,
.search-field span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

input {
  width: 100%;
  min-height: 44px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 12px;
  color: #172033;
  background: #ffffff;
}

input[type="file"] {
  padding: 9px 12px;
}

input:focus-visible,
button:focus-visible {
  outline: 3px solid rgba(14, 165, 233, 0.28);
  outline-offset: 2px;
}

.primary-action {
  border: 1px solid #14b8a6;
  color: #ffffff;
  font-weight: 800;
  background: linear-gradient(135deg, #14b8a6, #0ea5e9);
  box-shadow: 0 12px 22px rgba(14, 165, 233, 0.18);
}

.primary-action:hover,
.ghost-action:hover,
.result-list button:hover {
  transform: translateY(-1px);
}

.primary-action:disabled,
.ghost-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding-top: 12px;
}

.progress-panel,
.project-token {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: 44px;
  border: 1px solid rgba(14, 165, 233, 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.82);
}

.progress-panel div {
  display: grid;
  gap: 2px;
  min-width: 220px;
}

.progress-panel span,
.project-token span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.progress-panel strong {
  color: #172033;
  font-size: 13px;
}

.progress-panel b {
  color: #0f766e;
}

progress {
  width: 160px;
  height: 8px;
  overflow: hidden;
  border: 0;
  border-radius: 999px;
}

progress::-webkit-progress-bar {
  background: #dbeafe;
}

progress::-webkit-progress-value {
  border-radius: 999px;
  background: linear-gradient(90deg, #14b8a6, #0ea5e9);
}

.project-token code {
  color: #075985;
  font-weight: 700;
}

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 700;
}

.graph-workspace {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-height: calc(100vh - 116px);
  padding-top: 8px;
}

.diagram-stage {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: calc(100vh - 128px);
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.11);
}

.stage-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  min-height: 58px;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
  background: rgba(248, 250, 252, 0.88);
}

.stage-toolbar > div:first-child,
.source-header > div,
.search-header > div {
  display: grid;
  gap: 3px;
}

.stage-toolbar strong,
.source-header strong,
.search-header strong {
  color: #0f172a;
  font-size: 15px;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.ghost-action {
  border: 1px solid #cbd5e1;
  padding: 0 14px;
  color: #334155;
  font-weight: 700;
  background: #ffffff;
}

.drag-toggle {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  min-height: 44px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 12px;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
  background: #ffffff;
}

.drag-toggle input {
  width: 16px;
  min-height: 16px;
  accent-color: #0ea5e9;
}

.empty-state {
  flex: 1;
  display: grid;
  place-items: center;
  min-height: calc(100vh - 188px);
  padding: 28px;
  color: #64748b;
  text-align: center;
  background:
    linear-gradient(rgba(148, 163, 184, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.1) 1px, transparent 1px),
    #f8fbff;
  background-size: 28px 28px;
}

.empty-state strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
  font-size: 22px;
}

.source-drawer {
  position: absolute;
  top: 12px;
  right: 0;
  z-index: 20;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  width: min(460px, calc(100vw - 32px));
  height: calc(72vh + 58px);
  min-height: 698px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.16);
  border-radius: 8px;
  background: #282c34;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
  opacity: 0;
  pointer-events: none;
  transform: translateX(32px);
  visibility: hidden;
  transition: transform 220ms ease, opacity 180ms ease, visibility 180ms ease;
}

.source-drawer.open {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(0);
  visibility: visible;
}

.drawer-handle {
  position: absolute;
  top: 82px;
  left: -34px;
  width: 34px;
  min-height: 74px;
  border: 1px solid rgba(15, 23, 42, 0.18);
  border-right: 0;
  border-radius: 8px 0 0 8px;
  color: #abb2bf;
  cursor: pointer;
  background: #21252b;
  box-shadow: -8px 12px 24px rgba(15, 23, 42, 0.18);
}

.source-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 13px;
  border-bottom: 1px solid rgba(171, 178, 191, 0.16);
}

.source-header span {
  color: #61afef;
}

.source-header strong {
  color: #abb2bf;
  overflow-wrap: anywhere;
}

.icon-action {
  min-width: 44px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  color: inherit;
  font-size: 22px;
  background: rgba(255, 255, 255, 0.08);
}

.source-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 13px;
  border-bottom: 1px solid rgba(171, 178, 191, 0.14);
}

.source-badges span {
  border: 1px solid rgba(97, 175, 239, 0.28);
  border-radius: 999px;
  padding: 3px 8px;
  color: #61afef;
  font-size: 12px;
  background: rgba(97, 175, 239, 0.1);
}

.source-meta {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 11px 13px;
  border-bottom: 1px solid rgba(171, 178, 191, 0.14);
  color: #abb2bf;
  background: rgba(255, 255, 255, 0.03);
}

.source-meta div {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 8px;
}

.source-meta dt,
.source-meta dd {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
}

.source-meta dt {
  color: #61afef;
  font-weight: 800;
}

.source-meta dd {
  overflow-wrap: anywhere;
}

.code-view {
  margin: 0;
  min-height: 0;
  height: 100%;
  overflow: auto;
  color: #abb2bf;
  background: #282c34;
  scrollbar-color: #4b5263 #21252b;
}

.code-rows {
  display: table;
  min-width: max-content;
  min-height: 100%;
  width: 100%;
  padding: 12px 0;
  color: #abb2bf;
  background: #282c34;
  font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.65;
  tab-size: 4;
}

.code-row {
  display: table-row;
}

.code-row:hover {
  background: rgba(97, 175, 239, 0.08);
}

.line-number,
.code-row code {
  display: table-cell;
  white-space: pre;
}

.line-number {
  user-select: none;
  width: 58px;
  padding: 0 14px 0 8px;
  color: #636d83;
  text-align: right;
  background: #282c34;
  border-right: 1px solid rgba(99, 109, 131, 0.28);
}

.code-row code {
  min-width: 100%;
  padding: 0 24px 0 16px;
  font-family: "JetBrains Mono", Consolas, "Courier New", monospace;
}

.code-view :deep(.hljs) {
  color: #abb2bf;
  background: transparent;
}

.code-view :deep(.hljs-keyword),
.code-view :deep(.hljs-selector-tag),
.code-view :deep(.hljs-built_in),
.code-view :deep(.hljs-name) {
  color: #c678dd;
}

.code-view :deep(.hljs-string),
.code-view :deep(.hljs-title.class_),
.code-view :deep(.hljs-section),
.code-view :deep(.hljs-attribute) {
  color: #98c379;
}

.code-view :deep(.hljs-title.function_),
.code-view :deep(.hljs-function .hljs-title),
.code-view :deep(.hljs-property),
.code-view :deep(.hljs-attr) {
  color: #61afef;
}

.code-view :deep(.hljs-number),
.code-view :deep(.hljs-literal),
.code-view :deep(.hljs-symbol) {
  color: #d19a66;
}

.code-view :deep(.hljs-variable),
.code-view :deep(.hljs-template-variable),
.code-view :deep(.hljs-params),
.code-view :deep(.hljs-meta) {
  color: #e06c75;
}

.code-view :deep(.hljs-comment),
.code-view :deep(.hljs-quote) {
  color: #5c6370;
  font-style: italic;
}

.source-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.58);
  backdrop-filter: blur(12px);
}

.source-fullscreen-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  width: min(1500px, 96vw);
  height: min(920px, 92vh);
  overflow: hidden;
  border: 1px solid rgba(171, 178, 191, 0.2);
  border-radius: 8px;
  background: #282c34;
  box-shadow: 0 34px 120px rgba(15, 23, 42, 0.42);
}

.fullscreen-code .code-rows {
  font-size: 14px;
  line-height: 1.7;
}

.search-overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: start center;
  padding: 10vh 16px 16px;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(8px);
}

.search-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  width: min(720px, 100%);
  max-height: min(720px, 80vh);
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 28px 90px rgba(15, 23, 42, 0.24);
}

.search-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 14px;
  border-bottom: 1px solid #e2e8f0;
}

.search-field {
  padding: 14px;
  border-bottom: 1px solid #e2e8f0;
}

.result-list {
  min-height: 0;
  overflow: auto;
  padding: 10px;
}

.result-list button {
  display: grid;
  gap: 5px;
  width: 100%;
  margin-bottom: 8px;
  border: 1px solid #e2e8f0;
  padding: 11px;
  color: #172033;
  text-align: left;
  background: #ffffff;
}

.result-list button.selected,
.result-list button:hover {
  border-color: #0ea5e9;
  background: #f0f9ff;
}

.result-list button span,
.result-list button small {
  color: #64748b;
  overflow-wrap: anywhere;
}

.result-list button small,
.result-list p {
  font-size: 12px;
}

.result-list p {
  margin: 28px 8px;
  color: #64748b;
  text-align: center;
}

@media (prefers-reduced-motion: reduce) {
  * {
    transition-duration: 0.01ms !important;
  }
}

@media (max-width: 1120px) {
  .top-workbench,
  .input-console {
    grid-template-columns: 1fr;
  }

  .source-drawer {
    height: 620px;
    min-height: 0;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 10px;
  }

  .mode-tabs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stage-toolbar,
  .progress-panel {
    display: grid;
  }

  .source-drawer {
    position: fixed;
    top: auto;
    right: 10px;
    bottom: 10px;
    left: 10px;
    width: auto;
    height: 70vh;
    transform: translateY(calc(100% + 18px));
  }

  .drawer-handle {
    top: -34px;
    left: auto;
    right: 18px;
    width: 76px;
    min-height: 34px;
    border-right: 1px solid rgba(15, 23, 42, 0.18);
    border-bottom: 0;
    border-radius: 8px 8px 0 0;
  }

  .source-drawer.open {
    transform: translateY(0);
  }
}
</style>
