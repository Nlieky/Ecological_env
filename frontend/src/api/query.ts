import api from './index'

export const queryApi = {
  // Send query (alias for sendQuery)
  query: (params: { query: string; context?: any }) => {
    return api.post<any, { sessionId: string; answer: string; result: string; evidence?: any; chartData?: any }>('/query', params)
  },

  // Legacy method
  sendQuery: (query: string, context?: any) => {
    return api.post<any, { sessionId: string; content: string }>('/query', {
      query,
      context
    })
  }
}
