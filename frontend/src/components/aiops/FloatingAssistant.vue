<template>
  <!-- /chat 页本身就是助手，fab 冗余且会盖住页面自己的发送按钮，故隐藏 -->
  <button v-if="route.path !== '/chat'" class="fab" @click="app.toggleAssistant" title="AIOps 智能助手">
    <el-icon><ChatDotRound /></el-icon>
  </button>
  <el-drawer v-model="app.assistantOpen" title="AIOps 智能助手" direction="rtl" size="420px">
    <div class="asst">
      <div class="body">
        <ChatMessage v-for="m in chat.messages" :key="m.id" :msg="m" />
        <div v-if="chat.loading" class="thinking">主智能体思考中…</div>
        <div v-if="!chat.messages.length" class="empty">向主智能体提问，例如：最近出水 COD 是否超标？</div>
      </div>
      <ChatComposer />
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ChatDotRound } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useChatStore } from '@/stores/chat'
import ChatMessage from './ChatMessage.vue'
import ChatComposer from './ChatComposer.vue'
const route = useRoute()
const app = useAppStore()
const chat = useChatStore()
</script>

<style scoped>
.fab { position: fixed; right: 26px; bottom: 26px; z-index: 100; width: 54px; height: 54px; border-radius: 50%;
  border: 0; cursor: pointer; color: #fff; font-size: 22px; background: var(--brand-gradient);
  box-shadow: 0 8px 24px rgba(99,102,241,.4); display: grid; place-items: center; transition: transform .15s }
.fab:hover { transform: scale(1.07) }
.asst { display: flex; flex-direction: column; height: calc(100vh - 120px) }
.body { flex: 1; overflow-y: auto; padding: 4px 6px }
.thinking { color: var(--text-muted); font-size: 13px; padding: 10px 0 }
.empty { color: var(--text-muted); font-size: 13px; padding: 30px 0; text-align: center }
</style>
