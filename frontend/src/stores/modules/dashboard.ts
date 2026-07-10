import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  KpiSummary, ClaimIndicators, StructureIndicators, TimeIndicators,
  ProjectIndicator, PurchaserIndicator, ProcurementBatch,
} from '@/types/dashboard'
import {
  getSummary, getClaimIndicators, getStructureIndicators, getTimeIndicators,
  getByProject, getByPurchaser,
  getTopUnclaimedAmount, getTopUnclaimedQuantity, getTopClaimedAmount, getTopClaimedQuantity,
  drillBatches,
} from '@/api/modules/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  // ---- State ----
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Overview
  const summary = ref<KpiSummary | null>(null)

  // I. 库存领用
  const claim = ref<ClaimIndicators | null>(null)

  // II. 库存结构
  const structure = ref<StructureIndicators | null>(null)

  // III. 库存时间
  const time = ref<TimeIndicators | null>(null)

  // IV & V. 维度指标
  const projectIndicators = ref<ProjectIndicator[]>([])
  const purchaserIndicators = ref<PurchaserIndicator[]>([])

  // VI. TOP 排行
  const topUnclaimedAmount = ref<ProcurementBatch[]>([])
  const topUnclaimedQuantity = ref<ProcurementBatch[]>([])
  const topClaimedAmount = ref<ProcurementBatch[]>([])
  const topClaimedQuantity = ref<ProcurementBatch[]>([])

  // 当前 TOP 标签页
  const topTab = ref<'unclaimed-amount' | 'unclaimed-quantity' | 'claimed-amount' | 'claimed-quantity'>('unclaimed-amount')

  // ---- Actions ----
  async function loadAllData() {
    loading.value = true
    error.value = null
    try {
      const [s, c, st, t, pj, pr, ua, uq, ca, cq] = await Promise.all([
        getSummary(), getClaimIndicators(), getStructureIndicators(), getTimeIndicators(),
        getByProject(), getByPurchaser(),
        getTopUnclaimedAmount(10), getTopUnclaimedQuantity(10),
        getTopClaimedAmount(10), getTopClaimedQuantity(10),
      ])
      summary.value = s; claim.value = c; structure.value = st; time.value = t
      projectIndicators.value = pj; purchaserIndicators.value = pr
      topUnclaimedAmount.value = ua; topUnclaimedQuantity.value = uq
      topClaimedAmount.value = ca; topClaimedQuantity.value = cq
    } catch (e) {
      console.error('数据加载失败:', e)
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  function switchTopTab(tab: typeof topTab.value) {
    topTab.value = tab
  }

  // ---- 下钻（独立调用，不存入全局状态） ----
  async function fetchDrillBatches(params: {
    project_id?: number; material_id?: number; purchaser_id?: number
    age_min?: number; age_max?: number
  }) {
    return drillBatches(params)
  }

  return {
    loading, error,
    summary, claim, structure, time,
    projectIndicators, purchaserIndicators,
    topUnclaimedAmount, topUnclaimedQuantity, topClaimedAmount, topClaimedQuantity,
    topTab,
    loadAllData, switchTopTab, fetchDrillBatches,
  }
})
