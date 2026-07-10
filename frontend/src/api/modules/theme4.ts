import request from '../request'

// ═══ 主题四：TOP指标 · 后端返回类型 ═══

/** TOP 未领用库存单项 */
export interface TopUnclaimedItem {
  id: number
  material_code: string
  material_name: string
  batch_code: string
  inventory_amount: number
  current_quantity: number
  age_days: number
  inbound_date: string
  unit_price: number
  unit: string
  owner_project_code: string
  owner_project_name: string
  purchaser_name: string
}

// ═══ API 方法 ═══

/** TOP 未领用库存（按金额排序） */
export const getTopUnclaimedAmount = (limit = 15) =>
  request.get<TopUnclaimedItem[]>('/wms/indicators/top/unclaimed-amount', { params: { limit } })

/** TOP 未领用库存（按数量排序） */
export const getTopUnclaimedQuantity = (limit = 15) =>
  request.get<TopUnclaimedItem[]>('/wms/indicators/top/unclaimed-quantity', { params: { limit } })

/** 优化建议单项 */
export interface OptimizeSuggestApiItem {
  name: string
  current: number
  dailyUse: number
  maxStock: number
}

/** 智能备货优化建议 */
export const getOptimizeSuggest = (limit = 8, safetyDays = 60) =>
  request.get<OptimizeSuggestApiItem[]>('/wms/indicators/optimize-suggest', { params: { limit, safety_days: safetyDays } })
