<template>
  <!-- 固定胶囊按钮：图标+文字横排。点击开关助手面板。/chat 页隐藏 -->
  <button v-if="route.path !== '/chat'" class="fab" @click="app.toggleAssistant" title="AIOps 智能助手">
    <svg class="robot" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <!-- 浅色背板圈 -->
      <circle cx="12" cy="12" r="11" fill="rgba(37, 99, 235, 0.1)" stroke="none" />
      <!-- 天线 -->
      <line x1="12" y1="2.4" x2="12" y2="4.6" />
      <circle cx="12" cy="2" r="0.95" fill="currentColor" stroke="none" />
      <!-- 头部 -->
      <rect x="4.5" y="4.6" width="15" height="11.5" rx="4" />
      <!-- 眼睛 -->
      <circle cx="9.2" cy="9.8" r="1.1" fill="currentColor" stroke="none" />
      <circle cx="14.8" cy="9.8" r="1.1" fill="currentColor" stroke="none" />
      <!-- 笑脸嘴 -->
      <path d="M9.8 12.7 Q12 14.2 14.2 12.7" />
      <!-- 两侧耳朵 -->
      <path d="M4.5 8.4 H3 M4.5 12 H3 M19.5 8.4 H21 M19.5 12 H21" />
    </svg>
    <span class="fab-txt">
      <span class="t1">AIOps</span>
      <span class="t2">智能助手</span>
    </span>
  </button>

  <!-- 玻璃浮窗：非模态（无遮罩），不挡大屏，大屏可同时查看/点击 -->
  <Transition name="pop">
    <div v-if="app.assistantOpen" class="panel">
      <div class="panel-head">
        <span class="pt">🤖 AIOps 智能助手</span>
        <button class="close" @click="app.assistantOpen = false" title="收起">✕</button>
      </div>
      <div class="body">
        <ChatMessage v-for="m in chat.messages" :key="m.id" :msg="m" />
        <div v-if="chat.loading" class="thinking">主智能体思考中…</div>
        <div v-if="!chat.messages.length" class="empty">向主智能体提问，例如：<br />最近出水 COD 是否超标？</div>
      </div>
      <ChatComposer />
    </div>
  </Transition>
</template>

<script setup lang="ts">
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
/* 胶囊气泡：白底玻璃质感（多层白渐变 + backdrop 模糊 + 内外阴影 3D 球面），黑色文字/图标 */
.fab { position: fixed; right: 26px; bottom: 26px; z-index: 200;
  display: inline-flex; align-items: center; gap: 10px;
  height: 54px; padding: 0 20px 0 14px; border-radius: 32px;
  border: 1px solid rgba(96, 165, 250, 0.7);
  cursor: pointer; color: #1e293b; font-family: inherit;
  background:
    linear-gradient(180deg, rgba(219, 234, 254, 0.55) 0%, rgba(255,255,255,0.78) 46%, rgba(226,232,240,0.6) 100%);
  backdrop-filter: blur(14px) saturate(160%);
  -webkit-backdrop-filter: blur(14px) saturate(160%);
  box-shadow:
    inset 0 1px 1px rgba(255, 255, 255, 0.95),
    inset 0 -10px 18px rgba(148, 163, 184, 0.25),
    0 12px 30px rgba(85, 134, 182, 0.28),
    0 4px 10px rgba(73, 99, 154, 0.15);
  transition: transform .18s ease, box-shadow .18s ease }
.fab:hover { transform: translateY(-3px) scale(1.02);
  box-shadow:
    inset 0 1px 1px rgba(255, 255, 255, 1),
    inset 0 -10px 18px rgba(148, 163, 184, 0.3),
    0 16px 38px rgba(85, 134, 182, 0.38),
    0 5px 12px rgba(73, 99, 154, 0.2) }
.fab:active { transform: translateY(0) scale(0.99) }
.robot { width: 26px; height: 26px; flex-shrink: 0; color: #2563eb }
.fab-txt { display: flex; flex-direction: column; line-height: 1.15; text-align: left }
.t1 { font-size: 13px; font-weight: 800; letter-spacing: .6px; color: #0f172a }
.t2 { font-size: 10px; font-weight: 500; margin-top: 1px; color: #334155 }

/* 玻璃浮窗：非模态，无遮罩，不挡大屏 */
.panel { position: fixed; right: 26px; bottom: 92px; width: 400px; max-width: calc(100vw - 52px);
  height: 560px; max-height: calc(100vh - 130px); z-index: 199;
  display: flex; flex-direction: column; overflow: hidden; border-radius: 16px;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(18px) saturate(160%);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 12px 40px rgba(31, 38, 135, 0.22), 0 2px 8px rgba(99, 102, 241, 0.12);
}
.panel-head { display: flex; align-items: center; justify-content: space-between;
  padding: 11px 14px; border-bottom: 1px solid rgba(99, 102, 241, 0.14) }
.pt { font-size: 13px; font-weight: 700; color: var(--primary) }
.close { border: 0; background: transparent; cursor: pointer; font-size: 14px;
  color: var(--text-muted); width: 26px; height: 26px; border-radius: 7px; line-height: 1 }
.close:hover { background: rgba(99, 102, 241, 0.1); color: var(--primary) }
.body { flex: 1; overflow-y: auto; padding: 10px 14px }
.thinking { color: var(--text-muted); font-size: 13px; padding: 10px 0 }
.empty { color: var(--text-muted); font-size: 13px; padding: 26px 0; text-align: center; line-height: 1.7 }

/* 弹出/收起动画 */
.pop-enter-active, .pop-leave-active { transition: transform .22s cubic-bezier(.34, 1.56, .64, 1), opacity .22s }
.pop-enter-from, .pop-leave-to { transform: translateY(18px) scale(.95); opacity: 0 }
</style>
