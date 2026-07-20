import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const activePlant = ref<string>('第一污水处理厂')
  const dashboardFilters = ref({
    category: 'all' as 'all' | 'influent' | 'effluent',
    sort: 'anomaly' as 'anomaly' | 'value' | 'delta',
    timeWindow: '24h' as '1h' | '6h' | '24h',
  })
  function toggleSidebar() { sidebarCollapsed.value = !sidebarCollapsed.value }
  return { sidebarCollapsed, activePlant, dashboardFilters, toggleSidebar }
})
