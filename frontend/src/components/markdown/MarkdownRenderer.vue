<template>
  <div class="md" v-html="html"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ content: string }>()
marked.setOptions({ gfm: true, breaks: true })
const html = computed(() => marked.parse(props.content || '') as string)
</script>

<style scoped>
.md { font-size: 13.5px; line-height: 1.7; color: var(--text-primary); }
.md :deep(h1),.md :deep(h2),.md :deep(h3){margin:.6em 0 .3em;font-weight:700}
.md :deep(table){border-collapse:collapse;margin:8px 0;font-size:12.5px}
.md :deep(td),.md :deep(th){border:1px solid var(--brd);padding:4px 9px}
.md :deep(th){background:#f8fafc}
.md :deep(code){background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}
.md :deep(pre){background:#0f172a;color:#e2e8f0;padding:10px;border-radius:8px;overflow:auto}
.md :deep(ul),.md :deep(ol){padding-left:20px;margin:6px 0}
.md :deep(strong){font-weight:700}
</style>
