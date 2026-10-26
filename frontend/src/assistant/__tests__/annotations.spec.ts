import { expect, it } from 'vitest'
import { matchAnnotations, samplingTimeKey, sameAnnotationWindow } from '../annotations'

it('matches full business timestamps across explicit offsets without browser timezone', () => {
  expect(samplingTimeKey('2026-07-01T02:00:00Z')).toBe(samplingTimeKey('2026-07-01 10:00:00'))
  expect(samplingTimeKey('2026-07-01T02:00:00Z', 'UTC')).toBe(samplingTimeKey('2026-07-01 02:00:00'))
  expect(samplingTimeKey('2026-02-30 10:00:00')).toBeNull()
  expect(samplingTimeKey('2026-07-01T02:00:00Z', 'invalid-zone')).toBeNull()
})
it('places rounded detector values at actual samples and rejects unmatched dates/values', () => {
  const samples = [{ time: '2026-07-01 10:00:00', value: 7.1234 }]
  const annotation = { timestamp: '2026-07-01T02:00:00Z', value: 7.12, type: '离群' }
  expect(matchAnnotations([annotation], samples).points[0]?.coord).toEqual([0, 7.1234])
  expect(matchAnnotations([{ ...annotation, timestamp: '2025-07-01 10:00:00' }], samples).unmatched).toBe(1)
  expect(matchAnnotations([{ ...annotation, value: 8 }], samples).unmatched).toBe(1)
  expect(matchAnnotations([annotation, annotation], samples).unmatched).toBe(1)
  expect(matchAnnotations([], samples)).toEqual({ points: [], matched: 0, unmatched: 0 })
})
it('binds annotations to factory, provenance, full sampling window', () => {
  const binding = { plant: 'A', source: 'real', start: '2026-07-01 00:00:00', end: '2026-07-02 00:00:00', indicator: 'TN', side: 'influent' as const, algorithm: 'iforest' }
  const current = { plant: 'A', source: 'real', start: binding.start, end: binding.end }
  expect(sameAnnotationWindow(binding, current)).toBe(true)
  for (const change of [{ plant: 'B' }, { source: 'simulated' }, { end: '2026-07-03 00:00:00' }]) expect(sameAnnotationWindow(binding, { ...current, ...change })).toBe(false)
})
