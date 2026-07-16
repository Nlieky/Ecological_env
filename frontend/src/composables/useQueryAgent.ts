import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { PageContext } from '@/api/types/api.types'
import { queryService } from '@/api/services/query.service'

export function useQueryAgent() {
  const chatStore = useChatStore()

  const query = async (content: string, context?: PageContext) => {
    // Update page context if provided
    if (context) {
      chatStore.setPageContext(context)
    }

    // Add user message
    chatStore.addUserMessage(content)
    chatStore.setLoading(true)

    try {
      const response = await queryService.executeQuery({
        query: content,
        context
      })
      chatStore.setSessionId(response.session_id)
      chatStore.addAssistantMessage(response)
    } catch (error) {
      chatStore.addErrorMessage('Query failed, please try again later')
    } finally {
      chatStore.setLoading(false)
    }

    return {
      sessionId: chatStore.currentSessionId,
      messages: chatStore.messages
    }
  }

  return {
    query,
    isQuerying: computed(() => chatStore.loading),
    currentSessionId: computed(() => chatStore.currentSessionId),
    messages: computed(() => chatStore.messages),
    clearMessages: chatStore.clearMessages,
    setPageContext: chatStore.setPageContext
  }
}
