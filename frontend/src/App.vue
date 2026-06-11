<template>
  <main class="app-shell">
    <section class="control-panel">
      <div>
        <h1>ReActFlow</h1>
        <p>提交项目输入，生成可点击的代码流程图。</p>
      </div>

      <div class="mode-tabs">
        <button :class="{ active: mode === 'zip' }" @click="mode = 'zip'">Zip</button>
        <button :class="{ active: mode === 'local' }" @click="mode = 'local'">本地路径</button>
        <button :class="{ active: mode === 'github' }" @click="mode = 'github'">GitHub</button>
        <button :class="{ active: mode === 'gitee' }" @click="mode = 'gitee'">Gitee</button>
      </div>

      <form class="input-row" @submit.prevent="submit">
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
        />
        <button type="submit" :disabled="loading">{{ loading ? '解析中' : '开始解析' }}</button>
      </form>

      <div v-if="job" class="progress-panel">
        <div class="progress-line">
          <strong>{{ job.message }}</strong>
          <span>{{ job.progress }}%</span>
        </div>
        <progress :value="job.progress" max="100"></progress>
        <small>阶段：{{ stageLabel(job.stage) }} · {{ job.current }} / {{ job.total }}</small>
      </div>

      <div v-if="projectId" class="meta">
        <span>Project ID</span>
        <code>{{ projectId }}</code>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section v-if="projectId" class="workspace">
      <aside class="file-panel">
        <input v-model="fileQuery" type="text" placeholder="搜索文件、语言或节点" />
        <div class="file-count">{{ filteredFiles.length }} / {{ files.length }} 文件</div>
        <button
          v-for="file in filteredFiles"
          :key="file.path"
          class="file-item"
          :class="{ selected: selectedPath === file.path }"
          type="button"
          @click="selectFile(file.path)"
        >
          <span>{{ file.path }}</span>
          <small>{{ file.language || '文本' }} · {{ file.size }} B</small>
        </button>
      </aside>

      <section class="source-panel">
        <div class="source-header">
          <strong>{{ selectedPath || '未选择文件' }}</strong>
          <span v-if="sourceLanguage">{{ sourceLanguage }}</span>
          <span v-if="sourceTruncated">已截断</span>
        </div>
        <pre>{{ sourceContent || '从左侧文件列表或图中节点选择一个文件。' }}</pre>
      </section>
    </section>

    <section class="diagram-panel">
      <Diagram
        v-if="graphData"
        :graphData="graphData"
        :highlightQuery="fileQuery"
        :selectedPath="selectedPath"
        @nodeSelected="onNodeSelected"
      />
      <div v-else class="empty-state">提交项目后，这里会显示后端生成的流程图。</div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Diagram from './components/Diagram.vue'

type InputMode = 'zip' | 'local' | 'github' | 'gitee'

type GraphData = {
  nodes: Array<{ id: string; label: string; type?: string; path?: string; description?: string }>
  edges: Array<{ source: string; target: string; label?: string }>
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

const placeholder = computed(() => {
  if (mode.value === 'local') return '输入后端服务可访问的本地目录路径'
  if (mode.value === 'github') return 'https://github.com/owner/repo'
  return 'https://gitee.com/owner/repo'
})

const filteredFiles = computed(() => {
  const query = fileQuery.value.trim().toLowerCase()
  if (!query) return files.value
  return files.value.filter((file) => `${file.path} ${file.language}`.toLowerCase().includes(query))
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
  selectedPath.value = ''
  sourceContent.value = ''
  sourceLanguage.value = ''
  sourceTruncated.value = false
}

async function submitZipJob() {
  if (!selectedFile.value) {
    throw new Error('请选择一个 zip 文件')
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
    throw new Error('请输入项目来源')
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
      throw new Error(nextJob.error || nextJob.message || '解析失败')
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
    queued: '排队',
    input: '处理输入',
    extract: '解压/克隆',
    parse: '解析源码',
    ai: 'AI 增强',
    ai_skipped: '跳过 AI',
    diagram: '生成图谱',
    done: '完成',
    error: '失败'
  }
  return labels[stage] || stage
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
.app-shell {
  min-height: 100vh;
  background: #eef2f6;
  color: #172b4d;
  font-family: "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;
}

.control-panel {
  display: grid;
  gap: 14px;
  padding: 22px 28px;
  background: #ffffff;
  border-bottom: 1px solid #dfe3e8;
}

h1 {
  margin: 0;
  font-size: 24px;
}

p {
  margin: 6px 0 0;
  color: #5e6c84;
}

.mode-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mode-tabs button,
.input-row button {
  border: 1px solid #c8d1dc;
  background: #ffffff;
  color: #172b4d;
  min-height: 36px;
  padding: 0 14px;
  cursor: pointer;
}

.mode-tabs button.active,
.input-row button {
  background: #1264a3;
  border-color: #1264a3;
  color: #ffffff;
}

.input-row {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto;
  gap: 10px;
}

.input-row input {
  min-height: 36px;
  border: 1px solid #c8d1dc;
  padding: 0 10px;
  background: #ffffff;
}

.input-row button:disabled {
  opacity: 0.65;
  cursor: wait;
}

.progress-panel {
  display: grid;
  gap: 6px;
  max-width: 760px;
}

.progress-line {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

progress {
  width: 100%;
  height: 14px;
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #5e6c84;
}

.meta code {
  color: #172b4d;
  background: #eef2f6;
  padding: 3px 6px;
}

.error {
  color: #b42318;
}

.workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 12px;
  padding: 18px 18px 0;
}

.file-panel,
.source-panel {
  background: #ffffff;
  border: 1px solid #dfe3e8;
  min-height: 280px;
}

.file-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  max-height: 420px;
  overflow: auto;
}

.file-panel input {
  min-height: 34px;
  border: 1px solid #c8d1dc;
  padding: 0 8px;
}

.file-count {
  color: #5e6c84;
  font-size: 12px;
}

.file-item {
  display: grid;
  gap: 2px;
  text-align: left;
  border: 1px solid #dfe3e8;
  background: #ffffff;
  padding: 7px;
  cursor: pointer;
}

.file-item.selected {
  border-color: #1264a3;
  background: #eef6ff;
}

.file-item small {
  color: #5e6c84;
}

.source-panel {
  min-width: 0;
}

.source-header {
  display: flex;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #dfe3e8;
  color: #172b4d;
}

.source-panel pre {
  margin: 0;
  padding: 10px;
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}

.diagram-panel {
  padding: 18px;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 620px;
  border: 1px dashed #a7b2bf;
  background: #ffffff;
  color: #5e6c84;
}

@media (max-width: 720px) {
  .input-row {
    grid-template-columns: 1fr;
  }

  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
