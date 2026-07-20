import { defineStore } from 'pinia'
import { ref } from 'vue'
import { monitoringService } from '@/api/modules/monitoring'
import type { RealtimeData, DataQuality } from '@/api/types/api.types'

export const useRealtimeStore = defineStore('realtime', () => {
  const realtime = ref<RealtimeData | null>(null)
  const quality = ref<DataQuality | null>(null)
  const loading = ref(false)
  const lastUpdate = ref<string>('')

  async function fetchRealtime() {
    loading.value = true
    try {
      realtime.value = await monitoringService.realtime()
      quality.value = await monitoringService.quality('24h')
      lastUpdate.value = realtime.value?.timestamp || ''
    } finally {
      loading.value = false
    }
  }
  return { realtime, quality, loading, lastUpdate, fetchRealtime }
})
