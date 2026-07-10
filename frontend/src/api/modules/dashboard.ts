import request from '../request'
import type {
  KpiSummary,
  ClaimIndicators,
  StructureIndicators,
  TimeIndicators,
  ProcurementBatch,
  ProjectIndicator,
  PurchaserIndicator,
  Material,
  Project,
  Purchaser,
} from '@/types/dashboard'

/** Overview */
export const getSummary = () => request.get<KpiSummary>('/summary')

/** I. 库存领用 */
export const getClaimIndicators = () => request.get<ClaimIndicators>('/indicators/claim')

/** II. 库存结构 */
export const getStructureIndicators = () => request.get<StructureIndicators>('/indicators/structure')

/** III. 库存时间 */
export const getTimeIndicators = () => request.get<TimeIndicators>('/indicators/time')

export const getAgeLayers = (minAmount = 0, minAge = 0, maxAge?: number) =>
  request.get<ProcurementBatch[]>('/indicators/age-layers', {
    params: { min_amount: minAmount, min_age: minAge, max_age: maxAge },
  })

/** IV. 项目维度 */
export const getByProject = () => request.get<ProjectIndicator[]>('/indicators/by-project')

/** V. 采购人维度 */
export const getByPurchaser = () => request.get<PurchaserIndicator[]>('/indicators/by-purchaser')

/** VI. TOP 排行 */
export const getTopUnclaimedAmount = (limit = 10) =>
  request.get<ProcurementBatch[]>('/top/unclaimed-amount', { params: { limit } })

export const getTopUnclaimedQuantity = (limit = 10) =>
  request.get<ProcurementBatch[]>('/top/unclaimed-quantity', { params: { limit } })

export const getTopClaimedAmount = (limit = 10) =>
  request.get<ProcurementBatch[]>('/top/claimed-amount', { params: { limit } })

export const getTopClaimedQuantity = (limit = 10) =>
  request.get<ProcurementBatch[]>('/top/claimed-quantity', { params: { limit } })

/** 维度列表 */
export const getDimensions = (type: 'materials' | 'projects' | 'purchasers') =>
  request.get<(Material | Project | Purchaser)[]>(`/dimensions/${type}`)

/** 下钻：批次明细 */
export const drillBatches = (params: {
  project_id?: number; material_id?: number; purchaser_id?: number
  age_min?: number; age_max?: number
}) => request.get<ProcurementBatch[]>('/drill/batches', { params })
