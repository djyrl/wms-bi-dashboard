<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import {
  getTraceSummary,
  getTraceClaim,
  getTraceStructure,
  getTraceTime,
  getSourceStructure,
  getByProject,
  getByPurchaser,
  getProjectSummary,
  getPurchaserSummary,
  getBatchDigest,
} from '@/api/modules/traceability'
import type {
  TraceSummary,
  TraceClaim,
  TraceStructure,
  TraceTimeIndicators,
  SourceStructureData,
  ProjectIndicator,
  PurchaserIndicator,
  ProjectSummaryData,
  PurchaserSummaryData,
  BatchDigestData,
} from '@/api/modules/traceability'
import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'

const loading = ref(false)
const error = ref<string | null>(null)

// ═══ 核心指标 ═══
const summary = ref<TraceSummary | null>(null)
const claim = ref<TraceClaim | null>(null)
const structure = ref<TraceStructure | null>(null)
const timeIndicators = ref<TraceTimeIndicators | null>(null)

// ═══ 追溯数据 ═══
const sourceStructure = ref<SourceStructureData | null>(null)
const projectIndicators = ref<ProjectIndicator[]>([])
const purchaserIndicators = ref<PurchaserIndicator[]>([])
const projectSummary = ref<ProjectSummaryData | null>(null)
const purchaserSummary = ref<PurchaserSummaryData | null>(null)
const batchDigest = ref<BatchDigestData | null>(null)

// ═══ 排序状态 ═══
const projectSortBy = ref('inventory_amount')
const projectSortOrder = ref<'desc' | 'asc'>('desc')
const purchaserSortBy = ref('inventory_amount')
const purchaserSortOrder = ref<'desc' | 'asc'>('desc')

// ═══ 工具函数 ═══
function fmtWan(v: number) { return v ? (v / 10000).toFixed(2) : '0.00' }
function fmtPct(v: number) { return v?.toFixed(1) + '%' }
function fmtNum(v: number) { return v?.toLocaleString() || '0' }

// ═══ 实时时钟 ═══
const now = ref(new Date())
let timer: ReturnType<typeof setInterval> | null = null

