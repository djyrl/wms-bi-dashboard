import request from '../request'

// ---- 后端 /api/wms/indicators/structure 返回类型 ----

export interface WmsStructure {
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

// ---- 后端 /api/wms/indicators/by-project 返回类型 ----

export interface WmsProjectIndicator {
  project_code: string
  project_name: string
  inbound_amount: number
  claimed_amount: number
  unclaimed_amount: number
  claim_rate: number
  avg_age_days: number
  record_count: number
}

// ---- 后端 /api/wms/indicators/by-purchaser 返回类型 ----

export interface WmsPurchaserIndicator {
  purchaser_id: string
  purchaser_name: string
  inbound_amount: number
  claimed_amount: number
  unclaimed_amount: number
  claim_rate: number
  avg_age_days: number
  record_count: number
}

// ---- 后端 /api/wms/indicators/structure/by-category 返回类型 ----

export interface WmsCategoryItem {
  category_code: string
  category_name: string
  inventory_amount: number
  claim_rate: number
  sku_count: number
  record_count: number
}

// ---- API 请求 ----

/** 库存结构指标（项目占比 + 采购人占比） */
export const getStructure = () => request.get<WmsStructure>('/wms/indicators/structure')

/** 各项目指标 */
export const getByProject = () => request.get<WmsProjectIndicator[]>('/wms/indicators/by-project')

/** 各采购人指标 */
export const getByPurchaser = () => request.get<WmsPurchaserIndicator[]>('/wms/indicators/by-purchaser')

/** 按物资类别统计（气泡图） */
export const getByCategory = () => request.get<{ data: WmsCategoryItem[] }>('/wms/indicators/category/bubble')

// ---- 后端 /api/wms/indicators/batch/digest 返回类型 ----

export interface WmsBatchSeries {
  batch_code: string
  inbound_wan: number
  remain_pct: number
  color: string
  data: number[]
}

export interface WmsBatchDigest {
  labels: string[]
  series: WmsBatchSeries[]
}

/** 批次消化进度 */
export const getBatchDigest = () => request.get<WmsBatchDigest>('/wms/indicators/batch/digest')
