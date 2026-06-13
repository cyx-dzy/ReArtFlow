<template>
  <div ref="container" class="diagram-container" aria-label="代码结构图谱"></div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import G6 from '@antv/g6'

type GraphNode = {
  id: string
  label: string
  filename?: string
  type?: string
  language?: string
  path?: string
  shape?: string
  color?: string
  description?: string
  groupId?: string
  module?: string
  isFile?: boolean
  nodeKind?: string
  size?: number
}

type GraphEdge = {
  source: string
  target: string
  label?: string
  type?: string
  relation?: string
  style?: string
  description?: string
}

type GraphGroup = {
  id: string
  label: string
  description?: string
  color?: string
}

type GraphData = {
  groups?: GraphGroup[]
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const props = defineProps<{
  graphData: GraphData
  selectedPath?: string
  highlightQuery?: string
  nodeDragEnabled?: boolean
}>()

const emit = defineEmits<{
  (event: 'nodeSelected', node: GraphNode): void
}>()

const container = ref<HTMLElement | null>(null)
let graph: any = null
let resizeObserver: ResizeObserver | null = null
let customNodesRegistered = false

function registerCustomNodes() {
  if (customNodesRegistered) return
  customNodesRegistered = true

  G6.registerNode(
    'file-card',
    {
      draw(cfg: any, group: any) {
        const size = cfg.size || [190, 64]
        const width = Array.isArray(size) ? size[0] : size
        const height = Array.isArray(size) ? size[1] : size
        const x = -width / 2
        const y = -height / 2
        const accent = cfg.accent || cfg.style?.stroke || '#0ea5e9'
        const keyShape = group.addShape('rect', {
          attrs: {
            x,
            y,
            width,
            height,
            radius: 6,
            fill: cfg.style?.fill || '#ffffff',
            stroke: cfg.style?.stroke || '#d8dee9',
            lineWidth: cfg.style?.lineWidth || 1.2,
            shadowColor: 'rgba(15, 23, 42, 0.08)',
            shadowBlur: 12,
            shadowOffsetY: 5
          },
          name: 'file-card'
        })
        group.addShape('rect', {
          attrs: { x, y, width: 5, height, radius: [6, 0, 0, 6], fill: accent },
          name: 'accent'
        })
        group.addShape('text', {
          attrs: {
            text: cfg.fileName,
            x: x + 16,
            y: y + 22,
            textAlign: 'left',
            textBaseline: 'middle',
            fill: '#172033',
            fontSize: 12,
            fontWeight: 800,
            fontFamily: 'Inter, Microsoft YaHei, Noto Sans SC, sans-serif'
          },
          name: 'filename'
        })
        group.addShape('text', {
          attrs: {
            text: cfg.descriptionText,
            x: x + 16,
            y: y + 44,
            textAlign: 'left',
            textBaseline: 'middle',
            fill: '#64748b',
            fontSize: 11,
            fontFamily: 'Inter, Microsoft YaHei, Noto Sans SC, sans-serif'
          },
          name: 'description'
        })
        return keyShape
      }
    },
    'single-node'
  )

  G6.registerNode(
    'database-card',
    {
      draw(cfg: any, group: any) {
        const size = cfg.size || [184, 68]
        const width = Array.isArray(size) ? size[0] : size
        const height = Array.isArray(size) ? size[1] : size
        const x = -width / 2
        const y = -height / 2
        const stroke = cfg.style?.stroke || '#f59e0b'
        const keyShape = group.addShape('path', {
          attrs: {
            path: [
              ['M', x, y + 12],
              ['C', x, y - 4, x + width, y - 4, x + width, y + 12],
              ['L', x + width, y + height - 12],
              ['C', x + width, y + height + 4, x, y + height + 4, x, y + height - 12],
              ['Z'],
              ['M', x, y + 12],
              ['C', x, y + 28, x + width, y + 28, x + width, y + 12]
            ],
            fill: cfg.style?.fill || '#fff7ed',
            stroke,
            lineWidth: cfg.style?.lineWidth || 1.3,
            shadowColor: 'rgba(245, 158, 11, 0.12)',
            shadowBlur: 12,
            shadowOffsetY: 5
          },
          name: 'database-card'
        })
        group.addShape('text', {
          attrs: {
            text: cfg.fileName,
            x: 0,
            y: y + 30,
            textAlign: 'center',
            textBaseline: 'middle',
            fill: '#172033',
            fontSize: 12,
            fontWeight: 800,
            fontFamily: 'Inter, Microsoft YaHei, Noto Sans SC, sans-serif'
          },
          name: 'filename'
        })
        group.addShape('text', {
          attrs: {
            text: cfg.descriptionText,
            x: 0,
            y: y + 50,
            textAlign: 'center',
            textBaseline: 'middle',
            fill: '#92400e',
            fontSize: 11,
            fontFamily: 'Inter, Microsoft YaHei, Noto Sans SC, sans-serif'
          },
          name: 'description'
        })
        return keyShape
      }
    },
    'single-node'
  )
}

function renderGraph() {
  if (!container.value) return
  registerCustomNodes()

  const width = container.value.clientWidth || 1180
  const height = container.value.clientHeight || 720

  if (!graph) {
    graph = new G6.Graph({
      container: container.value,
      width,
      height,
      fitView: true,
      fitViewPadding: [48, 58, 48, 58],
      groupByTypes: false,
      modes: {
        default: props.nodeDragEnabled ? ['drag-canvas', 'zoom-canvas', 'drag-node'] : ['drag-canvas', 'zoom-canvas']
      },
      defaultCombo: {
        type: 'rect',
        padding: [36, 24, 24, 24],
        style: {
          fill: '#ffffff',
          stroke: '#d7dee8',
          lineWidth: 1,
          radius: 0,
          shadowColor: 'rgba(15, 23, 42, 0.05)',
          shadowBlur: 10,
          shadowOffsetY: 5
        },
        labelCfg: {
          refY: 14,
          position: 'top',
          style: {
            fill: '#111827',
            fontSize: 11,
            fontWeight: 800,
            fontFamily: 'Inter, Microsoft YaHei, Noto Sans SC, sans-serif'
          }
        }
      },
      defaultEdge: {
        type: 'polyline',
        style: {
          lineWidth: 1.2,
          stroke: '#3f3f46',
          radius: 8,
          endArrow: {
            path: G6.Arrow.triangle(7, 9, 0),
            fill: '#3f3f46'
          }
        },
        labelCfg: {
          autoRotate: false,
          refY: -10,
          style: {
            fontSize: 10,
            fill: '#111827',
            background: {
              fill: '#f8fbff',
              stroke: '#d7dee8',
              padding: [2, 5, 2, 5],
              radius: 2
            }
          }
        }
      }
    })

    graph.on('node:mouseenter', (event: any) => setFocus(event.item, true))
    graph.on('node:mouseleave', (event: any) => setFocus(event.item, false))
    graph.on('node:click', (event: any) => {
      const model = event.item?.getModel?.()
      if (model) {
        emit('nodeSelected', {
          id: String(model.id),
          label: String(model.rawLabel || model.label || model.id),
          filename: model.filename,
          type: model.nodeKind || model.type,
          language: model.language,
          path: model.path,
          description: model.description,
          groupId: model.groupId,
          module: model.module,
          shape: model.shapeKind,
          size: model.fileSize
        })
      }
    })
  } else {
    graph.changeSize(width, height)
  }

  graph.node((node: any) => ({
    ...node,
    stateStyles: {
      hover: { stroke: '#0ea5e9', lineWidth: 2.2 },
      dim: { opacity: 0.28 }
    }
  }))

  graph.edge((edge: any) => ({
    ...edge,
    stateStyles: {
      focus: { stroke: '#0ea5e9', lineWidth: 2 },
      dim: { opacity: 0.22 }
    }
  }))

  const layout = layoutModules()
  const visibleIds = new Set(layout.nodes.map((node) => node.id))

  const combos = layout.groups.map((group) => ({
    id: group.id,
    label: group.label,
    style: {
      fill: '#ffffff',
      stroke: '#d7dee8',
      lineWidth: 1,
      radius: 0
    },
    labelCfg: {
      style: {
        fill: '#111827',
        fontSize: 11,
        fontWeight: 800
      }
    }
  }))

  const nodes = layout.nodes.map((node) => {
    const selected = Boolean(props.selectedPath && node.path === props.selectedPath)
    const matched = isMatched(node)
    return {
      id: node.id,
      label: node.label,
      rawLabel: node.label,
      filename: node.filename || node.label || fileName(node.path),
      fileName: shortText(node.filename || node.label || fileName(node.path), 18),
      description: node.description || '',
      descriptionText: shortText(node.description || '项目主体源码文件', 20),
      language: node.language,
      nodeKind: node.nodeKind || (node.isFile ? 'file' : node.type),
      path: node.path,
      groupId: node.groupId,
      comboId: node.isFile && node.groupId ? node.groupId : undefined,
      x: (node as GraphNode & { x?: number }).x,
      y: (node as GraphNode & { y?: number }).y,
      module: node.module,
      shapeKind: node.shape,
      fileSize: node.size,
      type: g6NodeType(node),
      size: nodeSize(node),
      accent: node.color || colorForShape(node.shape),
      style: nodeStyle(node, selected, matched),
      labelCfg: { style: { opacity: 0 } }
    }
  })

  const edges = props.graphData.edges.filter((edge) => {
    const relation = edge.relation || edge.type
    return relation !== 'contains' && visibleIds.has(edge.source) && visibleIds.has(edge.target)
  }).map((edge) => ({
    source: edge.source,
    target: edge.target,
    label: edge.label || relationLabel(edge.relation || edge.type),
    type: 'polyline',
    labelCfg: {
      autoRotate: false,
      refY: -10,
      style: {
        fill: '#111827',
        fontSize: 10,
        background: {
          fill: '#f8fbff',
          stroke: '#d7dee8',
          padding: [2, 5, 2, 5],
          radius: 2
        }
      }
    },
    style: edgeStyle(edge)
  }))

  graph.data({ combos, nodes, edges })
  graph.render()
  graph.fitView()
}

function layoutModules() {
  const groups = props.graphData.groups || []
  const fileNodes = props.graphData.nodes.filter((node) => node.isFile)
  const grouped = groups
    .map((group) => ({
      ...group,
      files: fileNodes
        .filter((node) => node.groupId === group.id)
        .sort((a, b) => String(a.path || a.label).localeCompare(String(b.path || b.label)))
    }))
    .filter((group) => group.files.length > 0)

  const orphanFiles = fileNodes.filter((node) => !node.groupId || !groups.some((group) => group.id === node.groupId))
  if (orphanFiles.length) {
    grouped.push({
      id: 'group_unclassified',
      label: '其他文件',
      description: '未归入主要模块的源码文件',
      color: '#94a3b8',
      files: orphanFiles
    })
  }

  const positioned: GraphNode[] = []
  const roles = new Map<string, Array<GraphGroup & { files: GraphNode[] }>>()
  grouped.forEach((group) => {
    const role = groupRole(group)
    roles.set(role, [...(roles.get(role) || []), group])
  })

  let runtimeX = 210
  ;(roles.get('runtime') || []).forEach((group) => {
    const metrics = groupMetrics(group.files.length)
    placeGroupFiles(group, runtimeX + metrics.width / 2, 68, positioned)
    runtimeX += metrics.width + 64
  })

  let frontendY = 238
  ;(roles.get('frontend') || []).forEach((group) => {
    const metrics = groupMetrics(group.files.length)
    placeGroupFiles(group, 660, frontendY, positioned)
    frontendY += metrics.height + 58
  })

  let backendY = Math.max(470, frontendY + 18)
  ;(roles.get('backend') || []).forEach((group) => {
    const metrics = groupMetrics(group.files.length)
    placeGroupFiles(group, 360, backendY, positioned)
    backendY += metrics.height + 56
  })

  ;(roles.get('data') || []).forEach((group) => {
    const metrics = groupMetrics(group.files.length)
    placeGroupFiles(group, 360, backendY, positioned)
    backendY += metrics.height + 52
  })

  let sharedY = Math.max(470, frontendY + 18)
  ;(roles.get('shared') || []).forEach((group) => {
    const metrics = groupMetrics(group.files.length)
    placeGroupFiles(group, 900, sharedY, positioned)
    sharedY += metrics.height + 58
  })

  let otherY = Math.max(backendY, sharedY, 620)
  ;(roles.get('other') || []).forEach((group, index) => {
    const metrics = groupMetrics(group.files.length)
    placeGroupFiles(group, index % 2 === 0 ? 360 : 900, otherY, positioned)
    if (index % 2 === 1) otherY += metrics.height + 58
  })

  return { groups: grouped, nodes: positioned }
}

function groupMetrics(fileCount: number) {
  const columns = Math.min(3, Math.max(1, fileCount))
  const rows = Math.ceil(fileCount / columns)
  const cardWidth = 138
  const cardHeight = 58
  const gapX = 34
  const gapY = 30
  return {
    columns,
    rows,
    cardWidth,
    cardHeight,
    gapX,
    gapY,
    width: columns * cardWidth + Math.max(0, columns - 1) * gapX + 76,
    height: rows * cardHeight + Math.max(0, rows - 1) * gapY + 74
  }
}

function placeGroupFiles(
  group: GraphGroup & { files: GraphNode[] },
  centerX: number,
  topY: number,
  positioned: GraphNode[]
) {
  const metrics = groupMetrics(group.files.length)
  const contentWidth = metrics.columns * metrics.cardWidth + Math.max(0, metrics.columns - 1) * metrics.gapX
  const startX = centerX - contentWidth / 2 + metrics.cardWidth / 2
  const startY = topY + 54

  group.files.forEach((node, index) => {
    const col = index % metrics.columns
    const row = Math.floor(index / metrics.columns)
    positioned.push({
      ...node,
      x: startX + col * (metrics.cardWidth + metrics.gapX),
      y: startY + row * (metrics.cardHeight + metrics.gapY)
    } as GraphNode & { x: number; y: number })
  })
}

function groupRole(group: GraphGroup & { files: GraphNode[] }) {
  const groupText = `${group.id} ${group.label} ${group.description || ''}`.toLowerCase()
  const fileText = group.files
    .map((file) => `${file.path} ${file.shape} ${file.type}`)
    .join(' ')
    .toLowerCase()
  if (/runtime|deploy|delivery|docker|compose|test|spec|docs|root|验证|测试|部署/.test(groupText)) return 'runtime'
  if (/frontend|next|vue|react|page|route|前端|页面|路由/.test(groupText)) return 'frontend'
  if (/backend|server|api|rag|service|python|后端|接口|服务|解析/.test(groupText)) return 'backend'
  if (/shared|client|ui|widget|component|theme|共享|组件|主题/.test(groupText)) return 'shared'
  if (/data|store|model|schema|database|sql|数据库|存储|模型/.test(groupText)) return 'data'
  if (/frontend|next|vue|react|page|route|前端|页面|路由/.test(fileText)) return 'frontend'
  if (/backend|server|api|rag|service|python|后端|接口|服务|解析/.test(fileText)) return 'backend'
  if (/shared|client|ui|widget|component|theme|共享|组件|主题/.test(fileText)) return 'shared'
  if (/data|store|model|schema|database|sql|数据库|存储|模型/.test(fileText)) return 'data'
  if (/docker|compose|config|test|spec|docs|验证|测试|配置|部署/.test(fileText)) return 'runtime'
  return 'other'
}

function setFocus(item: any, active: boolean) {
  if (!graph || !item) return
  if (!active) {
    graph.getNodes().forEach((node: any) => graph.clearItemStates(node, ['dim', 'hover']))
    graph.getEdges().forEach((edge: any) => graph.clearItemStates(edge, ['dim', 'focus']))
    return
  }
  const relatedEdges = item.getEdges?.() || []
  const relatedIds = new Set<string>([String(item.getID())])
  relatedEdges.forEach((edge: any) => {
    relatedIds.add(String(edge.getSource?.().getID?.()))
    relatedIds.add(String(edge.getTarget?.().getID?.()))
  })
  graph.getNodes().forEach((node: any) => graph.setItemState(node, 'dim', !relatedIds.has(String(node.getID()))))
  graph.getEdges().forEach((edge: any) => graph.setItemState(edge, 'dim', !relatedEdges.includes(edge)))
  relatedEdges.forEach((edge: any) => graph.setItemState(edge, 'focus', true))
  graph.setItemState(item, 'hover', true)
}

function g6NodeType(node: GraphNode) {
  if (!node.isFile) return 'rect'
  if (node.shape === 'database') return 'database-card'
  return 'file-card'
}

function nodeStyle(node: GraphNode, selected: boolean, matched: boolean) {
  if (!node.isFile) {
    return {
      radius: 7,
      fill: node.id === 'project' ? '#e0f2fe' : '#f8fafc',
      stroke: node.color || '#94a3b8',
      lineWidth: 1.4
    }
  }
  if (selected) {
    return {
      fill: '#ccfbf1',
      stroke: '#0f766e',
      lineWidth: 2.2
    }
  }
  if (matched) {
    return {
      fill: '#fef9c3',
      stroke: '#ca8a04',
      lineWidth: 2
    }
  }
  return {
    fill: fillForShape(node.shape),
    stroke: node.color || colorForShape(node.shape),
    lineWidth: 1.2
  }
}

function edgeStyle(edge: GraphEdge) {
  const relation = edge.relation || edge.type
  const stroke = colorForRelation(relation)
  return {
    lineWidth: 1.25,
    stroke,
    radius: 10,
    opacity: 0.9,
    lineDash: edge.style === 'dashed' ? [6, 5] : undefined,
    endArrow: {
      path: G6.Arrow.triangle(7, 9, 0),
      fill: stroke
    }
  }
}

function colorForShape(shape = '') {
  const colors: Record<string, string> = {
    database: '#f59e0b',
    api: '#0ea5e9',
    ui: '#ec4899',
    config: '#f97316',
    test: '#ef4444',
    service: '#14b8a6',
    document: '#64748b',
    box: '#94a3b8'
  }
  return colors[shape] || '#0ea5e9'
}

function fillForShape(shape = '') {
  const fills: Record<string, string> = {
    database: '#fff7ed',
    api: '#eff6ff',
    ui: '#fff1f2',
    config: '#fff7ed',
    test: '#fef2f2',
    service: '#f0fdfa',
    document: '#f8fafc',
    box: '#f8fafc'
  }
  return fills[shape] || '#ffffff'
}

function colorForRelation(type = '') {
  const colors: Record<string, string> = {
    routes_to: '#0ea5e9',
    renders: '#ec4899',
    reads_writes: '#16a34a',
    configures: '#f97316',
    tests: '#ef4444',
    imports: '#8b5cf6',
    calls: '#2563eb',
    depends_on: '#64748b',
    related: '#94a3b8',
    module_relates: '#0f766e',
    explains: '#14b8a6',
    serves: '#14b8a6',
    stores: '#16a34a'
  }
  return colors[type] || '#64748b'
}

function relationLabel(type = '') {
  const labels: Record<string, string> = {
    routes_to: '路由到',
    renders: '渲染',
    reads_writes: '读写数据',
    configures: '配置',
    tests: '测试',
    imports: '导入',
    calls: '调用',
    depends_on: '依赖',
    related: '关联',
    module_relates: '模块关联',
    explains: '说明',
    serves: '服务于',
    stores: '存储'
  }
  return labels[type] || type
}

function nodeSize(node: GraphNode) {
  if (!node.isFile) return [168, 48]
  if (node.shape === 'database') return [140, 58]
  return [138, 56]
}

function isMatched(node: GraphNode) {
  const query = props.highlightQuery?.trim().toLowerCase()
  if (!query) return false
  return [node.label, node.filename, node.path, node.language, node.description, node.module].some((value) =>
    String(value || '').toLowerCase().includes(query)
  )
}

function fileName(path = '') {
  return path.split('/').pop() || ''
}

function shortText(value: string, max: number) {
  const clean = value.replace(/\s+/g, ' ').trim()
  return clean.length > max ? `${clean.slice(0, max)}...` : clean
}

function observeResize() {
  if (!container.value) return
  resizeObserver = new ResizeObserver(() => {
    if (!graph || !container.value) return
    graph.changeSize(container.value.clientWidth || 1180, container.value.clientHeight || 720)
    graph.fitView()
  })
  resizeObserver.observe(container.value)
}

onMounted(() => {
  renderGraph()
  observeResize()
})

watch(
  () => props.graphData,
  async () => {
    await nextTick()
    renderGraph()
  },
  { deep: true }
)

watch(
  () => [props.selectedPath, props.highlightQuery],
  async () => {
    await nextTick()
    renderGraph()
  }
)

watch(
  () => props.nodeDragEnabled,
  async () => {
    await nextTick()
    if (graph) {
      graph.destroy()
      graph = null
    }
    renderGraph()
  }
)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  if (graph) {
    graph.destroy()
    graph = null
  }
})
</script>

<style scoped>
.diagram-container {
  width: 100%;
  height: 72vh;
  min-height: 640px;
  background:
    linear-gradient(rgba(124, 58, 237, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(124, 58, 237, 0.07) 1px, transparent 1px),
    #efe6ff;
  background-size: 28px 28px;
}

@media (max-width: 900px) {
  .diagram-container {
    height: 62vh;
    min-height: 500px;
  }
}
</style>
