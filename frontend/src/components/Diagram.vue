<template>
  <div ref="container" class="diagram-container" aria-label="代码结构图谱"></div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import G6 from '@antv/g6'

type GraphNode = {
  id: string
  label: string
  type?: string
  language?: string
  path?: string
  shape?: string
  color?: string
  description?: string
  groupId?: string
}

type GraphEdge = {
  source: string
  target: string
  label?: string
  type?: string
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
}>()

const emit = defineEmits<{
  (event: 'nodeSelected', node: { id: string; label: string; type?: string; path?: string }): void
}>()

const container = ref<HTMLElement | null>(null)
let graph: any = null
let resizeObserver: ResizeObserver | null = null
let customNodesRegistered = false

function registerCustomNodes() {
  if (customNodesRegistered) return
  customNodesRegistered = true

  G6.registerNode(
    'database-node',
    {
      draw(cfg: any, group: any) {
        const size = cfg.size || [176, 62]
        const width = Array.isArray(size) ? size[0] : size
        const height = Array.isArray(size) ? size[1] : size
        const x = -width / 2
        const y = -height / 2
        const fill = cfg.style?.fill || '#152033'
        const stroke = cfg.style?.stroke || '#5eead4'
        const keyShape = group.addShape('path', {
          attrs: {
            path: [
              ['M', x, y + 10],
              ['C', x, y - 4, x + width, y - 4, x + width, y + 10],
              ['L', x + width, y + height - 10],
              ['C', x + width, y + height + 4, x, y + height + 4, x, y + height - 10],
              ['Z'],
              ['M', x, y + 10],
              ['C', x, y + 24, x + width, y + 24, x + width, y + 10]
            ],
            fill,
            stroke,
            lineWidth: cfg.style?.lineWidth || 1.6
          },
          name: 'database-shape'
        })
        group.addShape('text', {
          attrs: {
            text: cfg.label,
            x: 0,
            y: 4,
            textAlign: 'center',
            textBaseline: 'middle',
            fill: cfg.labelCfg?.style?.fill || '#d9f99d',
            fontSize: 12,
            fontWeight: cfg.labelCfg?.style?.fontWeight || 700,
            fontFamily: 'Inter, Microsoft YaHei, Noto Sans SC, sans-serif'
          },
          name: 'database-label'
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

  const width = container.value.clientWidth || 1000
  const height = container.value.clientHeight || 620

  if (!graph) {
    graph = new G6.Graph({
      container: container.value,
      width,
      height,
      fitView: true,
      fitViewPadding: [36, 46, 36, 46],
      layout: {
        type: 'dagre',
        rankdir: 'LR',
        nodesep: 40,
        ranksep: 104
      },
      modes: {
        default: ['drag-canvas', 'zoom-canvas', 'drag-node']
      },
      defaultNode: {
        type: 'rect',
        size: [184, 54],
        style: {
          radius: 8,
          fill: '#172033',
          stroke: '#38bdf8',
          lineWidth: 1.4,
          shadowColor: 'rgba(56, 189, 248, 0.22)',
          shadowBlur: 10
        },
        labelCfg: {
          style: {
            fontFamily: 'Inter, Microsoft YaHei, Noto Sans SC, sans-serif',
            fontSize: 12,
            fontWeight: 700,
            fill: '#dbeafe'
          }
        }
      },
      defaultEdge: {
        type: 'polyline',
        style: {
          lineWidth: 1.35,
          stroke: '#7dd3fc',
          radius: 8,
          endArrow: {
            path: G6.Arrow.triangle(7, 9, 0),
            fill: '#7dd3fc'
          }
        },
        labelCfg: {
          autoRotate: true,
          refY: -8,
          style: {
            fontSize: 11,
            fill: '#cbd5e1',
            background: {
              fill: '#101827',
              stroke: '#22314a',
              padding: [2, 5, 2, 5],
              radius: 3
            }
          }
        }
      }
    })

    graph.on('node:mouseenter', (event: any) => {
      const item = event.item
      if (item) graph.setItemState(item, 'hover', true)
    })
    graph.on('node:mouseleave', (event: any) => {
      const item = event.item
      if (item) graph.setItemState(item, 'hover', false)
    })
    graph.on('node:click', (event: any) => {
      const model = event.item?.getModel?.()
      if (model) {
        emit('nodeSelected', {
          id: String(model.id),
          label: String(model.rawLabel || model.label || model.id),
          type: model.nodeKind,
          path: model.path
        })
      }
    })
  } else {
    graph.changeSize(width, height)
  }

  graph.node((node: any) => ({
    ...node,
    stateStyles: {
      hover: {
        stroke: '#facc15',
        lineWidth: 2.2,
        shadowBlur: 16
      }
    }
  }))

  const nodes = props.graphData.nodes.map((node) => {
    const selected = Boolean(props.selectedPath && node.path === props.selectedPath)
    const matched = isMatched(node)
    return {
      id: node.id,
      label: trimLabel(node.label),
      rawLabel: node.label,
      nodeKind: node.type,
      path: node.path,
      type: g6NodeType(node.shape),
      size: nodeSize(node.shape),
      style: nodeStyle(node, selected, matched),
      labelCfg: {
        style: {
          fill: selected ? '#042f2e' : '#dbeafe',
          fontWeight: selected || matched ? 800 : 700
        }
      }
    }
  })

  const edges = props.graphData.edges.map((edge) => ({
    source: edge.source,
    target: edge.target,
    label: edge.label || relationLabel(edge.type),
    type: 'polyline',
    style: edgeStyle(edge)
  }))

  graph.data({ nodes, edges })
  graph.render()
  graph.fitView()
}

function g6NodeType(shape = '') {
  if (shape === 'database') return 'database-node'
  if (shape === 'api') return 'diamond'
  if (shape === 'ui') return 'ellipse'
  if (shape === 'service') return 'circle'
  return 'rect'
}

function nodeStyle(node: GraphNode, selected: boolean, matched: boolean) {
  if (selected) {
    return {
      fill: '#5eead4',
      stroke: '#99f6e4',
      lineWidth: 2.4,
      shadowColor: 'rgba(94, 234, 212, 0.45)',
      shadowBlur: 18
    }
  }
  if (matched) {
    return {
      radius: node.shape === 'box' ? 8 : 4,
      fill: '#302513',
      stroke: '#facc15',
      lineWidth: 2,
      shadowColor: 'rgba(250, 204, 21, 0.28)',
      shadowBlur: 14
    }
  }
  return {
    radius: node.shape === 'box' ? 8 : 4,
    fill: fillForShape(node.shape),
    stroke: node.color || colorForShape(node.shape),
    lineWidth: 1.4,
    shadowColor: 'rgba(15, 23, 42, 0.28)',
    shadowBlur: 8
  }
}

function edgeStyle(edge: GraphEdge) {
  const stroke = colorForRelation(edge.type)
  return {
    lineWidth: edge.type === 'contains' ? 1 : 1.35,
    stroke,
    radius: 8,
    lineDash: edge.style === 'dashed' ? [6, 5] : undefined,
    endArrow: {
      path: G6.Arrow.triangle(7, 9, 0),
      fill: stroke
    }
  }
}

function colorForShape(shape = '') {
  const colors: Record<string, string> = {
    database: '#5eead4',
    api: '#fbbf24',
    ui: '#f472b6',
    config: '#fb923c',
    test: '#f87171',
    service: '#38bdf8',
    document: '#a78bfa',
    box: '#94a3b8'
  }
  return colors[shape] || '#38bdf8'
}

function fillForShape(shape = '') {
  const fills: Record<string, string> = {
    database: '#152033',
    api: '#241d13',
    ui: '#25172a',
    config: '#271b12',
    test: '#2b1719',
    service: '#122235',
    document: '#1f1b37',
    box: '#172033'
  }
  return fills[shape] || '#172033'
}

function colorForRelation(type = '') {
  const colors: Record<string, string> = {
    contains: '#64748b',
    routes_to: '#38bdf8',
    renders: '#f472b6',
    reads_writes: '#22c55e',
    configures: '#fb923c',
    tests: '#f87171',
    imports: '#a78bfa',
    calls: '#60a5fa',
    depends_on: '#94a3b8',
    serves: '#2dd4bf',
    stores: '#22c55e'
  }
  return colors[type] || '#7dd3fc'
}

function relationLabel(type = '') {
  const labels: Record<string, string> = {
    contains: '包含',
    routes_to: '路由到',
    renders: '渲染',
    reads_writes: '读写数据',
    configures: '配置',
    tests: '测试',
    imports: '导入',
    calls: '调用',
    depends_on: '依赖',
    serves: '服务于',
    stores: '存储'
  }
  return labels[type] || type
}

function nodeSize(shape = '') {
  if (shape === 'hexagon') return [220, 62]
  if (shape === 'box') return [205, 56]
  if (shape === 'database') return [176, 62]
  if (shape === 'api') return [168, 68]
  if (shape === 'ui') return [180, 56]
  if (shape === 'service') return [86, 86]
  return [184, 54]
}

function trimLabel(label: string) {
  return label.length > 22 ? `${label.slice(0, 21)}...` : label
}

function isMatched(node: GraphNode) {
  const query = props.highlightQuery?.trim().toLowerCase()
  if (!query) return false
  return [node.label, node.path, node.language, node.type].some((value) =>
    String(value || '').toLowerCase().includes(query)
  )
}

function observeResize() {
  if (!container.value) return
  resizeObserver = new ResizeObserver(() => {
    if (!graph || !container.value) return
    graph.changeSize(container.value.clientWidth || 1000, container.value.clientHeight || 620)
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
  height: 620px;
  background:
    linear-gradient(rgba(148, 163, 184, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.06) 1px, transparent 1px),
    #101827;
  background-size: 26px 26px;
}

@media (max-width: 1180px) {
  .diagram-container {
    height: 520px;
  }
}
</style>
