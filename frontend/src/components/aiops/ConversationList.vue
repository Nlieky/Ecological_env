<template>
  <aside class="sess">
    <button class="newbtn" :disabled="creating" @click="newConversation">
      {{ creating ? '创建中…' : '+ 新对话' }}
    </button>
    <div class="head-row">
      <h4>历史会话 ({{ chat.conversations.length }})</h4>
      <button v-if="chat.conversations.length" class="clear-btn" @click="clearAll" title="清除全部历史">清除</button>
    </div>
    <div v-for="c in chat.conversations" :key="c.id" class="si" :class="{active: chat.current?.id === c.id}" @click="chat.openConversation(c.id)">
      <div class="si-body">
        <div class="t">{{ c.title }}</div>
        <div class="m">{{ c.message_count }} 条</div>
      </div>
      <button class="del" @click.stop="removeOne(c.id)" title="删除">✕</button>
    </div>
    <div v-if="!chat.conversations.length" class="empty">暂无历史</div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { conversationsService } from '@/api/modules/conversations'
const chat = useChatStore()
const creating = ref(false)

/** 新对话：先在后端落一条对话记录（列表立刻可见 + sessionId 绑定它，
 *  首次提问的问答会归到这条对话），再清空消息区。 */
async function newConversation() {
  if (creating.value) return
  creating.value = true
  try { await chat.startNewConversation() }
  finally { creating.value = false }
}

async function removeOne(id: string) {
  if (!confirm('确定删除这条对话？')) return
  try {
    await conversationsService.delete(id)
    await chat.fetchConversations()
    if (chat.current?.id === id) { chat.clearMessages() }
  } catch {}
}

async function clearAll() {
  if (!confirm('确定清除全部对话历史？此操作不可恢复。')) return
  try {
    await conversationsService.clearAll()
    chat.clearMessages()
    await chat.fetchConversations()
  } catch {}
}
</script>

<style scoped>
.sess { width: 220px; background: #fff; border-right: 1px solid var(--brd); padding: 14px 10px; flex-shrink: 0; overflow-y: auto }
.newbtn { width: 100%; padding: 9px; border-radius: 9px; border: 1px dashed var(--brd); background: #fff; color: var(--primary); font-size: 13px; font-weight: 600; cursor: pointer; margin-bottom: 12px }
.head-row { display: flex; justify-content: space-between; align-items: center; margin: 6px 6px 8px }
h4 { font-size: 11px; color: var(--text-muted); letter-spacing: 1px }
.clear-btn { font-size: 11px; color: var(--el-color-danger, #f56c6c); background: none; border: 1px solid var(--brd); border-radius: 5px; padding: 2px 8px; cursor: pointer }
.clear-btn:hover { background: #fef2f2; border-color: var(--el-color-danger, #f56c6c) }
.si { display: flex; align-items: center; gap: 4px; padding: 9px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 3px }
.si:hover { background: #eef2ff }
.si.active { background: #eef2ff; border-left: 3px solid var(--primary); font-weight: 600 }
.si-body { flex: 1; min-width: 0 }
.t { font-size: 12.5px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.m { font-size: 10.5px; color: var(--text-muted); margin-top: 2px }
.del { opacity: 0; font-size: 13px; color: var(--text-muted); background: none; border: 0; cursor: pointer; padding: 0 2px; flex-shrink: 0 }
.si:hover .del { opacity: .6 }
.del:hover { opacity: 1 !important; color: var(--el-color-danger, #f56c6c) }
.empty { color: var(--text-muted); font-size: 12px; padding: 10px }
</style>
