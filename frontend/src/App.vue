<template>
  <main class="app-shell">
    <section class="control-panel">
      <div>
        <h1>ReActFlow</h1>
        <p>提交项目输入，生成真实代码流程图。</p>
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
        <button type="submit" :disabled="loading">{{ loading ? '生成中' : '生成流程图' }}</button>
      </form>

      <div v-if="projectId" class="meta">
        <span>Project ID</span>
        <code>{{ projectId }}</code>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section class="diagram-panel">
      <Diagram v-if="graphData" :graphData="graphData" />
      <div v-else class="empty-state">提交一个项目后，这里会显示由后端生成的流程图。</div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Diagram from './components/Diagram.vue'

type InputMode = 'zip' | 'local' | 'github' | 'gitee'

type GraphData = {
  nodes: Array<{ id: string; label: string; type?: string }>
  edges: Array<{ source: string; target: string; label?: string }>
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const mode = ref<InputMode>('zip')
const textInput = ref('')
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const error = ref('')
const projectId = ref('')
const graphData = ref<GraphData | null>(null)

const placeholder = computed(() => {
  if (mode.value === 'local') return '输入后端服务器可访问的本地目录路径'
  if (mode.value === 'github') return 'https://github.com/owner/repo'
  return 'https://gitee.com/owner/repo'
})

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const response = mode.value === 'zip' ? await submitZip() : await submitJson()
    if (!response.ok) {
      const message = await readError(response)
      throw new Error(message)
    }
    const created = await response.json()
    projectId.value = created.project_id
    graphData.value = created.g6
    if (!graphData.value && projectId.value) {
      await loadDiagram(projectId.value)
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc)
  } finally {
    loading.value = false
  }
}

async function submitZip() {
  if (!selectedFile.value) {
    throw new Error('请选择一个 zip 文件')
  }
  const body = await selectedFile.value.arrayBuffer()
  return fetch(`${API_BASE}/input/zip`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/zip' },
    body
  })
}

async function submitJson() {
  const value = textInput.value.trim()
  if (!value) {
    throw new Error('请输入项目来源')
  }
  const payload =
    mode.value === 'local'
      ? { dir_path: value }
      : { repo_url: value }
  return fetch(`${API_BASE}/input`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: mode.value, payload })
  })
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
}
</style>
