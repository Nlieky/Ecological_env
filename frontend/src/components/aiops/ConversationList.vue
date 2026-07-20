<template>
  <aside class="sess">
    <button class="newbtn" @click="$emit('new')">+ 新对话</button>
    <h4>历史会话</h4>
    <div v-for="c in chat.conversations" :key="c.id" class="si" @click="chat.openConversation(c.id)">
      <div class="t">{{ c.title }}</div>
      <div class="m">{{ c.message_count }} 条</div>
    </div>
    <div v-if="!chat.conversations.length" class="empty">暂无历史</div>
  </aside>
</template>

<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
const chat = useChatStore()
defineEmits<{ (e: 'new'): void }>()
</script>

<style scoped>
.sess { width: 220px; background: #fff; border-right: 1px solid var(--brd); padding: 14px 10px; flex-shrink: 0; overflow-y: auto }
.newbtn { width: 100%; padding: 9px; border-radius: 9px; border: 1px dashed var(--brd); background: #fff; color: var(--primary); font-size: 13px; font-weight: 600; cursor: pointer; margin-bottom: 12px }
h4 { font-size: 11px; color: var(--text-muted); letter-spacing: 1px; margin: 6px 6px 8px }
.si { padding: 9px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 3px }
.si:hover { background: #eef2ff }
.t { font-size: 12.5px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.m { font-size: 10.5px; color: var(--text-muted); margin-top: 2px }
.empty { color: var(--text-muted); font-size: 12px; padding: 10px }
</style>
