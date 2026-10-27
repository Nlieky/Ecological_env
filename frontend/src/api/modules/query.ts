import api from '../client'
import type { QueryRequest, QueryResponse, CapabilitiesResponse } from '../types/api.types'

export interface StreamTiming { queueElapsedMs?: number; turnElapsedMs?: number }

export const queryService = {
  execute: (req: QueryRequest) => api.post<unknown, QueryResponse>('/query', req),
  capabilities: () => api.get<unknown, CapabilitiesResponse>('/query/capabilities'),

  /** 流式查询（SSE-over-POST）：实时回调 progress/delta/done/error。返回 AbortController。
   * 用 fetch + ReadableStream（EventSource 只支持 GET，查询带 body 故用 fetch）。 */
  executeStream(
    { query, session_id, view_context, mode }: { query: string; session_id?: string; view_context?: string; mode?: string },
    cbs: {
      onProgress?: (e: { subagent: string; stage: string; summary?: string; chartData?: any; elapsed_ms?: number }) => void
      onAction?: (actionData: { cmd: string; [k: string]: unknown } | null) => void
      onDelta?: (text: string) => void
      onDone?: (content: string, session_id: string, timing?: StreamTiming) => void
      onError?: (message: string) => void
    },
  ) {
    const ctrl = new AbortController()
    let settled = false
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined
    const fail = (message: string) => {
      if (settled) return
      settled = true
      cbs.onError?.(message)
    }
    ctrl.signal.addEventListener('abort', () => {
      fail('已停止接收；服务器任务可能仍在运行')
      void reader?.cancel().catch(() => {})
    }, { once: true })
    fetch('/api/query/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id, view_context: view_context || undefined, mode }),
      signal: ctrl.signal,
    })
      .then(async (res) => {
        if (settled) { void res.body?.cancel().catch(() => {}); return }
        if (!res.ok) {
          let detail = ''
          try {
            const payload = await res.json()
            const message = typeof payload.detail === 'string' ? payload.detail : payload.detail?.message
            if (typeof message === 'string') detail = message.replace(/[<>\u0000-\u001f]/g, '').slice(0, 240)
          } catch { /* HTML/proxy bodies are not suitable user details. */ }
          fail(`HTTP ${res.status}${detail ? ': ' + detail : ''}`)
          return
        }
        if (!res.body) { fail('流式响应为空'); return }
        reader = res.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        try {
        for (;;) {
          const { done, value } = await reader.read()
          if (settled) return
          if (done) { fail('连接已结束，未收到完成事件'); return }
          buf += dec.decode(value, { stream: true })
          let boundary: RegExpExecArray | null
          while ((boundary = /\r?\n\r?\n/.exec(buf))) {
            if (settled) return
            const raw = buf.slice(0, boundary.index)
            buf = buf.slice(boundary.index + boundary[0].length)
            const data = raw.split(/\r?\n/).filter((l) => l.startsWith('data:')).map((l) => l.slice(5).replace(/^ /, '')).join('\n')
            if (!data) continue
            let evt: { type: string; [k: string]: unknown }
            try { evt = JSON.parse(data) } catch { continue }
            if (evt.type === 'progress') cbs.onProgress?.(evt as any)
            else if (evt.type === 'action') cbs.onAction?.((evt.actionData as any) ?? null)
            else if (evt.type === 'delta') cbs.onDelta?.((evt.text as string) ?? '')
            else if (evt.type === 'done') {
              settled = true
              const timing: StreamTiming = {}
              if (typeof evt.queue_elapsed_ms === 'number' && Number.isFinite(evt.queue_elapsed_ms)) timing.queueElapsedMs = Math.max(0, evt.queue_elapsed_ms)
              if (typeof evt.turn_elapsed_ms === 'number' && Number.isFinite(evt.turn_elapsed_ms)) timing.turnElapsedMs = Math.max(0, evt.turn_elapsed_ms)
              cbs.onDone?.((evt.content as string) ?? '', (evt.session_id as string) ?? '', timing)
              return
            }
            else if (evt.type === 'error') { fail((evt.message as string) ?? '未知错误'); return }
            if (settled) return
          }
        }
        } finally {
          void reader.cancel().catch(() => {})
          reader.releaseLock()
        }
      })
      .catch((e) => {
        fail(e?.name === 'AbortError' ? '已停止接收；服务器任务可能仍在运行' : e?.message || '流式连接失败')
      })
    return ctrl
  },
}
