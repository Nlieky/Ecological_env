import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/** 把当前 tab 同步到 route.query[queryKey],支持深链与刷新保持。 */
export function useRouteTabState(tabs: string[], defaultTab = '', queryKey = 'tab') {
  const route = useRoute()
  const router = useRouter()
  const normalize = (t: string) => (tabs.includes(t) ? t : defaultTab || tabs[0])

  const activeTab = ref(normalize(String(route.query[queryKey] || defaultTab)))

  watch(activeTab, (t) => {
    if (t !== route.query[queryKey]) {
      router.replace({ query: { ...route.query, [queryKey]: t } })
    }
  })

  return { activeTab, normalize }
}
