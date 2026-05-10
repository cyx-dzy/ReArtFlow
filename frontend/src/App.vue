<template>
  <main style="padding: 16px;">
    <h2>Diagram 交互测试页</h2>
    <p>请验证：节点是否显示、拖拽/缩放是否可用。</p>
    <Diagram :graphData="graphData" />
  </main>
</template>

<script setup lang="ts">
import Diagram from './components/Diagram.vue'

const graphData = {
  nodes: [
    { id: 'root', label: '项目根节点' },
    { id: 'module1', label: '模块一' },
    { id: 'module2', label: '模块二' }
  ],
  edges: [
    { source: 'root', target: 'module1' },
    { source: 'module1', target: 'module2' }
  ]
}
</script>
