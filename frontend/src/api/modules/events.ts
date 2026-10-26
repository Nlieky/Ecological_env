import api from '../client'
import type { AlertEvent, EventListRequest, EventListResponse } from '../types/api.types'

export const eventsService = {
  list: (params?: EventListRequest) => api.get<unknown, EventListResponse>('/events', { params }),
  detail: (id: string) => api.get<unknown, AlertEvent>(`/events/${id}`),
  updateStatus: (id: string, status: string) => api.put<unknown, AlertEvent>(`/events/${id}/status`, { status }),
}
