<template>
  <div v-if="available" class="eco-aiops-widget">
    <!-- 背景遮罩 -->
    <transition name="eco-backdrop">
      <div v-if="visible" class="eco-backdrop" @click="closePanel" />
    </transition>

    <!-- 聊天面板 -->
    <transition name="eco-panel">
      <div v-if="visible" class="eco-panel">
        <!-- 面板头部 -->
        <div class="eco-panel-header">
          <div class="eco-header-left">
            <img src="@/assets/brand-mark.svg" alt="AI" class="eco-header-avatar" />
            <div class="eco-header-title">
              <span class="eco-title">废水监测智能助手</span>
              <span class="eco-subtitle">我可以帮你分析水质数据、检测异常、解释法规等</span>
            </div>
          </div>
          <button class="eco-close-btn" @click="closePanel">
            <el-icon><Close /></el-icon>
          </button>
        </div>

        <!-- 消息列表 -->
        <div class="eco-message-list" ref="messageListRef">
          <div v-if="messages.length === 0" class="eco-empty-state">
            <el-icon class="eco-empty-icon"><Service /></el-icon>
            <div class="eco-empty-title">欢迎使用废水监测智能助手</div>
            <div class="eco-empty-desc">您可以问我关于水质分析、异常检测、法规解读等问题</div>
            <div class="eco-quick-questions">
              <button
                v-for="q in suggestedQuestions"
                :key="q"
                class="eco-quick-chip"
                @click="sendQuestion(q)"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <div
            v-for="msg in messages"
            :key="msg.id"
            class="eco-message"
            :class="msg.role"
          >
            <div class="eco-message-avatar">
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
              <el-icon v-else><Service /></el-icon>
            </div>
            <div class="eco-message-content">
              <div class="eco-message-meta">
                <span class="eco-message-role">{{ msg.role === 'user' ? '您' : '智能助手' }}</span>
                <span class="eco-message-time">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="eco-message-text" v-html="renderMarkdown(msg.content)"></div>
            </div>
          </div>

          <!-- 正在输入指示器 -->
          <div v-if="isLoading" class="eco-message assistant">
            <div class="eco-message-avatar">
              <el-icon><Service /></el-icon>
            </div>
            <div class="eco-message-content">
              <div class="eco-typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="eco-composer">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="输入您的问题，按 Enter 发送，Shift + Enter 换行"
            @keydown="handleKeydown"
            :disabled="isLoading"
          />
          <div class="eco-composer-actions">
            <span class="eco-composer-hint">Enter 发送，Shift + Enter 换行</span>
            <el-button
              type="primary"
              size="small"
              @click="sendMessage"
              :loading="isLoading"
              :disabled="!inputMessage.trim()"
            >
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 悬浮按钮 -->
    <button class="eco-fab" @click="toggleVisible">
      <span class="eco-fab-core">
        <img src="@/assets/brand-mark.svg" alt="AI" class="eco-fab-avatar" />
      </span>
      <span class="eco-fab-label">
        <strong>AI 助手</strong>
      </span>
      <span class="eco-fab-dot"></span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { queryApi } from '@/api/query'
import { User, Service, Promotion, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const available = ref(true)
const visible = ref(false)
const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const messageListRef = ref<HTMLElement>()

const suggestedQuestions = ref<string[]>([
  '分析最近一周的数据异常情况',
  '查看所有站点的 pH 趋势',
  '今天检测到哪些违规行为？',
  '解释废水排放标准'
])

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit'
  })
}

function renderMarkdown(text: string) {
  return text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

function sendQuestion(question: string) {
  inputMessage.value = question
  sendMessage()
}

async function sendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage: ChatMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date().toISOString()
  }

  messages.value.push(userMessage)
  const query = inputMessage.value
  inputMessage.value = ''
  scrollToBottom()

  isLoading.value = true

  try {
    const response = await queryApi.query({
      query,
      context: {
        page: 'aiops-chat'
      }
    })

    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      // 后端返回的是 content 字段，兼容 answer/result 字段
      content: response.content || response.answer || response.result || '分析完成',
      timestamp: new Date().toISOString()
    }

    messages.value.push(assistantMessage)
  } catch (error) {
    console.error('Query failed:', error)
    ElMessage.error('获取回复失败，请稍后重试')

    const errorMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '抱歉，我遇到了一些问题，请稍后重试。',
      timestamp: new Date().toISOString()
    }
    messages.value.push(errorMessage)
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function toggleVisible() {
  visible.value = !visible.value
  if (visible.value) {
    nextTick(() => {
      scrollToBottom()
    })
  }
}

function closePanel() {
  visible.value = false
}

function handleOpenRequest() {
  visible.value = true
  nextTick(() => {
    scrollToBottom()
  })
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && visible.value) {
    closePanel()
  }
}

