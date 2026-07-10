import request from '../request'

// ═══ KPI 考核清单 后端返回类型 ═══

export interface SummaryInfo {
  update_time: string
  total_inbound_wan: number
  total_claimed_wan: number
  current_inventory_wan: number
  overall_claim_rate: number
  aged_ratio_1y: number
  ok_count: number
  warning_count: number
  alert_count: number
}

export interface KpiItem {
  key: string
  name: string
  formula?: string
  value: number
  unit: string
  target: string
  target_value?: number | null
  direction: 'up' | 'down'
  status: 'ok' | 'warning' | 'alert' | 'info'
  detail?: Record<string, any>
}

export interface K8ProjectItem {
  project_code: string
  project_name: string
  claim_rate: number
  inventory_amount_wan: number
  avg_age_days: number
  over90_ratio: number
}

export interface K9PurchaserItem {
  purchaser_name: string
  claim_rate: number
  unclaimed_amount_wan: number
  avg_age_days: number
}

export interface ProjectRatioItem {
  project_code: string
  project_name: string
  inventory_amount_wan: number
  ratio: number
}

export interface PurchaserRatioItem {
  purchaser_name: string
  inventory_amount_wan: number
  ratio: number
}

export interface AgeStructureItem {
  range: string
  amount: number
  ratio: number
  count: number
}

export interface K5ProjectItem {
  project_code: string
  project_name: string
  unclaimed_amount_wan: number
  claim_rate: number
  avg_age_days: number
}

export interface TopUnclaimedItem {
  rank: number
  material_code: string
  material_name: string
  inventory_amount_wan: number
  current_quantity: number
  unit: string
  age_days: number
  owner_project_code: string
  owner_project_name: string
  purchaser_name: string
}

export interface TopClaimedAmountItem {
  rank: number
  material_code: string
  claimed_amount_wan: number
  inbound_amount_wan: number
  inbound_date: string
}

export interface TopClaimedQuantityItem {
  rank: number
  material_code: string
  claimed_quantity: number
  inbound_quantity: number
  inbound_date: string
}

export interface K6Structure {
  project_ratios: ProjectRatioItem[]
  purchaser_ratios: PurchaserRatioItem[]
}

export interface K7Time {
  avg_age_weighted_days: number
  unused_days: number
  age_structure: AgeStructureItem[]
  aged_ratio_1y: number
}

export interface K8Project {
  description: string
  items: K8ProjectItem[]
}

export interface K9Purchaser {
  description: string
  items: K9PurchaserItem[]
}

export interface T1Top {
  key: string
  name: string
  description: string
  is_kpi: boolean
  items: TopUnclaimedItem[]
}

export interface T2Top {
  key: string
  name: string
  description: string
  is_kpi: boolean
  by_amount: TopClaimedAmountItem[]
  by_quantity: TopClaimedQuantityItem[]
}

export interface KpiChecklistRes {
  summary: SummaryInfo
  core_kpis: {
    K1: KpiItem
    K2: KpiItem
    K3: KpiItem
  }
  constraint_kpis: {
    K4: KpiItem
    K5: KpiItem & { detail: { projects: K5ProjectItem[]; total_count: number } }
  }
  structure_kpis: {
    K6: { key: string; name: string; description: string } & K6Structure
    K7: { key: string; name: string; description: string } & K7Time
    K8: { key: string; name: string } & K8Project
    K9: { key: string; name: string } & K9Purchaser
  }
  top_kpis: {
    T1: T1Top
    T2: T2Top
  }
}

// ═══ API 方法 ═══

/** 获取 KPI 考核清单完整数据 */
export const getKpiChecklist = () =>
  request.get<KpiChecklistRes>('/wms/indicators/kpi-checklist')
