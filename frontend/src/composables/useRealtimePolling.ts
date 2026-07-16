import { ref, onMounted, onUnmounted } from 'vue'
import { useRealtimeStore } from '@/stores/realtime'
import { realtimeService } from '@/api/services/realtime.service'

export function useRealtimePolling(interval = 10000) {
  const realtimeStore = useRealtimeStore()
  const isPolling = ref(true)
  let timer: number | null = null

  const fetch = async () => {
    try {
      const data = await realtimeService.getAllPlants()
      realtimeStore.plants = data
    } catch (error) {
      console.error('Failed to fetch realtime data:', error)
    }
  }

  const startPolling = () => {
    if (timer) return
    fetch()
    timer = window.setInterval(fetch, interval)
    isPolling.value = true
  }

  const stopPolling = () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    isPolling.value = false
  }

  onMounted(() => {
    startPolling()
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    isPolling,
    startPolling,
    stopPolling,
    refresh: fetch
  }
}
