// ============================================
// 采购库存 BI Dashboard 类型定义
// ============================================

// ---- 维度 ----
export interface Material {
  id: number; name: string; category: string; unit: string
}
export interface Project {
  id: number; name: string; department: string
}
export interface Purchaser {
  id: number; name: string; department: string
}

// ---- 采购批次 ----
export interface ProcurementBatch {
  id: number; batch_no: string
  material_id: number; project_id: number; purchaser_id: number
  inbound_date: string
  inbound_amount: number; inbound_quantity: number
  claimed_amount: number; claimed_quantity: number
  inventory_amount: number; inventory_quantity: number
  claim_rate_amount: number; claim_rate_quantity: number
  inventory_age_days: number
  material?: Material; project?: Project; purchaser?: Purchaser
}

// ---- Summary KPI ----
export interface KpiSummary {
  total_inbound_amount: number; total_claimed_amount: number
  total_inventory_amount: number; overall_claim_rate: number
  aged_ratio_1y: number; avg_age_weighted_days: number
  batch_count: number; total_inventory_quantity: number
}

// ---- I. 库存领用指标 ----
export interface ClaimIndicators {
  claim_rate_amount: number; claim_rate_quantity: number
  unclaimed_amount: number; unclaimed_quantity: number
  unclaimed_amount_ratio: number
  total_inbound_amount: number; total_claimed_amount: number
}

// ---- II. 库存结构指标 ----
export interface ProjectRatio {
  project_id: number; project_name: string
  inventory_amount: number; ratio: number; batch_count: number
}
export interface PurchaserRatio {
  purchaser_id: number; purchaser_name: string
  inventory_amount: number; ratio: number; batch_count: number
}
export interface StructureIndicators {
  current_inventory_amount: number; current_inventory_quantity: number
  project_ratios: ProjectRatio[]
  purchaser_ratios: PurchaserRatio[]
}

// ---- III. 库存时间指标 ----
export interface AgeStructureItem {
  range: string; amount: number; ratio: number; batch_count: number
}
export interface TimeIndicators {
  aged_ratio_1y: number; aged_amount_1y: number
  age_structure: AgeStructureItem[]
  avg_age_weighted_days: number
}

// ---- IV & V. 维度指标 ----
export interface ProjectIndicator {
  project_id: number; project_name: string; department: string
  inbound_amount: number; claimed_amount: number; unclaimed_amount: number
  claim_rate: number; avg_age_days: number; batch_count: number
}
export interface PurchaserIndicator {
  purchaser_id: number; purchaser_name: string; department: string
  inbound_amount: number; claimed_amount: number; unclaimed_amount: number
  claim_rate: number; avg_age_days: number; batch_count: number
}
