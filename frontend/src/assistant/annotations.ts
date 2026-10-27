import { formatSamplingTime } from '@/composables/dashboardData'
import type { Annotation } from '@/stores/action'

export interface AnnotationContext {
  plant: string; source: string; start: string; end: string
  indicator: string; side: 'influent' | 'effluent'; algorithm: string; timezone?: string
}
export interface SamplePoint { time: string; value: number | null }

/** Full business-calendar timestamp, never browser-local parsing or month/day truncation. */
export function samplingTimeKey(value: string, timezone = 'Asia/Shanghai'): string | null {
  if (typeof value !== 'string') return null
  const aware = /(Z|[+-]\d{2}:?\d{2})$/.test(value)
  if (aware && Number.isNaN(new Date(value.replace(' ', 'T')).getTime())) return null
  const text = aware ? formatSamplingTime(value.replace(' ', 'T'), timezone).split('（')[0]! : value.replace('T', ' ')
  const match = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::(\d{2}))?(?:\.(\d+))?$/.exec(text)
  if (!match) return null
  const [, year, month, day, hour, minute, second = '00', fraction = ''] = match
  const date = new Date(Date.UTC(+year!, +month! - 1, +day!, +hour!, +minute!, +second))
  if (date.getUTCFullYear() !== +year! || date.getUTCMonth() !== +month! - 1 || date.getUTCDate() !== +day! || date.getUTCHours() !== +hour! || date.getUTCMinutes() !== +minute! || date.getUTCSeconds() !== +second) return null
  const ms = aware ? String(new Date(value.replace(' ', 'T')).getUTCMilliseconds()).padStart(3, '0') : fraction.padEnd(3, '0').slice(0, 3)
  return `${year}-${month}-${day} ${hour}:${minute}:${second}.${ms}`
}

export function matchAnnotations(annotations: Annotation[], samples: SamplePoint[], timezone = 'Asia/Shanghai') {
  const byTime = new Map(samples.map((point, index) => [samplingTimeKey(point.time, timezone), { point, index }]))
  byTime.delete(null)
  const seen = new Set<string>()
  const points: { coord: [number, number]; value: string; itemStyle: { color: string } }[] = []
  for (const annotation of annotations) {
    const key = samplingTimeKey(annotation.timestamp, timezone)
    const sample = key ? byTime.get(key) : undefined
    // The current detector rounds returned values to 2 decimals. Compare at
    // that precision, then place the marker at the actual displayed sample.
    if (!key || seen.has(key) || !sample || typeof sample.point.value !== 'number' || !Number.isFinite(sample.point.value) || !Number.isFinite(annotation.value) || Math.abs(sample.point.value - annotation.value) > .00500001) continue
    seen.add(key)
    points.push({ coord: [sample.index, sample.point.value], value: annotation.type, itemStyle: { color: '#ef4444' } })
  }
  return { points, matched: points.length, unmatched: annotations.length - points.length }
}

export function sameAnnotationWindow(binding: AnnotationContext, current: { plant: string; source: string; start?: string; end?: string }) {
  const zone = binding.timezone || 'Asia/Shanghai'
  return binding.plant === current.plant && binding.source === current.source &&
    !!samplingTimeKey(binding.start, zone) && !!samplingTimeKey(binding.end, zone) &&
    samplingTimeKey(binding.start, zone) === samplingTimeKey(current.start || '', zone) &&
    samplingTimeKey(binding.end, zone) === samplingTimeKey(current.end || '', zone)
}
