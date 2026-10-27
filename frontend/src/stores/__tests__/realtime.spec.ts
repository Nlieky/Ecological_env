import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { monitoringService } from '@/api/modules/monitoring'
import { useRealtimeStore } from '../realtime'
import { usePlantsStore } from '../plants'
beforeEach(() => { setActivePinia(createPinia()); vi.restoreAllMocks() })
it('does not query unscoped legacy monitoring before plant selection', async () => {
  const query = vi.spyOn(monitoringService, 'realtime').mockResolvedValue({} as never)
  vi.spyOn(monitoringService, 'quality').mockResolvedValue({} as never)
  await useRealtimeStore().fetchRealtime()
  expect(query).not.toHaveBeenCalled()
})
it('passes selected plant to both monitoring queries', async () => {
  const query = vi.spyOn(monitoringService, 'realtime').mockResolvedValue({ timestamp: 't' } as never)
  const quality = vi.spyOn(monitoringService, 'quality').mockResolvedValue({} as never)
  usePlantsStore().selectPlant('selected')
  await useRealtimeStore().fetchRealtime()
  expect(query).toHaveBeenCalledWith('selected')
  expect(quality).toHaveBeenCalledWith('selected', '24h')
})
