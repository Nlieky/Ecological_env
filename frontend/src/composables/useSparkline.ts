export type Trend = 'up' | 'down' | 'volatile' | 'flat'

interface ClassifyOpts { slopeThresh?: number; volatilityThresh?: number; minPoints?: number }

/** 用线性回归斜率判方向,用变异系数(CV)判波动。 */
export function classifyTrend(series: number[], opts: ClassifyOpts = {}): Trend {
  const { slopeThresh = 0.1, volatilityThresh = 0.5, minPoints = 3 } = opts
  const s = series.filter((v) => typeof v === 'number' && !Number.isNaN(v))
  if (s.length < minPoints) return 'flat'

  const n = s.length
  const mean = s.reduce((a, b) => a + b, 0) / n

  // 先判断波动性（高频震荡优先检测）
  if (mean === 0) {
    const variance = s.reduce((a, b) => a + (b - mean) ** 2, 0) / n
    if (variance !== 0) return 'volatile'
    return 'flat'
  }
  const std = Math.sqrt(s.reduce((a, b) => a + (b - mean) ** 2, 0) / n)
  const cv = std / Math.abs(mean)
  if (cv >= volatilityThresh) return 'volatile'

  // 波动不显著时，计算斜率判断趋势方向
  const xs = s.map((_, i) => i)
  const xMean = (n - 1) / 2
  let num = 0, den = 0
  for (let i = 0; i < n; i++) { num += (xs[i] - xMean) * (s[i] - mean); den += (xs[i] - xMean) ** 2 }
  const slope = den === 0 ? 0 : num / den
  const normSlope = slope / Math.abs(mean)
  if (normSlope > slopeThresh) return 'up'
  if (normSlope < -slopeThresh) return 'down'

  return 'flat'
}

/** 把数值序列映射到 width×height viewBox 的 "x,y x,y ..." 点串(y 翻转,SVG 向下为正)。 */
export function sparklinePoints(series: number[], width: number, height: number): string {
  const s = series.filter((v) => typeof v === 'number' && !Number.isNaN(v))
  if (s.length === 0) return ''
  const n = s.length
  const min = Math.min(...s), max = Math.max(...s)
  const span = max - min || 1
  const pad = 2
  const usableH = height - pad * 2
  return s
    .map((v, i) => {
      const x = n === 1 ? 0 : (i / (n - 1)) * width
      const y = pad + (1 - (v - min) / span) * usableH
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}
