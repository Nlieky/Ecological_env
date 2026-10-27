import { ref } from 'vue'
import type { ConversationListItem } from '@/api/types/api.types'
import { requestGate } from './dashboardData'

type Envelope = { success: boolean; data?: { conversations: ConversationListItem[]; total_count: number }; error?: { message?: string } }
export function useAuditList(
  fetchList: (page: number, pageSize: number, search: string) => Promise<Envelope>,
  select: (id: string) => Promise<unknown>,
  options: { selectedId?: () => string; pageSize?: number } = {},
) {
  const conversations = ref<ConversationListItem[]>([])
  const total = ref(0); const loading = ref(false); const error = ref('')
  const page = ref(1); const search = ref(''); const pageSize = options.pageSize ?? 50
  const gate = requestGate()
  let searchTimer: ReturnType<typeof setTimeout> | undefined
  async function load() {
    const id = gate.begin()
    if (id === null) return
    loading.value = true; error.value = ''
    try {
      const response = await fetchList(page.value, pageSize, search.value)
      if (!gate.current(id)) return
      if (!response.success || !response.data) throw new Error(response.error?.message || '会话列表响应无效')
      conversations.value = response.data.conversations
      total.value = response.data.total_count
      if (conversations.value.length && !options.selectedId?.()) await select(conversations.value[0].id)
    } catch (reason) {
      if (gate.current(id)) error.value = `会话列表加载失败：${reason instanceof Error ? reason.message : String(reason)}`
    } finally {
      if (gate.current(id)) loading.value = false
    }
  }
  function setSearch(value: string) { search.value = value.trim().replace(/\s+/g, ' '); page.value = 1; return load() }
  function scheduleSearch(value: string, delay = 300) {
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(() => { searchTimer = undefined; void setSearch(value) }, delay)
  }
  function setPage(value: number) { page.value = Math.max(1, value); return load() }
  function dispose() { if (searchTimer) clearTimeout(searchTimer); gate.dispose() }
  return { conversations, total, loading, error, page, search, pageSize, setSearch, scheduleSearch, setPage, load, dispose }
}
