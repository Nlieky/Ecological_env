<template>
  <div class="chat-wrap">
    <ConversationList @new="chat.clearMessages()" />
    <section class="chat">
      <div class="chdr"><span class="ttl">AI 智能助手</span><span class="mdl">ctgu-vlm · 主智能体</span></div>
      <div class="body">
        <ChatMessage v-for="m in chat.messages" :key="m.id" :msg="m" />
        <div v-if="chat.loading" class="thinking">主智能体思考中…(同步查询约 15-60s)</div>
        <div v-if="!chat.messages.length && !chat.loading" class="empty">向主智能体提问,例如:最近出水COD是否超标?</div>
      </div>
      <ChatComposer />
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import ConversationList from '@/components/aiops/ConversationList.vue'
import ChatMessage from '@/components/aiops/ChatMessage.vue'
import ChatComposer from '@/components/aiops/ChatComposer.vue'

const chat = useChatStore()
onMounted(() => chat.fetchConversations())
</script>

<style scoped>
.chat-wrap { display: flex; height: calc(100vh - var(--header-height) - 40px); margin: -20px; }
.chat { flex: 1; display: flex; flex-direction: column; min-width: 0 }
.chdr { height: 52px; border-bottom: 1px solid var(--brd); display: flex; align-items: center; justify-content: space-between; padding: 0 18px; background: #fff }
.ttl { font-size: 15px; font-weight: 600 }
.mdl { font-size: 11px; color: var(--text-muted); background: #f8fafc; border: 1px solid var(--brd); padding: 3px 9px; border-radius: 6px }
.body { flex: 1; overflow-y: auto; padding: 20px 22px; background: var(--content-bg, #f1f5f9) }
.thinking { color: var(--text-muted); font-size: 13px; padding: 12px 0 }
.empty { color: var(--text-muted); font-size: 13px; padding: 40px 0; text-align: center }
</style>
