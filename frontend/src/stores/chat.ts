import { defineStore } from 'pinia'
import { ref } from 'vue'
import { conversationsService } from '@/api/modules/conversations'
import type { ConversationListItem, ConversationDetail } from '@/api/types/api.types'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<ConversationListItem[]>([])
  const current = ref<ConversationDetail | null>(null)
  const loading = ref(false)

  async function fetchConversations(page = 1) {
    const res = await conversationsService.list(page)
    conversations.value = res.data.conversations
  }
  async function openConversation(id: string) {
    const res = await conversationsService.detail(id)
    current.value = res.data
  }
  return { conversations, current, loading, fetchConversations, openConversation }
})
