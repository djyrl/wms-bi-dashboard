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

/** 天数 */
export function formatDays(days: number): string {
  if (days >= 365) return `${(days / 365).toFixed(1)}年`
  return `${Math.round(days)}天`
}

/** 领用率颜色 */
export function claimRateColor(rate: number): string {
  if (rate >= 80) return '#10b981'
  if (rate >= 50) return '#f59e0b'
  return '#ef4444'
}
