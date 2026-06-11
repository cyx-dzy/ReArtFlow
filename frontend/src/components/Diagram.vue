<template>
  <div ref="container" class="diagram-container"></div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import G6 from '@antv/g6'

type GraphData = {
  nodes: Array<{ id: string; label: string; type?: string; path?: string }>
  edges: Array<{ source: string; target: string; label?: string }>
}

const props = defineProps<{
  graphData: GraphData
  highlightQuery?: string
  selectedPath?: string
}>()

const emit = defineEmits<{
  (event: 'nodeSelected', node: { id: string; label: string; type?: string; path?: string }): void
}>()

const container = ref<HTMLElement | null>(null)
let graph: any = null

function renderGraph() {
  if (!container.value) return
  if (!graph) {
    graph = new G6.Graph({
      container: container.value,
      width: container.value.clientWidth || 900,
      height: container.value.clientHeight || 620,
      fitView: true,
      layout: {
        type: 'dagre',
        rankdir: 'LR',
        nodesep: 24,
        ranksep: 70
      },
      modes: {
        default: ['drag-canvas', 'zoom-canvas', 'drag-node']
      },
      defaultNode: {
        type: 'rect',
        size: [180, 38],
        style: {
          radius: 4,
          fill: '#ffffff',
          stroke: '#44546f',
          lineWidth: 1
        },
        labelCfg: {
          style: {
            fontFamily: 'Microsoft YaHei, Noto Sans SC, sans-serif',
            fontSize: 12,
            fill: '#172b4d'
          }
        }
      },
      defaultEdge: {
        type: 'polyline',
        style: {
          lineWidth: 1,
          stroke: '#8c9bab',
          endArrow: true
        },
        labelCfg: {
          autoRotate: true,
          style: {
            fontSize: 11,
            fill: '#5e6c84',
            background: {
              fill: '#fff',
              padding: [2, 4, 2, 4],
              radius: 2
            }
          }
        }
      }
    })
    graph.on('node:click', (event: any) => {
      const model = event.item?.getModel?.()
      if (model) {
        emit('nodeSelected', {
          id: String(model.id),
          label: String(model.label || model.id),
          type: model.type,
          path: model.path
        })
      }
    })
  }

  const query = (props.highlightQuery || '').trim().toLowerCase()
  const nodes = props.graphData.nodes.map((n) => {
    const haystack = `${n.label} ${n.path || ''} ${n.type || ''}`.toLowerCase()
    const matched = query && haystack.includes(query)
    const selected = props.selectedPath && n.path === props.selectedPath
    return {
      id: n.id,
      label: n.label,
      type: n.type,
      path: n.path,
      style: {
        fill: selected ? '#dbeafe' : matched ? '#fef3c7' : '#ffffff',
        stroke: selected ? '#1d4ed8' : matched ? '#b45309' : '#44546f',
        lineWidth: selected || matched ? 2 : 1
      }
    }
  })
  const edges = props.graphData.edges.map((e) => ({ source: e.source, target: e.target, label: e.label }))
  graph.data({ nodes, edges })
  graph.render()
  graph.fitView()
}

onMounted(() => {
  renderGraph()
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
  () => [props.highlightQuery, props.selectedPath],
  async () => {
    await nextTick()
    renderGraph()
  }
)

onBeforeUnmount(() => {
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
  border: 1px solid #dfe3e8;
  background: #f8fafc;
}
</style>
