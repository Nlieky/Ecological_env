<!-- frontend/src/views/PlantsConfigView.vue -->
<!-- 公共页头提供标题，面板保留配置操作与单一滚动区。 -->
<template>
  <PageShell title="厂区配置" subtitle="多厂层级、别名、报表映射与单厂参数" scroll="contained">
  <div class="pcv">
    <PlantsConfigPanel />
  </div>
  </PageShell>
</template>

<script setup lang="ts">
import PlantsConfigPanel from '@/components/agents/config/PlantsConfigPanel.vue'
import PageShell from '@/components/common/PageShell.vue'
</script>

<style scoped>
.pcv { height: 100%; min-height: 0;
  background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px;
  overflow: hidden; box-shadow: var(--card-shadow);
  display: flex; flex-direction: column }
.pcv :deep(.pc) { max-width: none; flex: 1; min-height: 0; box-sizing: border-box; padding: 18px 22px }
.pcv :deep(.pc-hl) { display: none }
</style>
