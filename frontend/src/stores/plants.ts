import { defineStore } from 'pinia'
import { ref } from 'vue'
import { plantsService } from '@/api/modules/plants'
import type { PlantTree, PlantDashboard } from '@/api/types/api.types'

export const usePlantsStore = defineStore('plants', () => {
  const tree = ref<PlantTree | null>(null)
  const treeLoading = ref(false)
  const treeError = ref<string | null>(null)

  // 树展开状态提升到 store：路由跳转(PlantTree 重挂载)不丢展开/选中
  const openCity = ref('')
  const openDist = ref('')
  const activePlant = ref('')

  /** 选中某厂：记录选中并确保父级链展开（点三级目录不再收回一级） */
  function selectPlant(pid: string, city?: string, dist?: string) {
    activePlant.value = pid
    if (city) openCity.value = city
    if (dist) openDist.value = dist
  }
  /** 按厂名反查父级并展开（从 URL 直进单厂页时用） */
  function expandTo(pid: string) {
    if (!tree.value) return
    for (const c of tree.value.cities ?? []) {
      for (const d of c.districts ?? []) {
        if ((d.plants ?? []).some((p) => p.plant_id === pid)) {
          openCity.value = c.name
          openDist.value = d.name
          return
        }
      }
    }
    // 未分组
    if ((tree.value.ungrouped ?? []).some((p) => p.plant_id === pid)) openCity.value = '__ungrouped__'
  }

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

  async function fetchDashboard(plantId: string, hours = 24, anchor?: string) {
    dashboardLoading.value = true
    try {
      const r = await plantsService.dashboard(plantId, hours, anchor)
      dashboard.value = r.data
      return r.data
    } catch { dashboard.value = null; return null }
    finally { dashboardLoading.value = false }
  }

  return { tree, treeLoading, treeError, dashboard, dashboardLoading,
    openCity, openDist, activePlant, selectPlant, expandTo, fetchTree, fetchDashboard }
})
