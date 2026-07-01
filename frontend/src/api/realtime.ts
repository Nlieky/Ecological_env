import api from './index'
import type { PlantData } from '@/types'

export const realtimeApi = {
  // Get all plants real-time data
  getAllPlants: () => {
    return api.get<any, PlantData[]>('/realtime/plants')
  },

  // Get single plant data
  getPlant: (id: string) => {
    return api.get<any, PlantData>(`/realtime/plants/${id}`)
  }
}
