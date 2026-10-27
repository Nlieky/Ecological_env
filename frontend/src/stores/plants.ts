import { defineStore } from 'pinia'
import { ref } from 'vue'
import { plantsService } from '@/api/modules/plants'
import type { PlantTree, PlantDashboard } from '@/api/types/api.types'

export const usePlantsStore = defineStore('plants', () => {
  const tree = ref<PlantTree | null>(null)
  const treeLoading = ref(false)
  const treeError = ref<string | null>(null)

  // 树展开状态提升到 store：路由跳转(PlantTree 重挂载)不丢展开/选中。
  // 多值数组而非单值手风琴——用户点开谁谁展开、关闭由用户自己关，互不影响
  // (之前单值模式点一个市其他市自动收起,违背直觉)。
  const openCities = ref<string[]>([])
  const openDists = ref<string[]>([])
  const activePlant = ref('')

  /** 市/区折叠切换（多值：加入或移出，不动其他节点） */
  function toggleCity(name: string) {
    openCities.value = openCities.value.includes(name)
      ? openCities.value.filter(n => n !== name)
      : [...openCities.value, name]
  }
  function toggleDist(name: string) {
    openDists.value = openDists.value.includes(name)
      ? openDists.value.filter(n => n !== name)
      : [...openDists.value, name]
  }

  /** 选中某厂：记录选中并确保父级链展开（点三级目录不再收回一级） */
  function selectPlant(pid: string, city?: string, dist?: string) {
    activePlant.value = pid
    if (city && !openCities.value.includes(city)) openCities.value = [...openCities.value, city]
    if (dist && !openDists.value.includes(dist)) openDists.value = [...openDists.value, dist]
  }
  /** 按厂名反查父级并展开（从 URL 直进单厂页时用） */
  function expandTo(pid: string) {
    if (!tree.value) return
    for (const c of tree.value.cities ?? []) {
      for (const d of c.districts ?? []) {
        if ((d.plants ?? []).some((p) => p.plant_id === pid)) {
          selectPlant(pid, c.name, d.name)
          return
        }
      }
    }
    // 未分组
    if ((tree.value.ungrouped ?? []).some((p) => p.plant_id === pid)
        && !openCities.value.includes('__ungrouped__')) {
      openCities.value = [...openCities.value, '__ungrouped__']
    }
  }

  const dashboard = ref<PlantDashboard | null>(null)
  const dashboardLoading = ref(false)
  const dashboardError = ref<string | null>(null)
  let dashboardGeneration = 0
  let dashboardQuery = ''
  function invalidateDashboard() {
    dashboardGeneration++
    dashboardLoading.value = false
  }

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

  async function fetchDashboard(plantId: string, hours = 24, anchor?: string, endDate?: string) {
    const generation = ++dashboardGeneration
    dashboardLoading.value = true
    dashboardError.value = null
    const query = JSON.stringify([plantId, hours, anchor || '', endDate || ''])
    if (dashboardQuery !== query) dashboard.value = null
    dashboardQuery = query
    try {
      const r = await plantsService.dashboard(plantId, hours, anchor, endDate)
      if (generation !== dashboardGeneration) return null
      dashboard.value = r.data
      return r.data
    } catch (e: unknown) {
      if (generation !== dashboardGeneration) return null
      dashboardError.value = e instanceof Error ? e.message : '看板数据加载失败'
      return null
    }
    finally { if (generation === dashboardGeneration) dashboardLoading.value = false }
  }

  return { tree, treeLoading, treeError, dashboard, dashboardLoading, dashboardError, invalidateDashboard,
    openCities, openDists, activePlant, toggleCity, toggleDist,
    selectPlant, expandTo, fetchTree, fetchDashboard }
})
