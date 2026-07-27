import request from '../request'

// ═══ 类型定义 ═══

/** KPI 总览（复用 /wms/indicators/summary） */
export interface TraceSummary {
  total_inbound_amount: number
  total_claimed_amount: number
  total_inventory_amount: number
  total_inventory_quantity: number
  total_records: number
  aged_amount_1y: number
  aged_ratio_1y: number
  avg_age_weighted_days: number
}

/** 领用指标区间（当年 / 全部） */
export interface TraceClaimRange {
  claim_rate_amount: number
  claim_rate_quantity: number
  unclaimed_amount: number
  unclaimed_amount_ratio: number
  total_inbound_amount: number
  total_claimed_amount: number
  total_inbound_quantity: number
  total_claimed_quantity: number
}

/** 领用指标（复用 /wms/indicators/claim） */
export interface TraceClaim {
  current_year: number
  year_start: string
  year_end: string
  all: TraceClaimRange
  year: TraceClaimRange
}

/** 来源结构 */
export interface SourceStructureRow {
  source_name: string
  inventory_amount: number
  ratio: number
}

export interface SourceStructureData {
  total_amount: number
  rows: SourceStructureRow[]
}

/** 项目指标 */
export interface ProjectIndicator {
  project_code: string
  project_name: string
  inbound_amount: number
  claimed_amount: number
  unclaimed_amount: number
  claim_rate: number
  avg_age_days: number
  over90_ratio?: number
  record_count: number
}

/** 采购人指标 */
export interface PurchaserIndicator {
  purchaser_id: string
  purchaser_name: string
  inbound_amount: number
  claimed_amount: number
  unclaimed_amount: number
  claim_rate: number
  avg_age_days: number
  record_count: number
}

/** 项目汇总表行 */
export interface ProjectSummaryRow {
  project_name: string
  project_code: string
  inbound_amount: number
  claimed_amount: number
  inventory_amount: number
  claim_rate: number
  avg_age_days: number
}

export interface ProjectSummaryData {
  total: number
  rows: ProjectSummaryRow[]
}

/** 采购人汇总表行 */
export interface PurchaserSummaryRow {
  purchaser_name: string
  inbound_amount: number
  claimed_amount: number
  inventory_amount: number
  claim_rate: number
  avg_age_days: number
}

export interface PurchaserSummaryData {
  total: number
  rows: PurchaserSummaryRow[]
}

/** 批次消化进度 */
export interface BatchDigestSeries {
  batch_code: string
  inbound_wan: number
  remain_pct: number
  color: string
  data: number[]
}

export interface BatchDigestData {
  labels: string[]
  series: BatchDigestSeries[]
}

/** 库存结构 */
export interface TraceStructure {
  current_inventory_amount: number
  current_inventory_quantity: number
  project_ratios: {
    project_code: string
    project_name: string
    inventory_amount: number
    ratio: number
  }[]
  purchaser_ratios: {
    purchaser_id: string
    purchaser_name: string
    inventory_amount: number
    ratio: number
  }[]
}

/** 库龄指标 */
export interface TraceTimeIndicators {
  aged_ratio_1y: number
  avg_age_weighted_days: number
  age_structure: {
    range: string
    ratio: number
    amount: number
    count: number
  }[]
}

// ═══ API 方法 ═══

/** KPI 总览 */
export const getTraceSummary = () =>
  request.get<TraceSummary>('/wms/indicators/summary')

/** 领用指标 */
export const getTraceClaim = () =>
  request.get<TraceClaim>('/wms/indicators/claim')

/** 库存结构 */
export const getTraceStructure = () =>
  request.get<TraceStructure>('/wms/indicators/structure')

/** 库龄指标 */
export const getTraceTime = () =>
  request.get<TraceTimeIndicators>('/wms/indicators/time')

/** 来源结构 */
export const getSourceStructure = () =>
  request.get<SourceStructureData>('/wms/indicators/source-structure')

/** 各项目指标 */
export const getByProject = () =>
  request.get<ProjectIndicator[]>('/wms/indicators/by-project')

/** 各采购人指标 */
export const getByPurchaser = () =>
  request.get<PurchaserIndicator[]>('/wms/indicators/by-purchaser')

/** 项目追溯汇总表 */
export const getProjectSummary = (params?: { sort_by?: string; sort_order?: string }) =>
  request.get<ProjectSummaryData>('/wms/indicators/project-summary', { params })

/** 采购人追溯汇总表 */
export const getPurchaserSummary = (params?: { sort_by?: string; sort_order?: string }) =>
  request.get<PurchaserSummaryData>('/wms/indicators/purchaser-summary', { params })

/** 批次消化进度 */
export const getBatchDigest = () =>
  request.get<BatchDigestData>('/wms/indicators/batch/digest')
