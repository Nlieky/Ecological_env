import { onBeforeUnmount } from 'vue'

/** 间隔轮询;start 时立即调一次,随后每 interval(ms)调一次;组件卸载自动 stop。 */
export function usePolling(fn: () => void | Promise<void>, interval: number) {
  let timer: ReturnType<typeof setInterval> | null = null

  function start() {
    if (timer) return
    void fn()
    timer = setInterval(() => void fn(), interval)
  }
  function stop() {
    if (timer) { clearInterval(timer); timer = null }
  }

  onBeforeUnmount(stop)
  return { start, stop }
}
