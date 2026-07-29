import api from '../client'
import type { QueryRequest, QueryResponse, CapabilitiesResponse } from '../types/api.types'

export const queryService = {
  execute: (req: QueryRequest) => api.post<unknown, QueryResponse>('/query', req),
  capabilities: () => api.get<unknown, CapabilitiesResponse>('/query/capabilities'),

  /** 流式查询（SSE-over-POST）：实时回调 progress/delta/done/error。返回 AbortController。
   * 用 fetch + ReadableStream（EventSource 只支持 GET，查询带 body 故用 fetch）。 */
  executeStream(
    { query, session_id }: { query: string; session_id?: string },
    cbs: {
      onProgress?: (e: { subagent: string; stage: string; summary?: string; chartData?: any }) => void
      onDelta?: (text: string) => void
      onDone?: (content: string, session_id: string) => void
      onError?: (message: string) => void
    },
  ) {
    const ctrl = new AbortController()
    fetch('/api/query/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id }),
      signal: ctrl.signal,
    })
      .then(async (res) => {
        if (!res.ok || !res.body) { cbs.onError?.(`HTTP ${res.status}`); return }
        const reader = res.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          let idx: number
          while ((idx = buf.indexOf('\n\n')) >= 0) {
            const raw = buf.slice(0, idx)
            buf = buf.slice(idx + 2)
            const line = raw.split('\n').find((l) => l.startsWith('data: '))
            if (!line) continue // keepalive / 注释行
            let evt: { type: string; [k: string]: unknown }
            try { evt = JSON.parse(line.slice(6)) } catch { continue }
            if (evt.type === 'progress') cbs.onProgress?.(evt as any)
            else if (evt.type === 'delta') cbs.onDelta?.((evt.text as string) ?? '')
            else if (evt.type === 'done') { cbs.onDone?.((evt.content as string) ?? '', (evt.session_id as string) ?? ''); return }
            else if (evt.type === 'error') { cbs.onError?.((evt.message as string) ?? '未知错误'); return }
          }
        }
      })
      .catch((e) => {
        if (e?.name !== 'AbortError') cbs.onError?.(e?.message || '流式连接失败')
      })
    return ctrl
  },
}
