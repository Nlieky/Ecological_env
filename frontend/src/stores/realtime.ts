import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PlantData } from '@/types'
import { realtimeApi } from '@/api/realtime'

export const useRealtimeStore = defineStore('realtime', () => {
  const plants = ref<PlantData[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Initialize plant data (4x4 grid, 1 with data)
  const initializePlants = async () => {
    loading.value = true
    error.value = null
    try {
      const data = await realtimeApi.getAllPlants()
      plants.value = data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  // Update single plant data
  const updatePlant = (plantId: string, data: Partial<PlantData>) => {
    const index = plants.value.findIndex(p => p.id === plantId)
    if (index !== -1) {
      plants.value[index] = { ...plants.value[index], ...data }
    }
  }

  return {
    plants,
    loading,
    error,
    initializePlants,
    updatePlant
  }
})
