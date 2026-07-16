import api from '../client'
import type { PlantData } from '../types/api.types'

export class RealtimeService {
  /**
   * 获取所有污水厂数据
   */
  async getAllPlants(): Promise<PlantData[]> {
    return api.get('/realtime/plants')
  }

  /**
   * 获取单个污水厂数据
   */
  async getPlant(id: string): Promise<PlantData> {
    return api.get(`/realtime/plants/${id}`)
  }
}

export const realtimeService = new RealtimeService()
