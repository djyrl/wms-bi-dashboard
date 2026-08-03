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

export interface ClaimYearlyItem {
  year: string
  inbound_amount: number
  claimed_amount: number
  net_amount: number
  claim_rate: number
}
export interface ClaimYearlyRes {
  years: string[]
  data: ClaimYearlyItem[]
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

export interface WmsClaimRange {
  claim_rate_amount: number
  claim_rate_quantity: number
  unclaimed_amount: number
  unclaimed_amount_ratio: number
  total_inbound_amount: number
  total_claimed_amount: number
  total_inbound_quantity: number
  total_claimed_quantity: number
}

export interface WmsClaimSplit {
  current_year: number
  year_start: string
  year_end: string
  all: WmsClaimRange
  year: WmsClaimRange
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

/** 按年入库/领用/领用率（全部年份） */
export const getClaimYearly = () =>
  request.get<ClaimYearlyRes>('/wms/indicators/claim/yearly')

/** 按物料类别统计库存（含安全线） */
export const getStructureByCategory = () =>
  request.get<CategoryRes>('/wms/indicators/structure/by-category')

/** 近N天逐日异常检测 */
export const getAnomalyDaily = (days = 30) =>
  request.get<AnomalyDailyRes>('/wms/indicators/anomaly/daily', { params: { days } })

/** KPI 总览（人大金仓） */
export const getWmsSummary = () =>
  request.get<WmsSummary>('/wms/indicators/summary')

/** 领用指标汇总（当年/全部拆分） */
export const getWmsClaim = () =>
  request.get<WmsClaimSplit>('/wms/indicators/claim')

// ---- ERP 领用率（erp_catalog_mb51）----

export interface ErpClaimRange {
  total_inbound_amount: number
  total_outbound_amount: number
  total_inbound_quantity: number
  total_outbound_quantity: number
  claim_rate_amount: number
  claim_rate_quantity: number
  unclaimed_amount: number
  unclaimed_amount_ratio: number
}

export interface ErpClaimSplit {
  current_year: number
  year_start: string
  year_end: string
  all: ErpClaimRange
  year: ErpClaimRange
  note: string
}

export interface ErpClaimMonthlyRow {
  doc_month: string
  inbound: number
  outbound: number
  claim_rate: number
  move_cnt: number
}

export interface ErpClaimMonthlyRes {
  rows: ErpClaimMonthlyRow[]
}

/** ERP 版领用指标汇总 */
export const getErpClaim = () =>
  request.get<ErpClaimSplit>('/wms/indicators/erp-claim')

/** ERP 版月度领用率 */
export const getErpClaimMonthly = (year?: number) =>
  request.get<ErpClaimMonthlyRes>('/wms/indicators/erp-claim-monthly', { params: { year } })
