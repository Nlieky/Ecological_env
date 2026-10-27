import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { plantsService } from '@/api/modules/plants'
import { usePlantsStore } from '../plants'
import type { PlantDashboard } from '@/api/types/api.types'

beforeEach(() => { setActivePinia(createPinia()); vi.restoreAllMocks() })
it('retains the last successful snapshot when the same query refresh fails', async () => {
  vi.spyOn(plantsService, 'dashboard').mockResolvedValueOnce({ success: true, data: dashboard('same') }).mockRejectedValueOnce(new Error('refresh unavailable'))
  const store = usePlantsStore(); await store.fetchDashboard('same')
  await store.fetchDashboard('same')
  expect(store.dashboard?.plant_id).toBe('same')
  expect(store.dashboardError).toBe('refresh unavailable')
})
it('clears old same-plant context immediately when window or anchor changes', async () => {
  vi.spyOn(plantsService, 'dashboard').mockResolvedValueOnce({ success: true, data: dashboard('same') }).mockImplementationOnce(() => new Promise(() => {}))
  const store = usePlantsStore(); await store.fetchDashboard('same', 24)
  void store.fetchDashboard('same', 6, '2026-01-01')
  expect(store.dashboard).toBeNull()
})
function dashboard(plant: string): PlantDashboard { return { plant_id: plant, window_hours: 24, indicators: {}, influent_points: 0, effluent_points: 0 } }
it('only publishes the latest requested plant response', async () => {
  let resolveOld!: (value: { success: boolean; data: PlantDashboard }) => void
  vi.spyOn(plantsService, 'dashboard').mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve })).mockResolvedValueOnce({ success: true, data: dashboard('new') })
  const store = usePlantsStore(); const old = store.fetchDashboard('old')
  await store.fetchDashboard('new'); resolveOld({ success: true, data: dashboard('old') }); await old
  expect(store.dashboard?.plant_id).toBe('new')
})
it('distinguishes failed requests from successful empty dashboards', async () => {
  vi.spyOn(plantsService, 'dashboard').mockRejectedValueOnce(new Error('database unavailable')).mockResolvedValueOnce({ success: true, data: dashboard('empty') })
  const store = usePlantsStore(); await store.fetchDashboard('broken')
  expect(store.dashboardError).toBe('database unavailable'); expect(store.dashboard).toBeNull()
  await store.fetchDashboard('empty'); expect(store.dashboardError).toBeNull(); expect(store.dashboard?.plant_id).toBe('empty')
})
it('invalidates pending requests when a board is disposed', async () => {
  let resolve!: (value: { success: boolean; data: PlantDashboard }) => void
  vi.spyOn(plantsService, 'dashboard').mockImplementation(() => new Promise(r => { resolve = r }))
  const store = usePlantsStore(); const pending = store.fetchDashboard('old'); store.invalidateDashboard()
  resolve({ success: true, data: dashboard('old') }); await pending
  expect(store.dashboard).toBeNull(); expect(store.dashboardLoading).toBe(false)
})
