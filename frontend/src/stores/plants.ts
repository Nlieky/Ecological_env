import { defineStore } from 'pinia'
import { ref } from 'vue'
import { plantsService } from '@/api/modules/plants'
import type { PlantTree, PlantDashboard } from '@/api/types/api.types'

export const usePlantsStore = defineStore('plants', () => {
  const tree = ref<PlantTree | null>(null)
  const treeLoading = ref(false)
  const treeError = ref<string | null>(null)

  const dashboard = ref<PlantDashboard | null>(null)
  const dashboardLoading = ref(false)

  async function fetchTree(force = false) {
    if (tree.value && !force) return tree.value
    treeLoading.value = true; treeError.value = null
    try {
      const r = await plantsService.tree()
      tree.value = r.data
      return r.data
    } catch (e: any) {
      treeError.value = e?.message || '目录树加载失败'
      return null
    } finally { treeLoading.value = false }
  }

  async function fetchDashboard(plantId: string, hours = 24) {
    dashboardLoading.value = true
    try {
      const r = await plantsService.dashboard(plantId, hours)
      dashboard.value = r.data
      return r.data
    } catch { dashboard.value = null; return null }
    finally { dashboardLoading.value = false }
  }

  return { tree, treeLoading, treeError, dashboard, dashboardLoading, fetchTree, fetchDashboard }
})
