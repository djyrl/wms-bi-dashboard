/** 金额格式化（万元） */
export function formatAmount(value: number): string {
  if (Math.abs(value) >= 100_000_000) return `${(value / 100_000_000).toFixed(2)}亿`
  if (Math.abs(value) >= 10_000) return `${(value / 10_000).toFixed(0)}万`
  return `¥${value.toLocaleString('zh-CN')}`
}

/** 千分位数字 */
export function formatNumber(value: number): string {
  return Math.round(value).toLocaleString('zh-CN')
}

/** 百分比 */
export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

/** 天数 → X年X月X天（自然月30天） */
export function formatDays(days: number): string {
  if (days == null || isNaN(days)) return '-'
  const d = Math.round(days)
  if (d >= 365) {
    const y = Math.floor(d / 365)
    const r = d % 365
    const m = Math.floor(r / 30)
    const rd = r % 30
    if (m > 0 && rd > 0) return `${y}年${m}月${rd}天`
    if (m > 0) return `${y}年${m}月`
    return `${y}年`
  }
  if (d >= 30) {
    const m = Math.floor(d / 30)
    const rd = d % 30
    return rd > 0 ? `${m}月${rd}天` : `${m}月`
  }
  return `${d}天`
}

/** 领用率颜色 */
export function claimRateColor(rate: number): string {
  if (rate >= 80) return '#10b981'
  if (rate >= 50) return '#f59e0b'
  return '#ef4444'
}
