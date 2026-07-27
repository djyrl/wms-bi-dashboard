import request from '../request'

/** 采购批次库存报表行 */
export interface InventoryReportRow {
  id: number
  purchase_batch: string
  material_name: string
  material_code: string
  project_code: string
  project_name: string
  purchaser_name: string
  inbound_date: string
  inbound_amount: number
  claimed_amount: number
  inventory_amount: number
  claim_rate: number
  age_days: number
}

export interface InventoryReportSummary {
  total_inbound: number
  total_claimed: number
  total_inventory: number
}

/** 报表响应 */
export interface InventoryReportData {
  total: number
  limit: number
  offset: number
  summary: InventoryReportSummary
  rows: InventoryReportRow[]
}

/** 采购批次库存报表 */
export const getInventoryReport = (params: {
  sort_by?: string
  sort_order?: string
  limit?: number
  offset?: number
}) =>
  request.get<InventoryReportData>('/wms/indicators/inventory-report', { params })


// ═══ 项目库存追溯汇总 ═══

/** 项目汇总行 */
export interface ProjectSummaryRow {
  project_name: string
  project_code: string
  inbound_amount: number
  claimed_amount: number
  inventory_amount: number
  claim_rate: number
  avg_age_days: number
}

/** 项目汇总响应 */
export interface ProjectSummaryData {
  total: number
  rows: ProjectSummaryRow[]
}

/** 项目库存追溯汇总表 */
export const getProjectSummary = (params?: {
  sort_by?: string
  sort_order?: string
}) =>
  request.get<ProjectSummaryData>('/wms/indicators/project-summary', { params })


// ═══ 采购人库存追溯汇总 ═══

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

export const getPurchaserSummary = (params?: {
  sort_by?: string
  sort_order?: string
}) =>
  request.get<PurchaserSummaryData>('/wms/indicators/purchaser-summary', { params })


// ═══ 库存来源结构 ═══

export interface SourceStructureRow {
  source_name: string
  inventory_amount: number
  ratio: number
}

export interface SourceStructureData {
  total_amount: number
  rows: SourceStructureRow[]
}

export const getSourceStructure = () =>
  request.get<SourceStructureData>('/wms/indicators/source-structure')
