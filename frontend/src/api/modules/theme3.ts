import request from '../request'

// ═══ 主题三：时间指标 · 后端返回类型 ═══

/** 库龄结构单项 */
export interface AgeStructureItem {
  range: string
  amount: number
  ratio: number
  count: number
}

/** GET /api/wms/indicators/time 返回 */
export interface TimeIndicatorsRes {
  aged_ratio_1y: number
  aged_amount_1y: number
  age_structure: AgeStructureItem[]
  avg_age_weighted_days: number
}

/** 库龄分层明细单项 */
export interface AgeLayerItem {
  id: number
  material_code: string
  batch_code: string
  inventory_amount: number
  current_quantity: number
  age_days: number
  inbound_date: string
  unit_price: number
  supplier_code: string
}

/** 项目指标单项 */
export interface WmsProjectIndicator {
  project_code: string
  inbound_amount: number
  claimed_amount: number
  unclaimed_amount: number
  claim_rate: number
  avg_age_days: number
  over90_ratio: number
  record_count: number
}

/** 库龄月度趋势单项 */
export interface AgeMonthlyItem {
  month: string
  avg_age: number
  over90_rate: number
}

/** 库龄月度趋势响应 */
export interface AgeMonthlyRes {
  months: string[]
  data: AgeMonthlyItem[]
}

/** 滞留热力图响应 */
export interface AgeHeatmapRes {
  categories: string[]
  age_labels: string[]
  data: number[][]
}

// ═══ API 方法 ═══

/** 时间指标：库龄结构、加权平均库龄、长库龄占比 */
export const getTimeIndicators = () =>
  request.get<TimeIndicatorsRes>('/wms/indicators/time')

/** 库龄分层统计（支持筛选） */
export const getAgeLayers = (params?: { min_amount?: number; min_age?: number; max_age?: number }) =>
  request.get<AgeLayerItem[]>('/wms/indicators/age-layers', { params })

/** 各项目指标（含平均库龄，用于库龄预警） */
export const getByProject = () =>
  request.get<WmsProjectIndicator[]>('/wms/indicators/by-project')

/** 库龄月度趋势（近12个月加权平均库龄 + 超90天占比） */
export const getAgeMonthly = () =>
  request.get<AgeMonthlyRes>('/wms/indicators/age/monthly')

/** 滞留库存热力图（物料类别 × 库龄段交叉矩阵） */
export const getAgeHeatmap = () =>
  request.get<AgeHeatmapRes>('/wms/indicators/age/heatmap')
