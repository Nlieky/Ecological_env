import { defineStore } from 'pinia'
import { ref } from 'vue'
import { monitoringService } from '@/api/modules/monitoring'
import { usePlantsStore } from '@/stores/plants'
import type { RealtimeData, DataQuality } from '@/api/types/api.types'

export const useRealtimeStore = defineStore('realtime', () => {
  const realtime = ref<RealtimeData | null>(null)
  const quality = ref<DataQuality | null>(null)
  const loading = ref(false)
  const lastUpdate = ref<string>('')

  async function fetchRealtime() {
    const plants = usePlantsStore()
    const plantId = plants.activePlant
    if (!plantId) { realtime.value = null; quality.value = null; lastUpdate.value = ''; return }
    loading.value = true
    try {
      const data = await monitoringService.realtime(plantId)
      const dataQuality = await monitoringService.quality(plantId, '24h')
      if (plants.activePlant !== plantId) return
      realtime.value = data
      quality.value = dataQuality
      lastUpdate.value = realtime.value?.timestamp || ''
    } finally {
      loading.value = false
    }
  }
  return { realtime, quality, loading, lastUpdate, fetchRealtime }
})
