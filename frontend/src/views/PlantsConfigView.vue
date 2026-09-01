<!-- frontend/src/views/PlantsConfigView.vue -->
<!-- 厂区配置独立页（数据域配置：多厂层级/别名/报表映射/单厂参数）。
     外壳只出页头说明，标题与操作按钮由面板自带——避免双标题堆叠。 -->
<template>
  <div class="pcv">
    <PlantsConfigPanel />
  </div>
</template>

<script setup lang="ts">
import PlantsConfigPanel from '@/components/agents/config/PlantsConfigPanel.vue'
</script>

<style scoped>
.pcv { height: calc(100vh - var(--header-height, 60px) - 40px);
  background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px;
  overflow: hidden; box-shadow: var(--card-shadow);
  display: flex; flex-direction: column }
.pcv :deep(.pc) { max-width: none; flex: 1; overflow-y: auto; padding: 18px 22px }
</style>
