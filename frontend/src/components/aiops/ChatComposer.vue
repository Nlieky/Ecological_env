<template>
  <div class="comp">
    <input v-model="text" :disabled="chat.loading" placeholder="问主智能体:例如 最近出水COD是否超标?" @keyup.enter="send" />
    <button :disabled="chat.loading || !text.trim()" @click="send">{{ chat.loading ? '思考中…' : '发送' }}</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
const chat = useChatStore()
const text = ref('')
function send() {
  const q = text.value.trim()
  if (!q || chat.loading) return
  text.value = ''
  void chat.sendQuery(q)
}
</script>

<style scoped>
.comp { border-top: 1px solid var(--brd); background: #fff; padding: 12px 18px; display: flex; gap: 10px }
input { flex: 1; border: 1px solid var(--brd); border-radius: 10px; padding: 11px 14px; font-size: 13px; outline: none; font-family: inherit }
input:focus { border-color: var(--primary) }
button { background: var(--primary); color: #fff; border: 0; border-radius: 10px; padding: 11px 20px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit }
button:disabled { opacity: .5; cursor: not-allowed }
</style>
