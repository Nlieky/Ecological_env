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

      <div v-if="isQuerying" class="message assistant">
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
        :disabled="isQuerying"
      />
      <el-button
        type="primary"
        @click="sendMessage"
        :loading="isQuerying"
        :disabled="!inputMessage.trim()"
      >
        <el-icon><Promotion /></el-icon>
        Send (Ctrl+Enter)
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useQueryAgent } from '@/composables/useQueryAgent'
import { useChatStore } from '@/stores/chat'
import { User, Service, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const { query, isQuerying, currentSessionId } = useQueryAgent()
const chatStore = useChatStore()

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const suggestedQuestions = ref<string[]>([
  '检查A厂最近的异常情况',
  '显示所有厂区pH趋势',
  '今天检测到哪些违规？'
])

const messages = computed(() => chatStore.messages)

const formatTime = (iso: string) => {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const renderMarkdown = (text: string) => {
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
  if (!inputMessage.value.trim() || isQuerying.value) return

  const queryText = inputMessage.value
  inputMessage.value = ''

  try {
    const response = await query(queryText, { page: 'chat' })

    if (response.chartData) {
      nextTick(() => {
        const messageId = (Date.now() + 1).toString()
        const container = document.querySelector(`[data-chart-id="${messageId}"]`) as HTMLElement
        if (container) {
          const chart = echarts.init(container)
          chart.setOption(response.chartData)
        }
      })
    }
  } catch (error) {
    ElMessage.error('查询失败')
  }

  scrollToBottom()
}

onMounted(() => {
  chatStore.addAssistantMessage({
    content: '你好！我是废水监测AI助手。我可以帮助你：\n\n* 分析水质数据\n* 检测异常和违规\n* 解释法规和合规性\n* 生成报告和证据链',
    session_id: '',
    timestamp: new Date().toISOString(),
    decision_path: []
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
