import api from '../client'
import type { EventListRequest, AlertEvent, EventListResponse } from '../types/api.types'

export class EventsService {
  /**
   * 获取事件列表
   */
  async getEvents(params?: EventListRequest): Promise<EventListResponse> {
    return api.get('/events', { params })
  }

  /**
   * 获取事件详情
   */
  async getEventDetail(id: string): Promise<AlertEvent> {
    return api.get(`/events/${id}`)
  }

  /**
   * 更新事件状态
   */
  async updateStatus(id: string, status: string): Promise<void> {
    return api.put(`/events/${id}/status`, { status })
  }

  /**
   * 导出事件报告
   */
  async exportEvents(params?: any): Promise<Blob> {
    return api.get('/events/export', {
      params,
      responseType: 'blob'
    })
  }
}

export const eventsService = new EventsService()
