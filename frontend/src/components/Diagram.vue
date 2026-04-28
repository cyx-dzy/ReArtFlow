<template>
  <div ref="container" class="diagram-container"></div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import G6 from '@antv/g6'

// 接收后端返回的 Mermaid 文本或 JSON 图谱
const props = defineProps<{
  graphData: any // 统一的 JSON 结构，或直接的 Mermaid 文本（这里统一为 JSON）
}>()

const container = ref<HTMLElement | null>(null)

onMounted(() => {
  if (!container.value) return

  // 使用 G6 渲染交互式图谱
  const graph = new G6.Graph({
    container: container.value,
    width: container.value.clientWidth,
    height: container.value.clientHeight,
    fitView: true,
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node']
    },
    defaultNode: {
      type: 'rect',
      style: {
        fill: '#fff',
        stroke: '#666',
        lineWidth: 1
      },
      labelCfg: {
        style: {
          fontSize: 12,
          fill: '#000'
        }
      }
    },
    defaultEdge: {
      style: {
        lineWidth: 1,
        stroke: '#aaa'
      }
    }
  })

  // 将统一的 JSON 转换为 G6 所需的 data 结构
  const nodes = props.graphData.nodes.map((n: any) => ({ id: n.id, label: n.label }))
  const edges = props.graphData.edges.map((e: any) => ({ source: e.source, target: e.target }))
  graph.data({ nodes, edges })
  graph.render()
})
</script>

<style scoped>
.diagram-container {
  width: 100%;
  height: 600px; /* 可根据需求自行调整 */
  border: 1px solid #eaeaea;
}
</style>
