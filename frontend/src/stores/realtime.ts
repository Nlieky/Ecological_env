import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PlantData } from '@/api/types/api.types'

export const useRealtimeStore = defineStore('realtime', () => {
  const plants = ref<PlantData[]>([])
  const loading = ref(false)
  const lastUpdate = ref<string>()

  const setPlants = (data: PlantData[]) => {
    plants.value = data
    lastUpdate.value = new Date().toISOString()
  }

  const getPlantById = (id: string) => {
    return plants.value.find(p => p.id === id)
  }

  return {
    plants,
    loading,
    lastUpdate,
    setPlants,
    getPlantById
  }
})
