import { defineStore } from 'pinia'
import { ref } from 'vue'
import { eventsService } from '@/api/modules/events'
import type { AlertEvent } from '@/api/types/api.types'

export const useEventsStore = defineStore('events', () => {
  const events = ref<AlertEvent[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchEvents(params: any = { page: 1, page_size: 20 }) {
    loading.value = true
    try {
      const res = await eventsService.list(params)
      events.value = (res.data || []) as AlertEvent[]
      total.value = res.total || 0
    } finally {
      loading.value = false
    }
  }
  return { events, total, loading, fetchEvents }
})
