<template>
  <PageShell title="AI 智能助手" subtitle="会话与执行状态" scroll="contained">
  <div class="chat-wrap">
    <ConversationList />
    <section class="chat">
      <div class="chdr"><span class="ttl">当前会话</span><span class="mdl">主智能体</span></div>
      <div class="body" ref="bodyRef">
        <ChatMessage v-for="m in chat.messages" :key="m.id" :msg="m" />
        <div v-if="!chat.messages.length" class="empty">向主智能体提问,例如:最近出水COD是否超标?</div>
      </div>
      <ChatComposer />
    </section>
  </div>
  </PageShell>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import PageShell from '@/components/common/PageShell.vue'
import { useChatStore } from '@/stores/chat'
import ConversationList from '@/components/aiops/ConversationList.vue'
import ChatMessage from '@/components/aiops/ChatMessage.vue'
import ChatComposer from '@/components/aiops/ChatComposer.vue'
import { useAssistantContext } from '@/composables/useAssistantContext'

const chat = useChatStore()
const bodyRef = ref<HTMLElement>()
useAssistantContext(() => ({ pageId: 'chat', source: '主AI助手页面（专业会话内容未共享）', status: chat.loading ? 'loading' : 'ready', actions: ['navigate'] }))

/** 自动滚到底部：新消息/流式输出时，让智能体回复始终贴底展示。
 *  只在用户本来就贴底(或接近底)时跟随——用户主动上翻阅读时不打扰。 */
function autoScroll() {
  const el = bodyRef.value
  if (!el) return
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  if (nearBottom || chat.messages[chat.messages.length - 1]?.role === 'user') {
    el.scrollTop = el.scrollHeight
  }
}

// 消息数量变化(新消息) 或 流式内容更新(delta 追加) → 贴底
watch(() => chat.messages.length, () => nextTick(autoScroll))
watch(() => {
  const last = chat.messages[chat.messages.length - 1]
  return last?.content?.length ?? 0
}, () => nextTick(autoScroll))

</script>

<style scoped>
/* 跟随公共内容区高度；会话列表与消息区各自滚动。 */
.chat-wrap { display: flex; height: 100%; min-height: 0; overflow: hidden }
.chat { flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0 }
.chdr, .chat :deep(.comp) { flex-shrink: 0 }
.chdr { height: 52px; border-bottom: 1px solid var(--brd); display: flex; align-items: center; justify-content: space-between; padding: 0 18px; background: #fff }
.ttl { font-size: 15px; font-weight: 600 }
.mdl { font-size: 11px; color: var(--text-muted); background: #f8fafc; border: 1px solid var(--brd); padding: 3px 9px; border-radius: 6px }
.body { flex: 1; min-height: 0; overflow-y: auto; padding: 20px 22px; background: var(--content-bg, #f1f5f9) }
.thinking { color: var(--text-muted); font-size: 13px; padding: 12px 0 }
.empty { color: var(--text-muted); font-size: 13px; padding: 40px 0; text-align: center }
</style>
