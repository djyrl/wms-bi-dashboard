// ============================================
// 库存分析驾驶舱 类型定义
// ============================================

// ---- 通用 ----
export interface KpiCardData {
  icon: string
  label: string
  value: number
  unit: string
  change: string
  changeType: 'up' | 'down'
  color: string
}

// ---- 主题一：领用指标 ----

export interface UsageRatePoint {
  month: string
  rate: number
  target: number
  trend: number
}

export interface InOutPoint {
  month: string
  inbound: number
  outbound: number
  net: number
}

export interface WaterLevelItem {
  materialCode?: string
  category: string
  current: number
  safeMax: number
  safeMin: number
}

export interface AnomalyDay {
  date: string
  inbound_amount: number
  claimed_amount: number
  type: 0 | 1
  label: string
  huanbi: number | null
}

// ---- 主题二：结构指标 ----

export interface ProjectTreeNode {
  name: string
  projectName: string
  projectCode: string
  value: number
  usageRate: number
}

export interface BuyerRankItem {
  name: string
  value: number
  usageRate: number
}

export interface CategoryBubbleItem {
  name: string
  inventory: number
  usageRate: number
  skuCount: number
}

export interface BatchDigestItem {
  name: string
  color: string
  data: number[]
}

// ---- 主题三：时间指标 ----

export interface AgePyramidItem {
  range: string
  amount: number
  skuCount: number
}

export interface AgeTrendPoint {
  month: string
  avgAge: number
  trend: number
  over90Rate: number
}

export interface SluggishHeatmapCell {
  ageRange: string
  category: string
  value: number
}

export interface AgeGaugeItem {
  project: string
  projectName?: string
  avgAgeDays: number
  over90Rate: number
  /** 未消耗库存金额（元） */
  unclaimedAmount?: number
}

// ---- 主题四：TOP指标 & 行动计划 ----

export interface SluggishItem {
  code: string
  name: string
  age: number
  amount: number
  quantity: number
  unit: string
  project: string
  projectName: string
  buyer: string
  suggest: string
  level: 'red' | 'amber' | 'green'
}

export interface OverstockItem {
  name: string
  current: number
  safeMax: number
}

export interface CleanupItem {
  project: string
  total: number
  cleaned: number
  remain: number
  rate: number
}

export interface OptimizeSuggestItem {
  name: string
  current: number
  dailyUse: number
  maxStock: number
}