function formatTime(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

onMounted(() => {
  loadAll()
  timer = setInterval(() => { now.value = new Date() }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

// ═══ 追溯链路 ═══
const traceChain = computed(() => {
  if (!summary.value || !claim.value) return null
  const inbound = summary.value.total_inbound_amount || 0
  const claimed = claim.value.all.total_claimed_amount || 0
  const remain = summary.value.total_inventory_amount || 0

  const consumedPct = inbound > 0 ? (claimed / inbound * 100) : 0
  const remainPct = inbound > 0 ? (remain / inbound * 100) : 0

  return {
    inbound: { label: '入库总额', value: inbound, unit: '万', desc: '累计采购入库金额' },
    consumed: { label: '已领用', value: claimed, unit: '万', pct: consumedPct, desc: '已消耗出库金额' },
    remain: { label: '当前库存', value: remain, unit: '万', pct: remainPct, desc: '未领用沉淀金额' },
  }
})

// ═══ 追溯效率评分 ═══
const traceScore = computed(() => {
  if (!claim.value || !timeIndicators.value) return null
  const claimRate = claim.value.all.claim_rate_amount || 0
  const agedRatio1y = (timeIndicators.value.aged_ratio_1y || 0) * 100
  const score = Math.min(100, Math.max(0, (claimRate * 0.6) + ((100 - agedRatio1y) * 0.4)))
  let grade = 'C'
  if (score >= 85) grade = 'A'
  else if (score >= 70) grade = 'B'
  return { score: Math.round(score), grade }
})

// ═══ 加载全部数据 ═══
async function loadAll() {
  loading.value = true
  error.value = null
  const errs: string[] = []

  const safeCall = async <T>(label: string, fn: () => Promise<T>): Promise<T | null> => {
    try {
      return await fn()
    } catch (e: any) {
      errs.push(`${label}: ${e?.message || '请求失败'}`)
      return null
    }
  }

  const [s, c, st, ti, ss, pi, puri] = await Promise.all([
    safeCall('总览', () => getTraceSummary()),
    safeCall('领用指标', () => getTraceClaim()),
    safeCall('库存结构', () => getTraceStructure()),
    safeCall('库龄指标', () => getTraceTime()),
    safeCall('来源结构', () => getSourceStructure()),
    safeCall('项目指标', () => getByProject()),
    safeCall('采购人指标', () => getByPurchaser()),
  ])

  summary.value = s
  claim.value = c
  structure.value = st
  timeIndicators.value = ti
  sourceStructure.value = ss
  projectIndicators.value = pi || []
  purchaserIndicators.value = puri || []

  const [ps, purs, bd] = await Promise.all([
    safeCall('项目汇总', () => getProjectSummary({ sort_by: projectSortBy.value, sort_order: projectSortOrder.value })),
    safeCall('采购人汇总', () => getPurchaserSummary({ sort_by: purchaserSortBy.value, sort_order: purchaserSortOrder.value })),
    safeCall('批次消化', () => getBatchDigest()),
  ])
  projectSummary.value = ps
  purchaserSummary.value = purs
  batchDigest.value = bd

  if (errs.length > 0) error.value = errs.join('；')
  loading.value = false
}

// ═══ 表格排序切换 ═══
async function toggleProjectSort(col: string) {
  if (projectSortBy.value === col) {
    projectSortOrder.value = projectSortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    projectSortBy.value = col
    projectSortOrder.value = 'desc'
  }
  try {
    projectSummary.value = await getProjectSummary({ sort_by: projectSortBy.value, sort_order: projectSortOrder.value })
  } catch {
    // 静默失败，保留上次数据
  }
}

async function togglePurchaserSort(col: string) {
  if (purchaserSortBy.value === col) {
    purchaserSortOrder.value = purchaserSortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    purchaserSortBy.value = col
    purchaserSortOrder.value = 'desc'
  }
  try {
    purchaserSummary.value = await getPurchaserSummary({ sort_by: purchaserSortBy.value, sort_order: purchaserSortOrder.value })
  } catch {
    // 静默失败
  }
}

function sortArrow(col: string, currentSort: string, currentOrder: string) {
  if (currentSort !== col) return '↕'
  return currentOrder === 'desc' ? '↓' : '↑'
}

</script>

<template>
  <div v-loading="loading" class="trace-page">
    <ErrorResult v-if="error" :message="error" @retry="loadAll" />

    <template v-if="!error && summary">
      <!-- ═══ 顶部标题栏 ═══ -->
      <div class="trace-header">
        <div class="header-left">
          <span class="header-title">🔍 库存追溯分析中心</span>
          <span class="header-subtitle">入库 → 消耗 → 沉淀，全链路可追溯</span>
        </div>
        <div class="header-right">
          <div v-if="traceScore" class="trace-score" :class="'grade-' + traceScore.grade">
            <span class="score-label">追溯健康度</span>
            <span class="score-value">{{ traceScore.score }}</span>
            <span class="score-grade">{{ traceScore.grade }}级</span>
          </div>
          <span class="header-time">{{ formatTime(now) }}</span>
        </div>
      </div>

      <!-- ═══ 核心KPI ═══ -->
      <div class="kpi-row">
        <el-tooltip content="累计采购入库总额 = SUM(original_quantity × unit_price)" placement="top">
          <div class="kpi-box" style="border-left-color:#3b82f6">
            <div class="kpi-icon">📥</div>
            <div class="kpi-body">
              <div class="kpi-label">入库总额（来源）</div>
              <div class="kpi-num">{{ fmtWan(summary.total_inbound_amount) }} <span class="kpi-unit">万</span></div>
              <div class="kpi-sub">累计采购入库金额</div>
            </div>
          </div>
        </el-tooltip>
        <el-tooltip content="累计领用出库总额" placement="top">
          <div class="kpi-box" style="border-left-color:#10b981">
            <div class="kpi-icon">📤</div>
            <div class="kpi-body">
              <div class="kpi-label">领用总额（消耗）</div>
              <div class="kpi-num">{{ fmtWan(claim?.all.total_claimed_amount || 0) }} <span class="kpi-unit">万</span></div>
              <div class="kpi-sub">已消耗出库金额</div>
            </div>
          </div>
        </el-tooltip>
        <el-tooltip content="当前未领用库存金额" placement="top">
          <div class="kpi-box" style="border-left-color:#f59e0b">
            <div class="kpi-icon">📦</div>
            <div class="kpi-body">
              <div class="kpi-label">当前库存（沉淀）</div>
              <div class="kpi-num">{{ fmtWan(summary.total_inventory_amount) }} <span class="kpi-unit">万</span></div>
              <div class="kpi-sub">{{ fmtNum(summary.total_inventory_quantity) }} 项库存</div>
            </div>
          </div>
        </el-tooltip>
        <el-tooltip content="领用金额 / 入库金额 × 100%" placement="top">
          <div class="kpi-box" style="border-left-color:#8b5cf6">
            <div class="kpi-icon">📊</div>
            <div class="kpi-body">
              <div class="kpi-label">整体领用率</div>
              <div class="kpi-num">{{ fmtPct(claim?.all.claim_rate_amount || 0) }}</div>
              <div class="kpi-sub">未领用占比 {{ fmtPct(claim?.all.unclaimed_amount_ratio || 0) }}</div>
            </div>
          </div>
        </el-tooltip>
      </div>

      <!-- ═══ 追溯链路可视化 ═══ -->
      <div class="trace-chain-section">
        <div class="section-title">
          <span>🔗 追溯链路：入库 → 消耗 → 沉淀</span>
          <span class="section-hint">金额流动全链路，一目了然</span>
        </div>
        <div class="chain-container">
          <!-- 入库节点 -->
          <div class="chain-node chain-inbound">
            <div class="chain-node-icon">📥</div>
            <div class="chain-node-title">入库来源</div>
            <div class="chain-node-value">{{ fmtWan(traceChain?.inbound.value || 0) }} 万</div>
            <div class="chain-node-desc">{{ traceChain?.inbound.desc }}</div>
          </div>

          <!-- 流动箭头 -->
          <div class="chain-arrow">
            <div class="arrow-line">
              <div class="arrow-fill" :style="{ width: traceChain ? Math.min(100, (traceChain.consumed.value / (traceChain.inbound.value || 1)) * 100) + '%' : '0%' }"></div>
            </div>
            <div class="arrow-label">领用率 {{ fmtPct(claim?.all.claim_rate_amount || 0) }}</div>
            <div class="arrow-icon">→</div>
          </div>

          <!-- 消耗节点 -->
          <div class="chain-node chain-consumed">
            <div class="chain-node-icon">📤</div>
            <div class="chain-node-title">已消耗</div>
            <div class="chain-node-value">{{ fmtWan(traceChain?.consumed.value || 0) }} 万</div>
            <div class="chain-node-desc">占比 {{ fmtPct(traceChain?.consumed.pct || 0) }}</div>
          </div>

          <!-- 流动箭头 -->
          <div class="chain-arrow">
            <div class="arrow-line arrow-remain">
              <div class="arrow-fill" :style="{ width: traceChain ? Math.min(100, (traceChain.remain.value / (traceChain.inbound.value || 1)) * 100) + '%' : '0%' }"></div>
            </div>
            <div class="arrow-label">沉淀率 {{ fmtPct(traceChain?.remain.pct || 0) }}</div>
            <div class="arrow-icon">→</div>
          </div>

          <!-- 沉淀节点 -->
          <div class="chain-node chain-remain">
            <div class="chain-node-icon">📦</div>
            <div class="chain-node-title">库存沉淀</div>
            <div class="chain-node-value">{{ fmtWan(traceChain?.remain.value || 0) }} 万</div>
            <div class="chain-node-desc">库龄 {{ summary.avg_age_weighted_days }} 天</div>
          </div>
        </div>
      </div>

      <!-- ═══ 第一行图表：来源追溯 ═══ -->
      <div class="chart-grid-2col">
        <!-- 项目来源追溯 -->
        <ChartCard title="🏗 项目来源追溯 TOP 8">
          <table class="mini-table" v-if="projectIndicators.length">
            <thead>
              <tr>
                <th>项目</th>
                <th class="num">入库金额</th>
                <th class="num">领用率</th>
                <th class="num">沉淀金额</th>
                <th class="num">库龄</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in projectIndicators.slice(0, 8)" :key="p.project_code">
                <td>
                  <el-tooltip :content="p.project_code" placement="top">
                    <span class="text-ellipsis">{{ p.project_name || p.project_code }}</span>
                  </el-tooltip>
                </td>
                <td class="num">{{ fmtWan(p.inbound_amount) }}万</td>
                <td class="num" :style="{ color: p.claim_rate < 30 ? '#f43f5e' : p.claim_rate < 60 ? '#f59e0b' : '#10b981' }">
                  {{ p.claim_rate.toFixed(1) }}%
                </td>
                <td class="num" :style="{ color: p.unclaimed_amount > 0 ? '#f43f5e' : '#64748b' }">
                  {{ fmtWan(p.unclaimed_amount) }}万
                </td>
                <td class="num" :style="{ color: p.avg_age_days > 180 ? '#f43f5e' : '#64748b' }">
                  {{ p.avg_age_days }}天
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-hint">暂无项目数据</div>
        </ChartCard>

        <!-- 采购人来源追溯 -->
        <ChartCard title="👤 采购人来源追溯 TOP 8">
          <table class="mini-table" v-if="purchaserIndicators.length">
            <thead>
              <tr>
                <th>采购人</th>
                <th class="num">入库金额</th>
                <th class="num">领用率</th>
                <th class="num">沉淀金额</th>
                <th class="num">库龄</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in purchaserIndicators.slice(0, 8)" :key="p.purchaser_id">
                <td>
                  <el-tooltip :content="p.purchaser_id" placement="top">
                    <span class="text-ellipsis">{{ p.purchaser_name || '(未知)' }}</span>
                  </el-tooltip>
                </td>
                <td class="num">{{ fmtWan(p.inbound_amount) }}万</td>
                <td class="num" :style="{ color: p.claim_rate < 30 ? '#f43f5e' : p.claim_rate < 60 ? '#f59e0b' : '#10b981' }">
                  {{ p.claim_rate.toFixed(1) }}%
                </td>
                <td class="num" :style="{ color: p.unclaimed_amount > 0 ? '#f43f5e' : '#64748b' }">
                  {{ fmtWan(p.unclaimed_amount) }}万
                </td>
                <td class="num" :style="{ color: p.avg_age_days > 180 ? '#f43f5e' : '#64748b' }">
                  {{ p.avg_age_days }}天
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-hint">暂无采购人数据</div>
        </ChartCard>
      </div>

      <!-- ═══ 第二行图表：时间追溯 + 来源结构 ═══ -->
      <div class="chart-grid-3col">
        <!-- 批次消化进度 — 时间追溯 -->
        <ChartCard title="📅 批次消化进度（时间追溯）">
          <div class="batch-container" v-if="batchDigest?.series?.length">
            <div
              v-for="s in batchDigest.series"
              :key="s.batch_code"
              class="batch-row"
            >
              <span class="batch-name" :style="{ color: s.color }">{{ s.batch_code }}</span>
              <div class="batch-bar-track">
                <div
                  class="batch-bar-fill"
                  :style="{ width: (s.data[0] / 100 * 100) + '%', background: s.color }"
                ></div>
              </div>
              <span class="batch-pct">{{ s.data[0].toFixed(1) }}%</span>
            </div>
            <div class="batch-legend">
              <span v-for="(lbl, i) in batchDigest.labels" :key="i" class="batch-legend-item">
                {{ lbl }}{{ i < batchDigest.labels.length - 1 ? ' → ' : '' }}
              </span>
            </div>
            <div class="batch-note">当前剩余占比（逐月模拟消化）</div>
          </div>
          <div v-else class="empty-hint">暂无批次消化数据</div>
        </ChartCard>

        <!-- 库龄结构分布 — 时间追溯 -->
        <ChartCard title="⏱ 库龄结构分布（时间追溯）">
          <div class="age-bars" v-if="timeIndicators?.age_structure?.length">
            <div class="age-bar" v-for="seg in timeIndicators.age_structure" :key="seg.range">
              <span class="age-label">{{ seg.range }}</span>
              <div class="age-track">
                <div
                  class="age-fill"
                  :style="{
                    width: Math.min(seg.ratio * 100, 100) + '%',
                    background: seg.range.includes('≥5') ? '#dc2626' : seg.range.includes('≥3') || seg.range.includes('3~') ? '#f59e0b' : seg.range.includes('1~') ? '#f97316' : '#3b82f6'
                  }"
                ></div>
              </div>
              <span class="age-info">
                <span class="age-pct">{{ (seg.ratio * 100).toFixed(2) }}%</span>
                <span class="age-amount">{{ fmtWan(seg.amount) }}万</span>
              </span>
            </div>
          </div>
          <div v-else class="empty-hint">暂无库龄数据</div>
        </ChartCard>

        <!-- 来源结构饼图区域 — 用简单的横向柱状图代替 -->
        <ChartCard title="🗂 库存来源结构">
          <div class="source-bars" v-if="sourceStructure?.rows?.length">
            <div class="source-bar" v-for="s in sourceStructure.rows.slice(0, 8)" :key="s.source_name">
              <span class="source-label" :title="s.source_name">{{ s.source_name || '(未归属)' }}</span>
              <div class="source-track">
                <div class="source-fill" :style="{ width: Math.max(2, s.ratio) + '%' }"></div>
              </div>
              <span class="source-pct">{{ s.ratio.toFixed(1) }}%</span>
              <span class="source-amount">{{ fmtWan(s.inventory_amount) }}万</span>
            </div>
          </div>
          <div v-else class="empty-hint">暂无来源结构数据</div>
        </ChartCard>
      </div>

      <!-- ═══ 项目追溯汇总表 ═══ -->
      <div class="trace-table-section">
        <div class="section-title">
          <span>📋 项目追溯汇总表</span>
          <span class="section-hint">按项目维度追溯入库→领用→库存，支持排序</span>
        </div>
        <div class="table-wrap">
          <table class="trace-table" v-if="projectSummary?.rows?.length">
            <thead>
              <tr>
                <th>项目名称</th>
                <th class="num sortable" @click="toggleProjectSort('inbound_amount')">
                  入库金额 {{ sortArrow('inbound_amount', projectSortBy, projectSortOrder) }}
                </th>
                <th class="num sortable" @click="toggleProjectSort('claimed_amount')">
                  领用金额 {{ sortArrow('claimed_amount', projectSortBy, projectSortOrder) }}
                </th>
                <th class="num sortable" @click="toggleProjectSort('inventory_amount')">
                  库存金额 {{ sortArrow('inventory_amount', projectSortBy, projectSortOrder) }}
                </th>
                <th class="num sortable" @click="toggleProjectSort('claim_rate')">
                  领用率 {{ sortArrow('claim_rate', projectSortBy, projectSortOrder) }}
                </th>
                <th class="num sortable" @click="toggleProjectSort('avg_age_days')">
                  平均库龄 {{ sortArrow('avg_age_days', projectSortBy, projectSortOrder) }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in projectSummary.rows" :key="row.project_code || row.project_name">
                <td>
                  <el-tooltip :content="row.project_code" placement="top">
                    <span class="text-ellipsis-cell">{{ row.project_name }}</span>
                  </el-tooltip>
                </td>
                <td class="num">{{ fmtWan(row.inbound_amount) }}万</td>
                <td class="num">{{ fmtWan(row.claimed_amount) }}万</td>
                <td class="num" :style="{ color: row.inventory_amount > 1000000 ? '#f43f5e' : '#334155' }">
                  {{ fmtWan(row.inventory_amount) }}万
                </td>
                <td class="num">
                  <span class="rate-badge" :class="{
                    'rate-low': row.claim_rate < 30,
                    'rate-mid': row.claim_rate >= 30 && row.claim_rate < 60,
                    'rate-high': row.claim_rate >= 60,
                  }">{{ row.claim_rate.toFixed(1) }}%</span>
                </td>
                <td class="num" :style="{ color: row.avg_age_days > 180 ? '#f43f5e' : row.avg_age_days > 90 ? '#f59e0b' : '#64748b' }">
                  {{ row.avg_age_days }}天
                </td>
              </tr>
            </tbody>
          </table>
          <div class="table-summary" v-if="projectSummary">
            共 {{ projectSummary.total }} 个项目
          </div>
        </div>
      </div>

      <!-- ═══ 采购人追溯汇总表 ═══ -->
      <div class="trace-table-section">
        <div class="section-title">
          <span>📋 采购人追溯汇总表</span>
          <span class="section-hint">按采购人维度追溯入库→领用→库存，支持排序</span>
        </div>
        <div class="table-wrap">
          <table class="trace-table" v-if="purchaserSummary?.rows?.length">
            <thead>
              <tr>
                <th>采购人</th>
                <th class="num sortable" @click="togglePurchaserSort('inbound_amount')">
                  入库金额 {{ sortArrow('inbound_amount', purchaserSortBy, purchaserSortOrder) }}
                </th>
                <th class="num sortable" @click="togglePurchaserSort('claimed_amount')">
                  领用金额 {{ sortArrow('claimed_amount', purchaserSortBy, purchaserSortOrder) }}
                </th>
                <th class="num sortable" @click="togglePurchaserSort('inventory_amount')">
                  库存金额 {{ sortArrow('inventory_amount', purchaserSortBy, purchaserSortOrder) }}
                </th>
                <th class="num sortable" @click="togglePurchaserSort('claim_rate')">
                  领用率 {{ sortArrow('claim_rate', purchaserSortBy, purchaserSortOrder) }}
                </th>
                <th class="num sortable" @click="togglePurchaserSort('avg_age_days')">
                  平均库龄 {{ sortArrow('avg_age_days', purchaserSortBy, purchaserSortOrder) }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in purchaserSummary.rows" :key="row.purchaser_name">
                <td>
                  <span class="text-ellipsis-cell">{{ row.purchaser_name }}</span>
                </td>
                <td class="num">{{ fmtWan(row.inbound_amount) }}万</td>
                <td class="num">{{ fmtWan(row.claimed_amount) }}万</td>
                <td class="num" :style="{ color: row.inventory_amount > 1000000 ? '#f43f5e' : '#334155' }">
                  {{ fmtWan(row.inventory_amount) }}万
                </td>
                <td class="num">
                  <span class="rate-badge" :class="{
                    'rate-low': row.claim_rate < 30,
                    'rate-mid': row.claim_rate >= 30 && row.claim_rate < 60,
                    'rate-high': row.claim_rate >= 60,
                  }">{{ row.claim_rate.toFixed(1) }}%</span>
                </td>
                <td class="num" :style="{ color: row.avg_age_days > 180 ? '#f43f5e' : row.avg_age_days > 90 ? '#f59e0b' : '#64748b' }">
                  {{ row.avg_age_days }}天
                </td>
              </tr>
            </tbody>
          </table>
          <div class="table-summary" v-if="purchaserSummary">
            共 {{ purchaserSummary.total }} 位采购人
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.trace-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  margin: -16px;
  padding: 16px;
  box-sizing: border-box;
  background: #f8fafc;
}

// ═══ 顶部标题栏 ═══
.trace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-radius: 10px;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  color: #fff;
  margin-bottom: 14px;
  flex-shrink: 0;

  .header-left {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  .header-title {
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  .header-subtitle {
    font-size: 12px;
    color: #94a3b8;
    font-weight: 400;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .header-time {
    font-family: 'Courier New', monospace;
    font-size: 14px;
    font-weight: 600;
    color: #cbd5e1;
  }
}

// ═══ 追溯健康度评分 ═══
.trace-score {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;

  .score-label { opacity: 0.8; }
  .score-value { font-size: 18px; font-weight: 800; }
  .score-grade { font-size: 11px; opacity: 0.7; }

  &.grade-A { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
  &.grade-B { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
  &.grade-C { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
}

// ═══ KPI 行 ═══
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
  flex-shrink: 0;

  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
}

.kpi-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 10px;
  padding: 16px 18px;
  border: 1px solid #e2e8f0;
  border-left-width: 3px;
  transition: transform 0.15s, box-shadow 0.15s;

  &:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,0.06); }

  .kpi-icon { font-size: 28px; flex-shrink: 0; }

  .kpi-body {
    min-width: 0;

    .kpi-label { font-size: 12px; color: #64748b; margin-bottom: 2px; }
    .kpi-num { font-size: 22px; font-weight: 800; color: #1e293b; line-height: 1.2; }
    .kpi-unit { font-size: 12px; font-weight: 500; color: #94a3b8; }
    .kpi-sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }
  }
}

// ═══ 追溯链路可视化 ═══
.trace-chain-section {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 18px 24px;
  margin-bottom: 14px;
  flex-shrink: 0;
}

.chain-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0;
  margin-top: 12px;
}

.chain-node {
  flex: 0 0 220px;
  text-align: center;
  padding: 18px 16px;
  border-radius: 12px;
  border: 2px solid;

  .chain-node-icon { font-size: 32px; margin-bottom: 6px; }
  .chain-node-title { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
  .chain-node-value { font-size: 22px; font-weight: 800; margin-bottom: 2px; }
  .chain-node-desc { font-size: 11px; opacity: 0.7; }
}

.chain-inbound {
  border-color: #93c5fd;
  background: #eff6ff;
  .chain-node-title { color: #2563eb; }
  .chain-node-value { color: #1e40af; }
  .chain-node-desc { color: #64748b; }
}

.chain-consumed {
  border-color: #86efac;
  background: #f0fdf4;
  .chain-node-title { color: #16a34a; }
  .chain-node-value { color: #15803d; }
  .chain-node-desc { color: #64748b; }
}

.chain-remain {
  border-color: #fdba74;
  background: #fff7ed;
  .chain-node-title { color: #ea580c; }
  .chain-node-value { color: #c2410c; }
  .chain-node-desc { color: #64748b; }
}

.chain-arrow {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 4px;
  min-width: 60px;

  .arrow-line {
    width: 100%;
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    overflow: hidden;

    .arrow-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #10b981);
      border-radius: 4px;
      transition: width 0.6s ease;
      min-width: 2px;
    }
  }

  .arrow-line.arrow-remain .arrow-fill {
    background: linear-gradient(90deg, #10b981, #f59e0b);
  }

  .arrow-label {
    font-size: 10px;
    color: #94a3b8;
    margin-top: 2px;
    white-space: nowrap;
  }

  .arrow-icon {
    font-size: 20px;
    color: #cbd5e1;
    margin-top: 0px;
  }
}

// ═══ 区块标题 ═══
.section-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;

  span:first-child { font-size: 14px; font-weight: 700; color: #1e293b; }
  .section-hint { font-size: 11px; color: #94a3b8; }
}

// ═══ 图表网格 ═══
.chart-grid-2col {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 14px;

  @media (max-width: 1024px) { grid-template-columns: 1fr; }
}

.chart-grid-3col {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 14px;

  @media (max-width: 1200px) { grid-template-columns: repeat(2, 1fr); }
  @media (max-width: 768px) { grid-template-columns: 1fr; }
}

// ═══ 迷你表格（来源追溯卡片内） ═══
.mini-table {
  width: 100%;
  font-size: 12px;
  border-collapse: collapse;

  thead th {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 500;
    padding: 4px 6px;
    border-bottom: 1px solid #e2e8f0;
    text-align: left;
  }

  td {
    padding: 5px 6px;
    border-bottom: 1px solid #f1f5f9;
    max-width: 120px;
  }

  .num { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }

  .text-ellipsis {
    display: inline-block;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: bottom;
  }
}

// ═══ 空数据提示 ═══
.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
  color: #94a3b8;
  font-size: 13px;
}

// ═══ 批次消化 ═══
.batch-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 4px 0;
}

.batch-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-name {
  width: 70px;
  font-size: 11px;
  font-weight: 700;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.batch-bar-track {
  flex: 1;
  height: 14px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.batch-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.batch-pct {
  width: 44px;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  text-align: right;
  flex-shrink: 0;
}

.batch-legend {
  font-size: 10px;
  color: #94a3b8;
  padding-left: 78px;
}

.batch-legend-item {
  display: inline;
}

.batch-note {
  font-size: 10px;
  color: #94a3b8;
  padding-left: 78px;
  font-style: italic;
}

// ═══ 库龄结构 ═══
.age-bars {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  min-height: 120px;
  padding: 0 4px;
}

.age-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.age-label {
  width: 56px;
  font-size: 11px;
  color: #64748b;
  text-align: right;
  flex-shrink: 0;
}

.age-track {
  flex: 1;
  height: 18px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.age-fill {
  height: 100%;
  border-radius: 4px;
  min-width: 2px;
  transition: width 0.4s ease;
}

.age-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  flex-shrink: 0;
}

.age-pct { font-size: 12px; font-weight: 600; }
.age-amount { font-size: 10px; color: #94a3b8; }

// ═══ 来源结构 ═══
.source-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
}

.source-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.source-label {
  width: 80px;
  font-size: 11px;
  color: #475569;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.source-track {
  flex: 1;
  height: 16px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.source-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 3px;
  min-width: 2px;
  transition: width 0.4s ease;
}

.source-pct {
  width: 42px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  text-align: right;
  flex-shrink: 0;
}

.source-amount {
  width: 52px;
  font-size: 10px;
  color: #94a3b8;
  text-align: right;
  flex-shrink: 0;
}

// ═══ 追溯汇总表 ═══
.trace-table-section {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 16px 20px;
  margin-bottom: 14px;
}

.table-wrap {
  margin-top: 10px;
  overflow-x: auto;
}

.trace-table {
  width: 100%;
  font-size: 13px;
  border-collapse: collapse;

  thead th {
    font-size: 12px;
    color: #64748b;
    font-weight: 600;
    padding: 8px 10px;
    border-bottom: 2px solid #e2e8f0;
    text-align: left;
    background: #f8fafc;
    white-space: nowrap;
    position: sticky;
    top: 0;
  }

  th.sortable {
    cursor: pointer;
    user-select: none;
    transition: color 0.15s;

    &:hover { color: #3b82f6; }
  }

  td {
    padding: 8px 10px;
    border-bottom: 1px solid #f1f5f9;
    max-width: 160px;
  }

  tbody tr {
    transition: background 0.1s;

    &:hover { background: #f8fafc; }
  }

  .num { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; color: #334155; }

  .text-ellipsis-cell {
    display: inline-block;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: bottom;
  }
}

.table-summary {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
  padding-left: 4px;
}

// ═══ 领用率徽章 ═══
.rate-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;

  &.rate-low { background: #fef2f2; color: #dc2626; }
  &.rate-mid { background: #fffbeb; color: #d97706; }
  &.rate-high { background: #f0fdf4; color: #16a34a; }
}
</style>
