import api from '../client'
import type { PlantData, PlantTree, PlantDashboard } from '../types/api.types'

export const plantsService = {
  /** 旧 mock 接口(全厂总览用,保留兼容) */
  list: () => api.get<unknown, PlantData[]>('/realtime/plants'),

  /** 多厂区目录树(真实数据): 市→厂区→厂 */
  tree: () => api.get<unknown, { success: boolean; data: PlantTree }>('/v1/plants/tree'),

  /** 单厂看板数据(真实数据): 指标当前值+趋势+状态;anchor=YYYY-MM-DD 任意时间点开播取段 */
  dashboard: (plantId: string, hours = 24, anchor?: string, endDate?: string) =>
    api.get<unknown, { success: boolean; data: PlantDashboard }>(
      `/v1/plants/${encodeURIComponent(plantId)}/dashboard`, { params: { hours, ...(anchor ? { anchor } : {}), ...(endDate ? { end_date: endDate } : {}) } },
    ),
}
