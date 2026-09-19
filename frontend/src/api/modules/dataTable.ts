import request from '../request'

export interface InventoryRow {
  id: string; purchase_batch: string; material_name: string; material_code: string
  project_code: string; project_name: string; purchaser_name: string; project_type: string
  inbound_date: string; putaway_date: string; batch_code: string
  original_quantity: number; current_quantity: number
  used_quantity: number; pick_quantity: number; repair_quantity: number
  scrap_quantity: number; repaired_quantity: number
  unit_price: number; unit: string; supplier_code: string
  inbound_amount: number; claimed_amount: number; inventory_amount: number
  claim_rate: number; age_days: number
}

export interface InventoryReportRes {
  total: number; limit: number; offset: number
  summary: { total_inbound: number; total_claimed: number; total_inventory: number }
  rows: InventoryRow[]
}

export interface ReportParams {
  sort_by?: string; sort_order?: string; limit?: number; offset?: number
  /** 列筛选：键为后端白名单列名（FILTERABLE_COLUMNS），值为子串匹配文本 */
  [key: string]: string | number | undefined
}

export const getInventoryReport = (params?: ReportParams) =>
  request.get<InventoryReportRes>('/wms/indicators/inventory-report', { params })

// ================================================================
// 明细宽表（WMS × ERP 批次级联）—— 对应后端 data_wide.py
// ================================================================

export interface InventoryWideRow {
  // WMS 标识 / 维度
  id: string; purchase_batch: string; material_name: string; material_code: string
  material_group_code: string
  project_code: string; project_name: string; project_type: string
  owner_project_type: string
  purchaser_name: string; submitter_name: string; contact_name: string
  inbound_date: string; putaway_date: string; batch_code: string
  // 数量
  original_quantity: number; current_quantity: number
  used_quantity: number; pick_quantity: number; repair_quantity: number
  scrap_quantity: number; repaired_quantity: number
  // 单价 / 单位 / 供应商
  unit_price: number; unit: string; supplier_code: string
  // WMS 金额（项目分摊后）+ 分摊因子
  inbound_amount: number; claimed_amount: number; inventory_amount: number
  project_ratio: number
  // 领用率 / 库龄
  claim_rate: number; age_days: number
  // ERP 金额（批次级，元）
  erp_recv_all: number; erp_reversal_all: number; erp_net_in_all: number; erp_out_all: number
  erp_recv_year: number; erp_reversal_year: number; erp_net_in_year: number; erp_out_year: number
  // 最佳估计库存
  best_inventory_amt: number
}

export interface InventoryWideSummary {
  total_inbound: number; total_claimed: number; total_inventory: number
  erp_recv_all: number; erp_reversal_all: number; erp_net_in_all: number; erp_out_all: number
  erp_recv_year: number; erp_reversal_year: number; erp_net_in_year: number; erp_out_year: number
  best_inventory_total: number
}

export interface InventoryWideReportRes {
  total: number; limit: number; offset: number; current_year: number
  summary: InventoryWideSummary
  rows: InventoryWideRow[]
}

export interface WideReportParams {
  sort_by?: string; sort_order?: string; limit?: number; offset?: number; year?: number
}

export const getInventoryWideReport = (params?: WideReportParams) =>
  request.get<InventoryWideReportRes>('/wms/indicators/inventory-wide-report', { params })
