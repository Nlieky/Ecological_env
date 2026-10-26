import { describe, expect, it, vi } from 'vitest'
import { dashboardRecords, latestValues, finiteStats, dateRange, contextLabel, plantStatusLabel, requestGate, dashboardSnapshot, shanghaiTime, advanceDate, formatSamplingTime, initializeMetrics, annotationCursor, shortSamplingTime } from '../dashboardData'

describe('dashboard data contract', () => {
  it('formats tree sampling instants in the same business timezone as the board', () => {
    expect(shortSamplingTime('2026-07-25 06:00:00+00:00', 'Asia/Shanghai')).toBe('07-25 14:00')
    expect(shortSamplingTime('2026-07-25 06:00:00+00:00', 'UTC')).toBe('07-25 06:00')
  })
  it('locates annotations on the union timeline, not the sparse indicator index', () => {
    const rows = Array.from({ length: 110 }, (_, i) => ({ timestamp: `t${i}`, influent: {}, effluent: {} }))
    expect(annotationCursor(rows, 't100', 105, 24)).toBe(105)
    expect(annotationCursor(rows, 't100', 12, 24)).toBe(110)
    expect(annotationCursor(rows, 'missing', 12, 24)).toBe(12)
  })
  it('does not select a shared plant or load after disposal during tree fetch', async () => {
    let resolve!: () => void
    const tree = new Promise<void>(r => { resolve = r })
    const gate = requestGate(); const select = vi.fn(); const load = vi.fn()
    const pending = initializeMetrics(() => tree, gate, select, load)
    gate.dispose(); resolve(); await pending
    expect(select).not.toHaveBeenCalled(); expect(load).not.toHaveBeenCalled()
  })
  it('rejects all new request starts after disposal', () => {
    const gate = requestGate(); gate.dispose()
    expect(gate.alive()).toBe(false)
    expect(gate.begin()).toBeNull()
  })
  it('advances replay by exactly seven calendar dates across month and year', () => {
    for (const zone of ['Asia/Shanghai', 'UTC', 'America/New_York']) {
      vi.stubEnv('TZ', zone)
      expect(advanceDate('2026-01-01', 7)).toBe('2026-01-08')
      expect(advanceDate('2026-01-29', 7)).toBe('2026-02-05')
      expect(advanceDate('2026-12-28', 7)).toBe('2027-01-04')
    }
    vi.unstubAllEnvs()
  })
  it('formats sample metadata in its declared timezone and labels unknown timezone', () => {
    expect(formatSamplingTime('2026-01-01T00:00:00Z', 'Asia/Shanghai')).toBe('2026-01-01 08:00:00（Asia/Shanghai）')
    expect(formatSamplingTime('2026-01-01T00:00:00Z', 'UTC')).toBe('2026-01-01 00:00:00（UTC）')
    expect(formatSamplingTime('2026-01-01 00:00:00')).toContain('时区未核验')
  })
  const indicators = { COD: { series: { influent: [{ time: '2026-01-01 01:00:00', value: 3 }, { time: '2026-01-01 03:00:00', value: null }], effluent: [{ time: '2026-01-01 02:00:00', value: 2 }] } }, TN: { series: { influent: [], effluent: [{ time: '2026-01-01 04:00:00', value: 1 }] } } }
  it('unions sorted timestamps from every indicator and side including null', () => {
    const rows = dashboardRecords(indicators)
    expect(rows.map(r => r.timestamp)).toEqual(['2026-01-01T01:00:00', '2026-01-01T02:00:00', '2026-01-01T03:00:00', '2026-01-01T04:00:00'])
    expect(rows[2].influent.COD).toBeNull()
    expect(rows[1].effluent.COD).toBe(2)
  })
  it('finds each side latest finite value independently', () => expect(latestValues(dashboardRecords(indicators), 'COD')).toEqual({ influent: 3, effluent: 2 }))
  it('skips null and nonfinite values in statistics', () => expect(finiteStats([null, NaN, Infinity, 2, 4])).toEqual({ mean: 3, min: 2, max: 4 }))
  it('defaults end date to the start and never caps long ranges', () => {
    expect(dateRange('2026-01-01', '')).toEqual({ anchor: '2026-01-01', endDate: '2026-01-01' })
    expect(dateRange('2026-01-01', '2026-02-01').endDate).toBe('2026-02-01')
    expect(() => dateRange('2026-02-01', '2026-01-01')).toThrow('结束日期')
  })
  it('reports source and mode without inventing live data', () => {
    expect(contextLabel()).toContain('未核验')
    expect(contextLabel({ origin: 'real', mode: 'historical' })).toBe('真实数据 · 历史数据')
    expect(plantStatusLabel('online')).toBe('有数据（时效未核验）')
    expect(plantStatusLabel('future')).toBe('未来时间数据')
  })
  it('invalidates stale requests and all requests after disposal', () => {
    const gate = requestGate(); const a = gate.begin(); const b = gate.begin()
    expect(gate.current(a)).toBe(false); expect(gate.current(b)).toBe(true)
    gate.dispose(); expect(gate.current(b)).toBe(false)
  })
  it('retains response metadata alongside the exact response records', () => {
    const response = { indicators, data_context: { origin: 'simulated', mode: 'simulation' }, latest_time: '2026-01-01 04:00:00' }
    const snapshot = dashboardSnapshot(response)
    expect(snapshot.dashboard).toBe(response)
    expect(snapshot.records[3].effluent.TN).toBe(1)
    expect(snapshot.dashboard.data_context.origin).toBe('simulated')
  })
  it('converts UTC to Shanghai and keeps local timestamps local', () => {
    expect(shanghaiTime('2026-01-01T00:00:00Z')).toBe('2026-01-01 08:00:00')
    expect(shanghaiTime('2026-01-01 08:00:00')).toBe('2026-01-01 08:00:00')
    expect(shanghaiTime(undefined)).toBe('—')
  })
})
