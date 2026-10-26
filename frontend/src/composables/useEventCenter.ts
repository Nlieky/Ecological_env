import { computed, ref } from 'vue'
import type { AlertEvent, EventListRequest, EventListResponse } from '@/api/types/api.types'

type Status = AlertEvent['status']
interface CaseLinkEl { id: string; label: string; type: string }
interface EventApi {
  list: (params: EventListRequest) => Promise<EventListResponse>
  updateStatus: (id: string, status: Status) => Promise<AlertEvent>
  node: (id: string) => Promise<{ neighbors: Record<string, { id: string; label: string }[]> }>
}
const transitions: Record<Status, Status[]> = { pending: ['pending', 'processing', 'resolved', 'ignored'], processing: ['processing', 'resolved', 'ignored'], resolved: ['resolved'], ignored: ['ignored'] }
const message = (reason: unknown) => reason instanceof Error ? reason.message : '请求失败'
const copy = (event: AlertEvent): AlertEvent => JSON.parse(JSON.stringify(event))

export function useEventCenter(api: EventApi) {
  const events = ref<AlertEvent[]>([]); const total = ref(0); const page = ref(1); const pageSize = 20
  const severity = ref(''); const status = ref(''); const loading = ref(false); const listError = ref('')
  const current = ref<AlertEvent | null>(null); const drawerVisible = ref(false); const saveError = ref('')
  const caseLink = ref<CaseLinkEl[] | null>(null); const caseLinkLoading = ref(false); const caseLinkError = ref('')
  const savingIds = ref(new Set<string>())
  let disposed = false; let listSeq = 0; let relationSeq = 0; let selectionSeq = 0
  const saving = computed(() => !!current.value && savingIds.value.has(current.value.id))
  const allowedStatuses = computed(() => current.value ? transitions[current.value.status] : [])
  async function load(): Promise<void> {
    if (disposed) return
    const seq = ++listSeq; loading.value = true; listError.value = ''
    try {
      const response = await api.list({ page: page.value, pageSize, severity: severity.value || undefined, status: status.value || undefined })
      if (disposed || seq !== listSeq) return
      events.value = response.data; total.value = response.total
      const last = Math.max(1, Math.ceil(response.total / pageSize))
      if (!response.data.length && page.value > last) { page.value = last; await load() }
    } catch (reason) { if (!disposed && seq === listSeq) listError.value = `事件列表加载失败：${message(reason)}` }
    finally { if (!disposed && seq === listSeq) loading.value = false }
  }
  function filterChanged() { page.value = 1; return load() }
  function setPage(value: number) { page.value = Math.max(1, value); return load() }
  function openDetail(row: AlertEvent) {
    if (disposed) return
    selectionSeq++; relationSeq++; current.value = copy(row); drawerVisible.value = true; saveError.value = ''
    caseLink.value = null; caseLinkError.value = ''; caseLinkLoading.value = false
  }
  function closeDetail() {
    selectionSeq++; relationSeq++; drawerVisible.value = false; current.value = null
    saveError.value = ''; caseLink.value = null; caseLinkError.value = ''; caseLinkLoading.value = false
  }
  async function loadRelation() {
    if (disposed || !current.value || !drawerVisible.value) return
    const id = current.value.id; const seq = ++relationSeq
    caseLink.value = null; caseLinkError.value = ''; caseLinkLoading.value = true
    try {
      const response = await api.node(`case:${id}`)
      if (disposed || seq !== relationSeq) return
      const out: CaseLinkEl[] = []
      for (const type of ['plant', 'violation_pattern']) for (const node of response.neighbors[type] || []) out.push({ id: node.id, label: node.label, type })
      caseLink.value = out.length ? out : null
    } catch (reason) {
      if (!disposed && seq === relationSeq && (reason as { response?: { status?: number } })?.response?.status !== 404) caseLinkError.value = `关联链路加载失败：${message(reason)}`
    } finally { if (!disposed && seq === relationSeq) caseLinkLoading.value = false }
  }
  async function saveStatus(next: Status) {
    if (disposed || !current.value || saving.value || !allowedStatuses.value.includes(next)) return
    const id = current.value.id; const selection = selectionSeq
    savingIds.value = new Set([...savingIds.value, id]); saveError.value = ''
    try {
      const confirmed = await api.updateStatus(id, next)
      if (disposed) return
      events.value = events.value.map(row => row.id === id ? copy(confirmed) : row)
      if (current.value?.id === id) current.value = copy(confirmed)
      await load()
    } catch (reason) {
      if (!disposed && selection === selectionSeq && current.value?.id === id) saveError.value = `状态更新失败：${message(reason)}`
    } finally { const remaining = new Set(savingIds.value); remaining.delete(id); savingIds.value = remaining }
  }
  function dispose() { disposed = true; listSeq++; closeDetail(); loading.value = false }
  return { events, total, page, pageSize, severity, status, loading, listError, current, drawerVisible, saveError, saving, allowedStatuses, caseLink, caseLinkLoading, caseLinkError, load, filterChanged, setPage, openDetail, closeDetail, loadRelation, saveStatus, dispose }
}
