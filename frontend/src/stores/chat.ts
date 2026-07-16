import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage, PageContext } from '@/types'
import type { QueryResponse } from '@/api/types/api.types'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const currentSessionId = ref<string>()
  const loading = ref(false)
  const pageContext = ref<PageContext | null>(null)

  const messageCount = computed(() => messages.value.length)
  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  const addUserMessage = (content: string) => {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }
    messages.value.push(message)
  }

  const addAssistantMessage = (response: QueryResponse) => {
    const message: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response.content,
      timestamp: response.timestamp,
      chartData: response.chartData,
      evidence: response.decision_path
    }
    messages.value.push(message)
  }

  const addErrorMessage = (content: string) => {
    const message: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'system',
      content,
      timestamp: new Date().toISOString()
    }
    messages.value.push(message)
  }

  const clearMessages = () => {
    messages.value = []
    currentSessionId.value = undefined
  }

  const setSessionId = (id: string) => {
    currentSessionId.value = id
  }

  const setLoading = (value: boolean) => {
    loading.value = value
  }

  const setPageContext = (context: PageContext) => {
    pageContext.value = context
  }

  return {
    messages,
    currentSessionId,
    loading,
    pageContext,
    messageCount,
    lastMessage,
    addUserMessage,
    addAssistantMessage,
    addErrorMessage,
    clearMessages,
    setSessionId,
    setLoading,
    setPageContext
  }
})
