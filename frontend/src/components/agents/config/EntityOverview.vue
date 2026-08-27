<template>
  <div class="ov" v-if="entity">
    <div class="ov-head">
      <span class="ov-icon">{{ entity.icon }}</span>
      <div>
        <div class="ov-name">{{ entity.label }}</div>
        <div class="ov-dir">{{ entity.dir }}</div>
      </div>
    </div>
    <div class="ov-sec">
      <div class="sec-t">身份文件（{{ entity.identity_files.length }}）</div>
      <div class="chips">
        <span v-for="f in entity.identity_files" :key="f" class="chip"
              @click="$emit('openFile', f)">{{ f }}</span>
      </div>
    </div>
    <div class="ov-sec" v-if="entity.skills.length">
      <div class="sec-t">技能（{{ entity.skills.length }}）</div>
      <div class="chips">
        <span v-for="s in entity.skills" :key="s.name" class="chip skill">📘 {{ s.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AgentEntity } from '@/api/modules/agentConfig'
defineProps<{ entity: AgentEntity }>()
defineEmits<{ (e: 'openFile', f: string): void }>()
</script>

<style scoped>
.ov { max-width: 720px }
.ov-head { display: flex; align-items: center; gap: 13px; margin-bottom: 18px }
.ov-icon { width: 46px; height: 46px; border-radius: 12px; background: var(--brand-gradient);
  display: grid; place-items: center; font-size: 22px }
.ov-name { font-size: 17px; font-weight: 700; color: var(--text-primary) }
.ov-dir { font-size: 11.5px; color: var(--text-muted); font-family: ui-monospace, monospace; margin-top: 2px }
.ov-sec { margin-bottom: 16px }
.sec-t { font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 8px }
.chips { display: flex; flex-wrap: wrap; gap: 7px }
.chip { font-size: 12px; font-family: ui-monospace, monospace; background: #f8fafc;
  border: 1px solid var(--brd); padding: 4px 11px; border-radius: 7px; color: var(--text-secondary); cursor: pointer }
.chip:hover { border-color: var(--primary); color: var(--primary) }
.chip.skill { background: #fffbeb; border-color: #fde68a; cursor: default }
</style>
