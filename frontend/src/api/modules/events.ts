import api from '../client'
import type { EventListResponse } from '../types/api.types'

export const eventsService = {
  list: (params?: any) => api.get<unknown, EventListResponse>('/events', { params }),
  detail: (id: string) => api.get<unknown, any>(`/events/${id}`),
  updateStatus: (id: string, status: string) => api.put<unknown, void>(`/events/${id}/status`, { status }),
}
