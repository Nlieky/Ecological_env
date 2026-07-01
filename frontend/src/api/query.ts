import api from './index'
import type { ChatMessage } from '@/types'

export const queryApi = {
  // Send query
  sendQuery: (query: string, context?: any) => {
    return api.post<any, { sessionId: string; content: string }>('/query', {
      query,
      context
    })
  }
}
