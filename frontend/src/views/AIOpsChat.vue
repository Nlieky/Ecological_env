<template>
  <div class="chat-container">
    <div class="chat-header">
      <h2>AI Assistant</h2>
      <el-tag type="success">Online</el-tag>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message"
        :class="msg.role"
      >
        <div class="message-avatar">
          <el-icon v-if="msg.role === 'user'"><User /></el-icon>
          <el-icon v-else><Service /></el-icon>
        </div>
        <div class="message-content">
          <div class="message-header">
            <span class="message-role">{{ msg.role === 'user' ? 'You' : 'AI Assistant' }}</span>
            <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          <div v-if="msg.chartData" class="message-chart">
            <div :data-chart-id="msg.id" class="echarts-container" style="width:100%;height:300px;"></div>
          </div>
          <div v-if="msg.evidence && msg.evidence.length > 0" class="message-evidence">
            <el-collapse>
              <el-collapse-item title="View Evidence Chain" name="evidence">
                <div class="evidence-list">
                  <div v-for="(item, idx) in msg.evidence" :key="idx" class="evidence-item">
                    <el-tag size="small">{{ item.type }}</el-tag>
                    <span>{{ item.description }}</span>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>

      <div v-if="isTyping" class="message assistant">
        <div class="message-avatar">
          <el-icon><Service /></el-icon>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="suggested-questions" v-if="suggestedQuestions.length > 0 && messages.length <= 1">
      <span class="suggested-label">Try asking:</span>
      <el-tag
        v-for="q in suggestedQuestions"
        :key="q"
        @click="sendSuggested(q)"
        class="suggested-tag"
        type="info"
      >
        {{ q }}
      </el-tag>
    </div>

    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="2"
        placeholder="Ask about water quality, anomalies, regulations..."
        @keydown.enter.ctrl="sendMessage"
        :disabled="isTyping"
      />
      <el-button
        type="primary"
        @click="sendMessage"
        :loading="isTyping"
        :disabled="!inputMessage.trim()"
      >
        <el-icon><Promotion /></el-icon>
        Send (Ctrl+Enter)
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { queryApi } from '@/api/query'
import type { ChatMessage } from '@/types'
import { User, Service, Promotion } from '@element-plus/icons-vue'
import { Service as ServiceIcon } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const isTyping = ref(false)
const messagesContainer = ref<HTMLElement>()
const suggestedQuestions = ref<string[]>([
  'Check recent anomalies in Plant A',
  'Show pH trends for all plants',
  'What violations were detected today?'
])

const formatTime = (iso: string) => {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const renderMarkdown = (text: string) => {
  // Simple markdown-like rendering
  return text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const sendSuggested = (question: string) => {
  inputMessage.value = question
  sendMessage()
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isTyping.value) return

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

  isTyping.value = true

  try {
    const response = await queryApi.query({
      query,
      context: {
        page: 'chat'
      }
    })

    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response.content || response.answer || response.result || 'Analysis complete',
      timestamp: new Date().toISOString(),
      evidence: response.evidence,
      chartData: response.chartData
    }

    messages.value.push(assistantMessage)

    // 渲染图表（如果有）
    if (response.chartData) {
      nextTick(() => {
        const container = document.querySelector(`[data-chart-id="${assistantMessage.id}"]`) as HTMLElement
        if (container) {
          const chart = echarts.init(container)
          chart.setOption(response.chartData)
        }
      })
    }
  } catch (error) {
    console.error('Query failed:', error)
    ElMessage.error('Failed to get response from AI assistant')

    const errorMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: 'Sorry, I encountered an error processing your request. Please try again.',
      timestamp: new Date().toISOString()
    }
    messages.value.push(errorMessage)
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

onMounted(() => {
  // Welcome message
  messages.value.push({
    id: 'welcome',
    role: 'assistant',
    content: 'Hello! I am your AI assistant for wastewater monitoring. I can help you with:\n\n* Analyzing water quality data\n* Detecting anomalies and violations\n* Explaining regulations and compliance\n* Generating reports and evidence chains',
    timestamp: new Date().toISOString()
  })
})
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #1a1a2e;
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #333;
  background: #16213e;
}

.chat-header h2 {
  margin: 0;
  color: #eaeaea;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #333;
  color: #eaeaea;
}

.message.assistant .message-avatar {
  background: #409eff;
}

.message.user .message-avatar {
  background: #67c23a;
}

.message-content {
  background: #333;
  padding: 12px 16px;
  border-radius: 12px;
  color: #eaeaea;
  max-width: 600px;
  overflow-wrap: break-word;
}

.message.user .message-content {
  background: #409eff;
}

.message-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.message-text {
  line-height: 1.6;
  overflow-wrap: break-word;
  word-break: break-word;
}

.message-text :deep(code) {
  background: #444;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14px;
}

.message-evidence {
  margin-top: 12px;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 14px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
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

.suggested-questions {
  padding: 12px 20px;
  border-top: 1px solid #333;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  background: #16213e;
}

.suggested-label {
  font-size: 14px;
  color: #999;
}

.suggested-tag {
  cursor: pointer;
}

.chat-input {
  padding: 16px 20px;
  border-top: 1px solid #333;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #16213e;
}

.chat-input .el-textarea {
  flex: 1;
}

.chat-input .el-textarea :deep(.el-textarea__inner) {
  background: #333;
  border-color: #444;
  color: #eaeaea;
}

.chat-input .el-textarea :deep(.el-textarea__inner):focus {
  border-color: #409eff;
}

.message-chart {
  margin-top: 12px;
  padding: 8px 0;
  overflow: hidden;
}

.echarts-container {
  background: #2a2a3e;
  border-radius: 8px;
  min-height: 300px;
}
</style>
