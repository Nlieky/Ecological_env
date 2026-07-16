import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { PageContext } from '@/api/types/api.types'

export function useQueryAgent() {
  const chatStore = useChatStore()

  const query = async (content: string, context?: PageContext) => {
    // Update page context if provided
    if (context) {
      chatStore.setPageContext(context)
    }

    // Send message using existing store method
    await chatStore.sendMessage(content)

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
