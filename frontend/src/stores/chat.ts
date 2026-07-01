import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage, PageContext } from '@/types'
import { queryApi } from '@/api/query'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const currentSessionId = ref<string | null>(null)
  const pageContext = ref<PageContext | null>(null)

  // Send message
  const sendMessage = async (content: string) => {
    loading.value = true

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    messages.value.push(userMessage)

    try {
      const response = await queryApi.sendQuery(content, pageContext.value)
      currentSessionId.value = response.sessionId

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString()
      }
      messages.value.push(assistantMessage)
    } catch (e: any) {
      messages.value.push({
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: 'Query failed, please try again later',
        timestamp: new Date().toISOString()
      })
    } finally {
      loading.value = false
    }
  }

  // Set page context
  const setPageContext = (context: PageContext) => {
    pageContext.value = context
  }

  // Clear messages
  const clearMessages = () => {
    messages.value = []
    currentSessionId.value = null
  }

  return {
    messages,
    loading,
    currentSessionId,
    pageContext,
    sendMessage,
    setPageContext,
    clearMessages
  }
})
