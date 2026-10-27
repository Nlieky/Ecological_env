<script setup lang="ts">
import { computed } from 'vue'
type State = 'idle' | 'ready' | 'initial-loading' | 'refreshing' | 'empty' | 'not-found' | 'partial' | 'error' | 'unavailable' | 'disabled' | 'stale'
const props = withDefaults(defineProps<{ state: State; preserveContent?: boolean; title?: string; message?: string }>(), { preserveContent: false })
defineEmits<{ retry: [] }>()
const messages: Partial<Record<State, string>> = { 'initial-loading': '正在加载…', refreshing: '正在刷新…', empty: '暂无数据', 'not-found': '未找到相关内容', partial: '部分数据暂不可用', error: '数据加载失败，请稍后重试。', unavailable: '服务暂不可用', disabled: '此功能已停用', stale: '数据已陈旧，请核验数据时效。' }
const message = computed(() => props.message ?? messages[props.state])
const showContent = computed(() => props.preserveContent || ['idle', 'ready', 'refreshing', 'partial', 'stale'].includes(props.state))
const canRetry = computed(() => ['error', 'unavailable', 'partial', 'stale'].includes(props.state))
</script>
<template><div class="page-state" :aria-busy="state === 'initial-loading' || state === 'refreshing'"><div v-if="message || title || $slots.hint" class="page-state__message" :class="{ 'page-state__message--blocking': !showContent }" :role="canRetry ? 'alert' : 'status'"><slot name="hint"><strong v-if="title">{{ title }}</strong><span>{{ message }}</span></slot><button v-if="canRetry" type="button" @click="$emit('retry')">重试</button></div><slot v-if="showContent" /></div></template>
<style scoped>
.page-state{min-height:0;min-width:0;flex:1;display:flex;flex-direction:column;gap:12px}.page-state__message{display:flex;align-items:center;justify-content:center;gap:12px;padding:12px;color:var(--text-secondary,#64748b);background:#f0f7ff;border-radius:8px;font-size:14px;flex-wrap:wrap}.page-state__message--blocking{flex:1;min-height:160px}.page-state button{border:1px solid #bfdbfe;background:white;color:#1d4ed8;border-radius:6px;padding:5px 12px;cursor:pointer}.page-state button:focus-visible{outline:2px solid var(--primary,#6366f1);outline-offset:2px}
</style>
