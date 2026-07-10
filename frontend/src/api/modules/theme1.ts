import request from '../request'

// ---- 主题一接口返回的原始类型 ----

export interface ClaimMonthlyItem {
  month: string
  inbound_amount: number
  claimed_amount: number
  net_amount: number
  claim_rate: number
}
export interface ClaimMonthlyRes {
  months: string[]
  data: ClaimMonthlyItem[]
}

export interface ClaimDailyItem {
  day: string
  inbound_amount: number
  claimed_amount: number
  net_amount: number
  claim_rate: number
}
export interface ClaimDailyRes {
  days: string[]
  data: ClaimDailyItem[]
}

export interface CategoryItem {
  material_code: string
  category: string
  current: number
  safe_max: number
  safe_min: number
  record_count: number
}
export interface CategoryRes {
  data: CategoryItem[]
}

export interface ClaimWeeklyItem {
  week: string
  inbound_amount: number
  claimed_amount: number
  net_amount: number
  claim_rate: number
}
export interface ClaimWeeklyRes {
  weeks: string[]
  data: ClaimWeeklyItem[]
}

export interface AnomalyDailyItem {
  date: string
  inbound_amount: number
  claimed_amount: number
  type: 0 | 1
  label: string
}
export interface AnomalyDailyRes {
  data: AnomalyDailyItem[]
}

export interface WmsSummary {
  total_inbound_amount: number
  total_claimed_amount: number
  total_inventory_amount: number
  total_inventory_quantity: number
  total_records: number
  aged_amount_1y: number
  aged_ratio_1y: number
  avg_age_weighted_days: number
}

export interface WmsClaim {
  claim_rate_amount: number
  claim_rate_quantity: number
  unclaimed_amount: number
  unclaimed_amount_ratio: number
  total_inbound_amount: number
  total_claimed_amount: number
}

// ---- API 方法 ----

/** 月度入库/领用/领用率（最近12个月） */
export const getClaimMonthly = () =>
  request.get<ClaimMonthlyRes>('/wms/indicators/claim/monthly')

/** 按天入库/领用/领用率（当月） */
export const getClaimDaily = () =>
  request.get<ClaimDailyRes>('/wms/indicators/claim/daily')

/** 按周入库/领用/领用率（最近12周） */
export const getClaimWeekly = () =>
  request.get<ClaimWeeklyRes>('/wms/indicators/claim/weekly')

/** 按物料类别统计库存（含安全线） */
export const getStructureByCategory = () =>
  request.get<CategoryRes>('/wms/indicators/structure/by-category')

/** 近N天逐日异常检测 */
export const getAnomalyDaily = (days = 30) =>
  request.get<AnomalyDailyRes>('/wms/indicators/anomaly/daily', { params: { days } })

/** KPI 总览（人大金仓） */
export const getWmsSummary = () =>
  request.get<WmsSummary>('/wms/indicators/summary')

/** 领用指标汇总 */
export const getWmsClaim = () =>
  request.get<WmsClaim>('/wms/indicators/claim')
