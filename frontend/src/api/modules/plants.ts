import api from '../client'
import type { PlantData } from '../types/api.types'

export const plantsService = {
  list: () => api.get<unknown, PlantData[]>('/realtime/plants'),
}
