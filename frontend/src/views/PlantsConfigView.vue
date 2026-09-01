<!-- frontend/src/views/PlantsConfigView.vue -->
<!-- 厂区配置独立页（从智能体配置页拆出——它是数据域配置:多厂层级/别名/报表映射，
     不属于智能体域）。复用 PlantsConfigPanel 全部能力。 -->
<template>
  <div class="pcv">
    <div class="pcv-head">
      <div class="pcv-title">厂区配置</div>
      <div class="pcv-sub">多厂层级（市→厂区→厂）/ 别名 / 报表映射 / 单厂参数 · 保存即 git 快照</div>
    </div>
    <PlantsConfigPanel />
  </div>
</template>

<script setup lang="ts">
import PlantsConfigPanel from '@/components/agents/config/PlantsConfigPanel.vue'
</script>

<style scoped>
.pcv { display: flex; flex-direction: column; height: calc(100vh - var(--header-height, 60px) - 40px);
  background: var(--card-bg); border: 1px solid var(--brd); border-radius: 13px;
  overflow: hidden; box-shadow: var(--card-shadow) }
.pcv-head { padding: 16px 20px 12px; border-bottom: 1px solid var(--brd); background: #f8fafc; flex-shrink: 0 }
.pcv-title { font-size: 16px; font-weight: 700; color: var(--text-primary) }
.pcv-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px }
/* 面板在独立页里可滚动 */
.pcv :deep(.pc) { max-width: none; }
</style>
