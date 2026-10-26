<template>
  <div class="comp">
    <input v-model="text" :disabled="chat.loading"
      :placeholder="channel === 'action' ? '下指令:例如 检测pH平稳异常 / 只看COD' : '问主智能体:例如 最近出水COD是否超标?'"
      @keyup.enter="send" />
    <button :disabled="chat.loading || !text.trim()" @click="send">{{ chat.loading ? '执行中…' : '发送' }}</button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { mainAssistantDraft, formatHandoffDraft } from '@/assistant/handoff'
import { useChatStore } from '@/stores/chat'
const props = withDefaults(defineProps<{ channel?: 'chat' | 'action' }>(), { channel: 'chat' })
const chat = useChatStore()
const text = ref('')
watch(mainAssistantDraft, draft => {
  if (props.channel === 'chat' && draft) {
    text.value = text.value.trim() ? `${text.value}\n\n${formatHandoffDraft(draft)}` : formatHandoffDraft(draft)
    mainAssistantDraft.value = null
  }
}, { immediate: true })
function send() {
  const q = text.value.trim()
  if (!q || chat.loading) return
  text.value = ''
  // channel=action → AI 助手(右下角)动作通道:后端只走动作短路
  void chat.sendQuery(q, props.channel === 'action' ? 'floating' : 'chat')
}
</script>

<style scoped>
.comp { border-top: 1px solid var(--brd); background: #fff; padding: 12px 18px; display: flex; gap: 10px }
input { flex: 1; border: 1px solid var(--brd); border-radius: 10px; padding: 11px 14px; font-size: 13px; outline: none; font-family: inherit }
input:focus { border-color: var(--primary) }
button { background: var(--primary); color: #fff; border: 0; border-radius: 10px; padding: 11px 20px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit }
button:disabled { opacity: .5; cursor: not-allowed }
</style>
