import request from '../request'
import type {
  KpiSummary,
  ClaimIndicators,
  StructureIndicators,
  TimeIndicators,
  ProcurementBatch,
  ProjectIndicator,
  PurchaserIndicator,
} from '@/types/dashboard'

/** 0. KPI 总览 */
export const getSummary = () => request.get<KpiSummary>('/wms/indicators/summary')

/** I. 采购领用率（当年/全部） */
export const getClaimIndicators = () => request.get<ClaimIndicators>('/wms/indicators/claim')

/** II. 库存结构 */
export const getStructureIndicators = () => request.get<StructureIndicators>('/wms/indicators/structure')

/** III. 库龄指标 */
export const getTimeIndicators = () => request.get<TimeIndicators>('/wms/indicators/time')

/** 库龄分层统计 */
export const getAgeLayers = (params?: { min_amount?: number; min_age?: number; max_age?: number }) =>
  request.get<ProcurementBatch[]>('/wms/indicators/age-layers', { params })

/** IV. 项目维度 */
export const getByProject = () => request.get<ProjectIndicator[]>('/wms/indicators/by-project')

/** V. 采购人维度 */
export const getByPurchaser = () => request.get<PurchaserIndicator[]>('/wms/indicators/by-purchaser')

/** VI. TOP 排行 — 未领用库存（金额） */
export const getTopUnclaimedAmount = (limit = 10) =>
  request.get<ProcurementBatch[]>('/wms/indicators/top/unclaimed-amount', { params: { limit } })

/** 未领用库存 TOP（数量） */
export const getTopUnclaimedQuantity = (limit = 10) =>
  request.get<ProcurementBatch[]>('/wms/indicators/top/unclaimed-quantity', { params: { limit } })

/** 领用 TOP（金额） */
export const getTopClaimedAmount = (limit = 10) =>
  request.get<any[]>('/wms/indicators/top/claimed-amount', { params: { limit } })

/** 领用 TOP（数量） */
export const getTopClaimedQuantity = (limit = 10) =>
  request.get<any[]>('/wms/indicators/top/claimed-quantity', { params: { limit } })

/** 维度值列表 */
export const getDistinctValues = (field: string, projectType?: string) =>
  request.get<string[]>('/wms/indicators/distinct-values', { params: { field, project_type: projectType } })

/** 兼容旧 API：/api/dimensions/{type} — 前端不再使用，保留以防有组件引用 */
export const getDimensions = (type: string) =>
  request.get<string[]>(`/wms/indicators/distinct-values?field=${type === 'materials' ? 'material_code' : type === 'projects' ? 'project_code' : 'purchaser_name'}`)

/** 下钻：批次明细 — 兼容旧 API */
export const drillBatches = (params: {
  project_id?: number; material_id?: number; purchaser_id?: number
  age_min?: number; age_max?: number
}) => request.get<ProcurementBatch[]>('/wms/indicators/age-layers', {
  params: {
    min_age: params.age_min,
    max_age: params.age_max,
  },
})
