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
}

export const getInventoryReport = (params?: ReportParams) =>
  request.get<InventoryReportRes>('/wms/indicators/inventory-report', { params })
