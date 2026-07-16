import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AlertEvent, EventListRequest } from '@/api/types/api.types'
import { eventsService } from '@/api/services/events.service'

export const useEventsStore = defineStore('events', () => {
  const events = ref<AlertEvent[]>([])
  const loading = ref(false)
  const pagination = ref({
    total: 0,
    page: 1,
    pageSize: 20
  })

  const fetchEvents = async (params?: EventListRequest) => {
    loading.value = true
    try {
      const response = await eventsService.getEvents(params)
      events.value = response.items
      pagination.value = {
        total: response.total,
        page: response.page,
        pageSize: response.pageSize
      }
    } finally {
      loading.value = false
    }
  }

  const updateStatus = async (id: string, status: string) => {
    await eventsService.updateStatus(id, status)
    const event = events.value.find(e => e.id === id)
    if (event) {
      event.status = status as any
    }
  }

  return {
    events,
    loading,
    pagination,
    fetchEvents,
    updateStatus
  }
})
