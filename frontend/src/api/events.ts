import api from './index'
import type { AlertEvent } from '@/types'

export const eventsApi = {
  // Get event list
  getEvents: (params: {
    startTime?: string
    endTime?: string
    type?: string
    plantId?: string
    severity?: string
    status?: string
    page?: number
    pageSize?: number
  }) => {
    return api.get<any, { data: AlertEvent[]; total: number }>('/events', { params })
  },

  // Get event detail
  getEventDetail: (id: string) => {
    return api.get<any, AlertEvent>(`/events/${id}`)
  },

  // Update event status
  updateEventStatus: (id: string, status: string) => {
    return api.put<any, AlertEvent>(`/events/${id}/status`, { status })
  },

  // Export events
  exportEvents: (params: any, format: 'xlsx' | 'pdf' | 'json' = 'xlsx') => {
    return api.get(`/events/export`, {
      params: { ...params, format },
      responseType: 'blob'
    })
  }
}
