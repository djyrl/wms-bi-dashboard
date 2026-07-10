import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getStructure, getByProject, getByPurchaser, getByCategory, getBatchDigest } from '@/api/modules/theme2'
import type { WmsStructure, WmsProjectIndicator, WmsPurchaserIndicator, WmsCategoryItem, WmsBatchDigest } from '@/api/modules/theme2'
import type {
  ProjectTreeNode,
  BuyerRankItem,
  CategoryBubbleItem,
  BatchDigestItem,
  KpiCardData,
} from '@/types/inventory'

export const useTheme2Store = defineStore('theme2', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ═══ 图表数据 ═══
  const structureProjectTree = ref<ProjectTreeNode[]>([])
  const structureBuyerRank = ref<BuyerRankItem[]>([])
  const structureCategoryBubble = ref<CategoryBubbleItem[]>([])
  const structureBatch = ref<BatchDigestItem[]>([])
  const structureBatchLabels = ref<string[]>([])

  // ═══ 原始 API 返回值 ═══
  const structure = ref<WmsStructure | null>(null)
  const projectIndicators = ref<WmsProjectIndicator[]>([])
  const purchaserIndicators = ref<WmsPurchaserIndicator[]>([])

  // ---- KPI 卡片 ----
  const kpiCards = computed<KpiCardData[]>(() => {
    const s = structure.value
    const projs = projectIndicators.value
    return [
      {
        icon: '🔍',
        label: '库存来源项目数',
        value: projs.length || s?.project_ratios?.length || 0,
        unit: '个',
        change: projs.length > 0 ? `已有数据 ${projs.length} 个项目` : '--',
        changeType: 'down',
        color: '#f59e0b',
      },
      {
        icon: '📦',
        label: '当前库存总额',
        value: s?.current_inventory_amount ? Math.round(s.current_inventory_amount) : 0,
        unit: '万',
        change: s ? `${s.current_inventory_quantity?.toLocaleString?.() || 0} 项库存` : '--',
        changeType: 'down',
        color: '#f59e0b',
      },
      {
        icon: '👤',
        label: '涉及采购人数',
        value: s?.purchaser_ratios?.length || 0,
        unit: '人',
        change: s?.purchaser_ratios?.length
          ? `最大占比 ${s.purchaser_ratios.reduce((max, p) => p.ratio > max.ratio ? p : max).purchaser_name}`
          : '--',
        changeType: 'down',
        color: '#f59e0b',
      },
      {
        icon: '📊',
        label: '项目平均库存金额',
        value: (() => {
          const validProjects = (s?.project_ratios || []).filter(p => p.project_code && p.project_code !== '')
          return validProjects.length
            ? Math.round(s!.current_inventory_amount / validProjects.length)
            : 0
        })(),
        unit: '万',
        change: (() => {
          const validProjects = (s?.project_ratios || []).filter(p => p.project_code && p.project_code !== '')
          return validProjects.length ? `共 ${validProjects.length} 个项目` : '--'
        })(),
        changeType: 'down',
        color: '#f59e0b',
      },
    ]
  })

  // ---- 将 API 数据转为图表格式 ----
  function buildChartData(s: WmsStructure, projs: WmsProjectIndicator[], purchasers: WmsPurchaserIndicator[], categories: WmsCategoryItem[], batchDigest: WmsBatchDigest | null) {
    // 项目树图
    structureProjectTree.value = (s.project_ratios || []).map(p => {
      const pi = projs.find(x => x.project_code === p.project_code)
      return {
        name: p.project_code || '(未关联)',
        projectName: p.project_name || p.project_code || '(未关联)',
        value: p.inventory_amount,
        usageRate: pi?.claim_rate ?? 0,
      }
    })

    // 采购人排行 — 优先使用 by-purchaser 接口（包含领用率），其次用 structure 中的 purchaser_ratios
    if (purchasers.length > 0) {
      structureBuyerRank.value = purchasers.map(p => ({
        name: p.purchaser_name || '(未知)',
        value: p.unclaimed_amount,
        usageRate: p.claim_rate ?? 0,
      }))
    } else if ((s.purchaser_ratios || []).length > 0) {
      structureBuyerRank.value = s.purchaser_ratios.map(p => ({
        name: p.purchaser_name || '(未知)',
        value: p.inventory_amount,
        usageRate: 0,
      }))
    } else {
      structureBuyerRank.value = []
    }

    // 物料类别气泡 — 使用 by-category 接口按物资类别（matkl/wgbez）统计
    structureCategoryBubble.value = categories.map(c => ({
      name: c.category_name || c.category_code || '未知',
      inventory: c.inventory_amount,
      usageRate: c.claim_rate,
      skuCount: c.sku_count,
    }))

    // 批次消化进度 — 按 batch_code 取 TOP 6，模拟逐月消化
    if (batchDigest && batchDigest.series.length > 0) {
      structureBatchLabels.value = batchDigest.labels
      structureBatch.value = batchDigest.series.map(s => ({
        name: s.batch_code,
        color: s.color,
        data: s.data,
      }))
    } else {
      structureBatchLabels.value = []
      structureBatch.value = []
    }
  }

  // ---- 加载全部数据 ----
  async function loadAllData() {
    loading.value = true
    error.value = null
    try {
      const [s, projs, purchasers, catRes, batchDigest] = await Promise.all([
        getStructure(),
        getByProject(),
        getByPurchaser(),
        getByCategory(),
        getBatchDigest(),
      ])
      structure.value = s
      projectIndicators.value = projs
      purchaserIndicators.value = purchasers
      buildChartData(s, projs, purchasers, catRes.data || [], batchDigest)
    } catch (e) {
      console.error('主题二数据加载失败:', e)
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    kpiCards,
    structureProjectTree,
    structureBuyerRank,
    structureCategoryBubble,
    structureBatch,
    structureBatchLabels,
    structure,
    projectIndicators,
    loadAllData,
  }
})
