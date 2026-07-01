import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AlertEvent } from '@/types'
import { eventsApi } from '@/api/events'

export const useEventsStore = defineStore('events', () => {
  const events = ref<AlertEvent[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)

  // Get event list
  const fetchEvents = async (params?: any) => {
    loading.value = true
    try {
      const result = await eventsApi.getEvents({
        page: currentPage.value,
        pageSize: pageSize.value,
        ...params
      })
      events.value = result.data
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  // Update event status
  const updateStatus = async (id: string, status: string) => {
    await eventsApi.updateEventStatus(id, status)
    const index = events.value.findIndex(e => e.id === id)
    if (index !== -1) {
      events.value[index].status = status as any
    }
  }

  return {
    events,
    total,
    loading,
    currentPage,
    pageSize,
    fetchEvents,
    updateStatus
  }
})
