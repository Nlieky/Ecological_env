import api from '../client'
import type { ConversationListResponse, ConversationDetail } from '../types/api.types'

export const conversationsService = {
  list: (page = 1, pageSize = 20, search?: string) =>
    api.get<unknown, { success: boolean; data: ConversationListResponse }>('/v1/conversations', {
      params: { page, page_size: pageSize, search },
    }),
  create: (title?: string) =>
    api.post<unknown, { success: boolean; data: { id: string; title: string; started_at: string } }>(
      '/v1/conversations', { title }),
  detail: (id: string) =>
    api.get<unknown, { success: boolean; data: ConversationDetail }>(`/v1/conversations/${id}`),
  delete: (id: string) =>
    api.delete<unknown, { success: boolean }>(`/v1/conversations/${id}`),
  clearAll: () =>
    api.delete<unknown, { success: boolean }>('/v1/conversations'),
}
