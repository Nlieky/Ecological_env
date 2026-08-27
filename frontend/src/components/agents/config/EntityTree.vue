<template>
  <div class="etree">
    <div class="et-h">智能体</div>
    <div v-for="e in entities" :key="e.name" class="et-item"
         :class="{ active: e.name === modelValue, master: e.name === 'master' }"
         @click="$emit('update:modelValue', e.name)">
      <span class="et-icon">{{ e.icon }}</span>
      <span class="et-label">{{ e.label }}</span>
      <span class="et-nfiles">{{ e.identity_files.length }}身份</span>
    </div>
    <div class="et-sep"></div>
    <div class="et-item" :class="{ active: modelValue === '__plants__' }" @click="$emit('update:modelValue', '__plants__')">
      <span class="et-icon">⚙️</span><span class="et-label">厂区配置</span>
    </div>
    <div class="et-item" :class="{ active: modelValue === '__service__' }" @click="$emit('update:modelValue', '__service__')">
      <span class="et-icon">🔄</span><span class="et-label">服务管理</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AgentEntity } from '@/api/modules/agentConfig'
defineProps<{ entities: AgentEntity[]; modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<style scoped>
.etree { width: 210px; flex-shrink: 0; border-right: 1px solid var(--brd); padding: 14px 10px; overflow-y: auto }
.et-h { font-size: 11px; color: var(--text-muted); letter-spacing: 1px; margin: 0 0 8px 8px }
.et-item { display: flex; align-items: center; gap: 9px; padding: 9px 10px; border-radius: 9px;
  cursor: pointer; font-size: 13px; color: var(--text-primary); margin-bottom: 3px; transition: background .12s }
.et-item:hover { background: #f1f5f9 }
.et-item.active { background: var(--primary-soft, #eef2ff); color: var(--primary); font-weight: 600 }
.et-icon { font-size: 16px }
.et-nfiles { margin-left: auto; font-size: 10.5px; color: var(--text-muted) }
.et-sep { height: 1px; background: var(--brd); margin: 10px 4px }
</style>
