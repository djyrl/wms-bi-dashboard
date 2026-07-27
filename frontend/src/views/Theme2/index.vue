<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getStructure, getByProject, getByPurchaser, getByCategory, getBatchDigest } from '@/api/modules/theme2'
import type { WmsStructure, WmsProjectIndicator, WmsPurchaserIndicator, WmsCategoryItem, WmsBatchDigest } from '@/api/modules/theme2'
import type { ProjectTreeNode, BuyerRankItem, CategoryBubbleItem, BatchDigestItem, KpiCardData } from '@/types/inventory'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import ProjectTreemap from '@/components/inventory/structure/ProjectTreemap.vue'
import BuyerRanking from '@/components/inventory/structure/BuyerRanking.vue'
import CategoryBubble from '@/components/inventory/structure/CategoryBubble.vue'
import BatchProgress from '@/components/inventory/structure/BatchProgress.vue'

const loading = ref(false)
const error = ref<string | null>(null)

const structureProjectTree = ref<ProjectTreeNode[]>([])
const structureBuyerRank = ref<BuyerRankItem[]>([])
const structureCategoryBubble = ref<CategoryBubbleItem[]>([])
const structureBatch = ref<BatchDigestItem[]>([])
const structureBatchLabels = ref<string[]>([])

const structure = ref<WmsStructure | null>(null)
const projectIndicators = ref<WmsProjectIndicator[]>([])
const purchaserIndicators = ref<WmsPurchaserIndicator[]>([])

const kpiCards = computed<KpiCardData[]>(() => {
  const s = structure.value
  const projs = projectIndicators.value
  const validProjs = (projs || []).filter(p => p.project_code && p.project_name !== '非项目物资')
  const validRatios = (s?.project_ratios || []).filter(p => p.project_code && p.project_name !== '非项目物资')
  return [
    {
      icon: '🔍',
      label: '库存来源项目数',
      value: validRatios.length,
      unit: '个',
      change: validRatios.length > 0 ? `有效库存项目 ${validRatios.length} 个` : '--',
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
      icon: '📊',
      label: '项目平均库存金额',
      value: (() => {
        return validRatios.length
          ? Math.round(s!.current_inventory_amount / validRatios.length)
          : 0
      })(),
      unit: '万',
      change: (() => {
        return validRatios.length ? `共 ${validRatios.length} 个项目` : '--'
      })(),
      changeType: 'down',
      color: '#f59e0b',
    },
  ]
})

function buildChartData(
  s: WmsStructure,
  projs: WmsProjectIndicator[],
  purchasers: WmsPurchaserIndicator[],
  categories: WmsCategoryItem[],
  batchDigest: WmsBatchDigest | null,
) {
  structureProjectTree.value = (s.project_ratios || [])
    .filter(p => p.project_name !== '非项目物资')
    .map(p => {
      const pi = projs.find(x => x.project_code === p.project_code)
      return {
        name: p.project_name || p.project_code || '(未关联)',
        projectName: p.project_name || p.project_code || '(未关联)',
        projectCode: p.project_code || '',
        value: p.inventory_amount / 10000,
        usageRate: pi?.claim_rate ?? 0,
      }
    })

  if (purchasers.length > 0) {
    structureBuyerRank.value = purchasers.map(p => ({
      name: p.purchaser_name || '(未知)',
      value: p.unclaimed_amount / 10000,
      usageRate: p.claim_rate ?? 0,
    }))
  } else if ((s.purchaser_ratios || []).length > 0) {
    structureBuyerRank.value = s.purchaser_ratios.map(p => ({
      name: p.purchaser_name || '(未知)',
      value: p.inventory_amount / 10000,
      usageRate: 0,
    }))
  } else {
    structureBuyerRank.value = []
  }

  structureCategoryBubble.value = categories.map(c => ({
    name: c.category_name || c.category_code || '未知',
    inventory: c.inventory_amount,
    usageRate: c.claim_rate,
    skuCount: c.sku_count,
  }))

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

async function loadAllData() {
  loading.value = true
  error.value = null

  const errs: string[] = []
  let s: WmsStructure | null = null
  let projs: WmsProjectIndicator[] = []
  let purchasers: WmsPurchaserIndicator[] = []
  let categories: WmsCategoryItem[] = []
  let batchDigest: WmsBatchDigest | null = null

  try { s = await getStructure() } catch (e: any) { errs.push('库存结构: ' + (e?.message || '失败')) }
  try { projs = await getByProject() } catch (e: any) { errs.push('项目分析: ' + (e?.message || '失败')) }
  try { purchasers = await getByPurchaser() } catch (e: any) { errs.push('采购人: ' + (e?.message || '失败')) }
  try { const r = await getByCategory(); categories = r.data || [] } catch (e: any) { errs.push('类别: ' + (e?.message || '失败')) }
  try { batchDigest = await getBatchDigest() } catch (e: any) { errs.push('批次: ' + (e?.message || '失败')) }

  if (s) {
    structure.value = s
    projectIndicators.value = projs
    purchaserIndicators.value = purchasers
    buildChartData(s, projs, purchasers, categories, batchDigest)
  }

  if (errs.length > 0) {
    error.value = errs.join('；')
  }
  loading.value = false
}

const projectTreemapRef = ref<InstanceType<typeof ProjectTreemap>>()

function handleRefreshTreemap() {
  projectTreemapRef.value?.refresh()
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载项目分析数据..." class="theme2-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══════════ 主题二：结构指标 ═══════════ 
      <SectionHeader :num="2" title="结构指标 · 定位库存来源" desc="按项目/采购人/类别逐层下钻，找到库存形成的关键来源" color="#f59e0b" />
-->
      <div class="chart-grid">
        <ChartCard title="🌳 按项目维度 · 库存金额分布">
          <template #actions>
            <el-button size="small" text @click="handleRefreshTreemap">🔄 刷新</el-button>
            <span class="card-subtitle">矩形面积=库存金额，颜色=领用率</span>
          </template>
          <ProjectTreemap ref="projectTreemapRef" :data="structureProjectTree" />
        </ChartCard>
        <ChartCard title="👤 按采购负责人 · 库存贡献排行">
          <template #actions>
            <span class="card-subtitle">定位高库存的责任主体</span>
          </template>
          <BuyerRanking :data="structureBuyerRank" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="🏷 按物料类别 · 库存金额与领用率">
          <template #actions>
            <span class="card-subtitle">气泡大小=库存金额，颜色=领用率</span>
          </template>
          <CategoryBubble :data="structureCategoryBubble" />
        </ChartCard>
        <ChartCard title="📦 按入库批次 · 库存消化进度">
          <template #actions>
            <span class="card-subtitle">批次入库后逐月剩余库存占比</span>
          </template>
          <BatchProgress :data="structureBatch" :labels="structureBatchLabels" />
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme2-dashboard {
  padding: 0 0 24px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 4px;

  > .el-card {
    display: flex;
    flex-direction: column;

    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
  }
}

.card-subtitle {
  font-size: 10px;
  color: #94a3b8;
}

@media (max-width: 1024px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