onMounted(() => {
  window.addEventListener('ecological-aiops-open', handleOpenRequest)
  window.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('ecological-aiops-open', handleOpenRequest)
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<style scoped>
.eco-aiops-widget {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1000;
}

/* 背景遮罩 */
.eco-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(4px);
  z-index: 999;
}

.eco-backdrop-enter-active,
.eco-backdrop-leave-active {
  transition: opacity 0.2s ease;
}

.eco-backdrop-enter-from,
.eco-backdrop-leave-to {
  opacity: 0;
}

/* 聊天面板 */
.eco-panel {
  position: absolute;
  right: 0;
  bottom: 70px;
  width: 420px;
  max-width: calc(100vw - 48px);
  height: 600px;
  max-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #dbe4f0;
  border-radius: 20px;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.18);
  overflow: hidden;
  z-index: 1001;
}

.eco-panel-enter-active,
.eco-panel-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.eco-panel-enter-from,
.eco-panel-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

/* 面板头部 */
.eco-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #fff7ed 0%, #f0f9ff 100%);
}

.eco-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.eco-header-avatar {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

.eco-header-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.eco-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.eco-subtitle {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eco-close-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.eco-close-btn:hover {
  background: rgba(148, 163, 184, 0.12);
  color: #334155;
}

/* 消息列表 */
.eco-message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.eco-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px;
}

.eco-empty-icon {
  font-size: 48px;
  color: #94a3b8;
  margin-bottom: 16px;
}

.eco-empty-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.eco-empty-desc {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 24px;
  line-height: 1.6;
}

.eco-quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.eco-quick-chip {
  padding: 6px 12px;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #fff;
  color: #1d4ed8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.eco-quick-chip:hover {
  background: #eff6ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

/* 消息项 */
.eco-message {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.eco-message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.eco-message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #f1f5f9;
  color: #64748b;
}

.eco-message.assistant .eco-message-avatar {
  background: linear-gradient(135deg, #67b7ab 0%, #5586b6 58%, #49639a 100%);
  color: #ffffff;
}

.eco-message.user .eco-message-avatar {
  background: #3b82f6;
  color: #ffffff;
}

.eco-message-content {
  flex: 1;
  min-width: 0;
}

.eco-message-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.eco-message.user .eco-message-meta {
  justify-content: flex-end;
}

.eco-message-role {
  font-weight: 600;
}

.eco-message-text {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #334155;
}

.eco-message.user .eco-message-text {
  background: linear-gradient(135deg, #dbeafe 0%, #f0f9ff 100%);
  border-color: #bfdbfe;
  color: #1e293b;
}

.eco-message-text :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #1d4ed8;
}

/* 输入指示器 */
.eco-typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.eco-typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typing 1.4s infinite;
}

.eco-typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.eco-typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-8px);
  }
}

/* 输入区域 */
.eco-composer {
  padding: 12px 16px;
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
}

.eco-composer :deep(.el-textarea__inner) {
  border-radius: 12px;
  font-size: 13px;
}

.eco-composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.eco-composer-hint {
  font-size: 11px;
  color: #94a3b8;
}

/* 悬浮按钮 */
.eco-fab {
  position: relative;
  z-index: 1002;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 120px;
  height: 52px;
  padding: 6px 14px 6px 6px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.12);
  cursor: pointer;
  border: 1px solid #bdd5fb;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.eco-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(59, 130, 246, 0.16);
}

.eco-fab:active {
  transform: translateY(0);
}

.eco-fab-core {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 20px;
  background: linear-gradient(145deg, #eef5ff 0%, #f6fbff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.96), 0 8px 16px rgba(59, 130, 246, 0.08);
}

.eco-fab-avatar {
  width: 28px;
  height: 28px;
  display: block;
}

.eco-fab-label {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.1;
}

.eco-fab-label strong {
  font-size: 13px;
  color: #0f172a;
}

.eco-fab-dot {
  position: absolute;
  top: 8px;
  right: 12px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.96), 0 0 0 5px rgba(34, 197, 94, 0.1);
}

/* 响应式 */
@media (max-width: 480px) {
  .eco-aiops-widget {
    right: 12px;
    bottom: 12px;
  }

  .eco-panel {
    width: calc(100vw - 24px);
    max-width: none;
    height: calc(100vh - 80px);
    max-height: none;
    bottom: 64px;
  }

  .eco-fab {
    min-width: 56px;
    width: 56px;
    height: 56px;
    padding: 0;
    justify-content: center;
  }

  .eco-fab-label {
    display: none;
  }

  .eco-fab-core {
    width: 100%;
    height: 100%;
    border-radius: 50%;
  }

  .eco-fab-avatar {
    width: 32px;
    height: 32px;
  }

  .eco-fab-dot {
    top: 6px;
    right: 6px;
  }
}
</style>
