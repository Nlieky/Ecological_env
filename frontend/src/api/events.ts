import api from './index'
import type { AlertEvent } from '@/types'

export const eventsApi = {
  // Get event list (alias for getEvents)
  list: (params: {
    startTime?: string
    endTime?: string
    type?: string
    plantId?: string
    severity?: string
    status?: string
    page?: number
    page_size?: number
  }) => {
    return api.get<any, { items: AlertEvent[]; total: number }>('/events', { params })
  },

  // Legacy method
  getEvents: (params: any) => {
    return api.get<any, { data: AlertEvent[]; total: number }>('/events', { params })
  },

  // Get event detail
  getEventDetail: (id: string) => {
    return api.get<any, AlertEvent>(`/events/${id}`)
  },

  // Update event status (alias for updateEventStatus)
  updateStatus: (id: string, status: string) => {
    return api.put<any, AlertEvent>(`/events/${id}/status`, { status })
  },

  // Legacy method
  updateEventStatus: (id: string, status: string) => {
    return api.put<any, AlertEvent>(`/events/${id}/status`, { status })
  },

  // Export events (alias for exportEvents)
  export: (params: any) => {
    return api.get('/events/export', {
      params,
      responseType: 'blob'
    })
  },

  // Legacy method
  exportEvents: (params: any, format: 'xlsx' | 'pdf' | 'json' = 'xlsx') => {
    return api.get(`/events/export`, {
      params: { ...params, format },
      responseType: 'blob'
    })
  }
}
