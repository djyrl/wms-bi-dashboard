<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
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

const router = useRouter()
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
      icon: '🔍', label: '库存来源项目数',
      value: validRatios.length, unit: '个',
      change: validRatios.length > 0 ? `有效库存项目 ${validRatios.length} 个` : '--', changeType: 'down', color: '#f59e0b',
    },
    {
      icon: '🏗️', label: '库存最高项目',
      value: validRatios[0] ? validRatios[0].inventory_amount / 10000 : 0, unit: '万',
      change: (validRatios[0]?.project_name && validRatios[0].project_name !== validRatios[0].project_code)
        ? validRatios[0].project_name : validRatios[0]?.project_code || '--', changeType: 'down', color: '#f59e0b',
    },
    {
      icon: '📊', label: '项目平均库存金额',
      value: validRatios.length ? s!.current_inventory_amount / validRatios.length : 0, unit: '万',
      change: validRatios.length ? `共 ${validRatios.length} 个项目` : '--', changeType: 'down', color: '#f59e0b',
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
    structureBuyerRank.value = purchasers.map(p => ({ name: p.purchaser_name || '(未知)', value: p.unclaimed_amount / 10000, usageRate: p.claim_rate ?? 0 }))
  } else if ((s.purchaser_ratios || []).length > 0) {
    structureBuyerRank.value = s.purchaser_ratios.map(p => ({ name: p.purchaser_name || '(未知)', value: p.inventory_amount / 10000, usageRate: 0 }))
  } else {
    structureBuyerRank.value = []
  }

  structureCategoryBubble.value = categories.map(c => ({ name: c.category_name || c.category_code || '未知', inventory: c.inventory_amount, usageRate: c.claim_rate, skuCount: c.sku_count }))

  if (batchDigest && batchDigest.series.length > 0) {
    structureBatchLabels.value = batchDigest.labels
    structureBatch.value = batchDigest.series.map(s => ({ name: s.batch_code, color: s.color, data: s.data }))
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
  if (errs.length > 0) error.value = errs.join('；')
  loading.value = false
}

const treemapRef = ref()
onMounted(() => loadAllData())
</script>

<template>
  <div v-loading="loading" class="page">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />
    <template v-if="!error">
      <el-button circle class="back-float" @click="router.push('/')" title="返回上级页面">←</el-button>
      <!-- <h2>🏗👤📊 责任归属 · 剩的是谁的 → 谁的问题最大</h2> -->
      <KpiCards :cards="kpiCards" />
      <div class="grid">
        <ChartCard title="🌳 项目库存金额分布"><template #actions><el-button size="small" text @click="treemapRef?.refresh()">🔄 刷新</el-button><span class="sub">面积=金额，颜色=领用率</span></template><ProjectTreemap ref="treemapRef" :data="structureProjectTree" /></ChartCard>
        <ChartCard title="👤 采购人库存排行"><template #actions><span class="sub">定位高库存责任主体</span></template><BuyerRanking :data="structureBuyerRank" /></ChartCard>
      </div>
      <div class="grid">
        <ChartCard title="🏷 物料类别气泡图"><template #actions><span class="sub">气泡=金额，颜色=领用率</span></template><CategoryBubble :data="structureCategoryBubble" /></ChartCard>
        <ChartCard title="📦 批次消化进度"><template #actions><span class="sub">入库后逐月剩余库存占比</span></template><BatchProgress :data="structureBatch" :labels="structureBatchLabels" /></ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0 0 24px; }
h2 { font-size: 20px; margin-bottom: 16px; }
.back-float { position: fixed; top: 12px; left: 12px; z-index: 200; width: 26px; height: 26px; min-width: 26px; padding: 0; border: 1px solid #e2e8f0; background: rgba(255,255,255,0.88); backdrop-filter: blur(6px); box-shadow: 0 1px 4px rgba(0,0,0,0.06); font-size: 13px; color: #94a3b8; }
.back-float:hover { color: #3b82f6; border-color: #3b82f6; background: #fff; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 4px; }
.sub { font-size: 10px; color: #94a3b8; }
@media (max-width: 1024px) { .grid { grid-template-columns: 1fr; } }
</style>
