<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { echarts } from '@/utils/echarts'
import { getWmsSummary, getErpClaim, getClaimWeekly, getErpAgeMonthly } from '@/api/modules/theme1'
import { getStructure } from '@/api/modules/theme2'
import type { WmsStructure } from '@/api/modules/theme2'
import { getTimeIndicators } from '@/api/modules/theme3'
import { getTopUnclaimedAmount, getOptimizeSuggest } from '@/api/modules/theme4'
import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import UsageRateTrend from '@/components/inventory/claim/UsageRateTrend.vue'
import AgeTrend from '@/components/inventory/time/AgeTrend.vue'
import { formatDays } from '@/utils/format'
import { filterExcluded } from '@/utils/excludeMaterials'

const loading = ref(false)
const error = ref<string | null>(null)
const summary = ref<any>(null)
const erpClaim = ref<any>(null)
const structure = ref<WmsStructure | null>(null)
const timeIndicators = ref<any>(null)
const topUnclaimed = ref<any[]>([])
const optimizeSuggest = ref<any[]>([])
const claimWeeklyRate = ref<any[]>([])
const claimWeeklyMonths = ref<string[]>([])
const erpAgeMonthlyData = ref<any>(null)
const projectBarRef = ref<HTMLDivElement>()
const agePieRef = ref<HTMLDivElement>()
let projectBarChart: any = null
let agePieChart: any = null

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [s, ec, st, ti, top, os, cw, eam] = await Promise.all([
      getWmsSummary(), getErpClaim(), getStructure(), getTimeIndicators(), getTopUnclaimedAmount(8),
      getOptimizeSuggest(5, 60), getClaimWeekly(), getErpAgeMonthly(),
    ])
    summary.value = s
    erpClaim.value = ec
    structure.value = st
    timeIndicators.value = ti
    topUnclaimed.value = filterExcluded(top)
    optimizeSuggest.value = os
    // 领用率周趋势
    if (cw?.data) {
      claimWeeklyRate.value = cw.data.map((d: any) => ({ month: d.week, rate: d.claim_rate, target: 20, trend: 0 }))
      claimWeeklyMonths.value = cw.weeks || []
    }
    erpAgeMonthlyData.value = eam
  } catch (e: any) {
    error.value = e.message || '加载失败'
  }
  loading.value = false
}

function fmtWan(v: number) { return v ? (v / 10000).toFixed(2) : '0.00' }
function truncateText(text: string, maxLen = 20): string {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '…' : text
}
function fmtAge(days: number | undefined | null): string {
  if (days == null) return '-'
  return formatDays(days)
}

function renderProjectBar() {
  const projs = (structure.value?.project_ratios || [])
    .filter((p: any) => p.project_name && p.project_name !== '非项目物资')
    .slice(0, 8)
  if (!projectBarRef.value || !projs.length) return
  if (!projectBarChart) {
    projectBarChart = echarts.init(projectBarRef.value)
  }
  projectBarChart.setOption({
    tooltip: { trigger: 'axis', formatter: (params: any) => `${projs[params[0].dataIndex]?.project_name || params[0].name}<br/>库存: ${params[0].value} 万` },
    grid: { left: 10, right: 10, top: 10, bottom: 50 },
    xAxis: { type: 'category', data: projs.map((p: any) => (p.project_name || '').length > 6 ? (p.project_name || '').slice(0, 6) + '…' : p.project_name), axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}万' } },
    series: [{ type: 'bar', data: projs.map((p: any) => +((p.inventory_amount || 0) / 10000).toFixed(0)), itemStyle: { color: '#3b82f6', borderRadius: [4,4,0,0] } }],
  }, true)
}

function renderAgePie() {
  const segs = (timeIndicators.value?.age_structure || []).filter((s: any) => s.range !== '≥5年')
  if (!agePieRef.value || !segs.length) return
  if (!agePieChart) agePieChart = echarts.init(agePieRef.value)
  agePieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 万 ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '50%'],
      data: segs.map((s: any) => ({ name: s.range, value: +(s.amount / 10000).toFixed(2) })),
      label: { formatter: '{b}\n{d}%' },
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      color: ['#3b82f6', '#f59e0b', '#f43f5e'],
    }],
  }, true)
}

watch(() => structure.value?.project_ratios, () => nextTick(renderProjectBar))
watch(() => timeIndicators.value?.age_structure, () => nextTick(renderAgePie))
onMounted(() => { setTimeout(renderProjectBar, 500); setTimeout(renderAgePie, 600) })

// 实时时钟
const now = ref(new Date())
let timer: ReturnType<typeof setInterval> | null = null

function formatTime(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
}

// 全屏切换
const isFullscreen = ref(false)
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}
function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
  // 全屏动画结束后多次 resize，确保 echarts 拿到最终尺寸
  ;[300, 600, 1000].forEach(delay => {
    setTimeout(() => {
      projectBarChart?.resize()
      agePieChart?.resize()
      window.dispatchEvent(new Event('resize'))
    }, delay)
  })
}

onMounted(() => {
  loadAll()
  timer = setInterval(() => { now.value = new Date() }, 1000)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})



</script>

<template>
  <div v-loading="loading" class="hub-page">
    <ErrorResult v-if="error" :message="error" @retry="loadAll" />

    <template v-if="!error && summary">
      <!-- 顶部标题栏 -->
      <div class="dashboard-header">
        <span class="header-title">业务数据</span>
        <span class="header-time">{{ formatTime(now) }}</span>
        <span class="header-fs-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏展示'">
          {{ isFullscreen ? '⛶' : '⛶' }}
        </span>
      </div>

      <!-- 核心KPI -->
      <div class="kpi-row">
        <el-tooltip content="WMS实物在库 + ERP有余额未入WMS的批次" placement="top">
          <div class="kpi-box" style="border-left-color:#f59e0b">
            <div class="kpi-label">当前库存总额</div>
            <div class="kpi-num">{{ (erpClaim?.erp_inventory ?? 0).toFixed(2) }} 万</div>
            <div class="kpi-sub">期末在库物资总金额</div>
          </div>
        </el-tooltip>
        <el-tooltip content="ERP数据：当年出库金额 / 入库金额 × 100%" placement="top">
          <div class="kpi-box" style="border-left-color:#10b981">
            <div class="kpi-label">采购领用率（{{ erpClaim?.current_year }}年）</div>
            <div class="kpi-num">{{ erpClaim?.year?.claim_rate_amount?.toFixed(2) }}%</div>
            <div class="kpi-sub">= {{ erpClaim?.year?.total_outbound_amount?.toFixed(0) || 0 }}万 / {{ erpClaim?.year?.net_inbound_amount?.toFixed(0) || 0 }}万</div>
          </div>
        </el-tooltip>
        <el-tooltip content="ERP数据：SUM(DMBTR) 101 移动类型" placement="top">
          <div class="kpi-box" style="border-left-color:#3b82f6">
            <div class="kpi-label">入库总额（{{ erpClaim?.current_year }}年）</div>
            <div class="kpi-num">{{ erpClaim?.year?.total_inbound_amount?.toFixed(2) }} 万</div>
            <div class="kpi-sub">当年采购入库金额</div>
          </div>
        </el-tooltip>
        <el-tooltip content="Σ(库存金额 × 库龄天数) / Σ(库存金额)  金额加权平均" placement="top">
          <div class="kpi-box" style="border-left-color:#8b5cf6">
            <div class="kpi-label">加权平均库龄（{{ erpClaim?.current_year }}年）</div>
            <div class="kpi-num">{{ fmtAge(timeIndicators?.avg_age_weighted_days) }}</div>
            <div class="kpi-sub">≥1年占比 {{ (timeIndicators?.aged_ratio_1y * 100).toFixed(1) }}%</div>
          </div>
        </el-tooltip>
      </div>

      <!-- 快速一览 -->
      <div class="chart-grid">
        <ChartCard title="📉 物资领用率趋势（按周）">
          <UsageRateTrend :data="claimWeeklyRate" :months="claimWeeklyMonths" granularity="周" :hideDetail="true" />
        </ChartCard>

        <ChartCard title="🌳 项目库存金额分布 TOP 8">
          <div ref="projectBarRef" style="width:100%;height:100%;min-height:200px"></div>
        </ChartCard>

        <ChartCard title="📊 加权平均库龄月度趋势">
          <AgeTrend
            :data="(erpAgeMonthlyData?.rows || []).filter((d: any) => d.doc_month.startsWith('2026')).map((d: any) => ({ month: d.doc_month, avgAge: d.avg_age, trend: 0, over90Rate: d.over90_rate }))"
            :months="(erpAgeMonthlyData?.rows || []).filter((d: any) => d.doc_month.startsWith('2026')).map((d: any) => d.doc_month)"
            :hideDetail="true"
          />
        </ChartCard>

        <!-- 第二行：3 个补充指标 -->
        <ChartCard :title="'👤 项目负责人库存占比 TOP ' + (isFullscreen ? 10 : 5)">
          <table class="mini-table" v-if="structure?.purchaser_ratios?.length">
            <tr v-for="p in structure.purchaser_ratios.slice(0, isFullscreen ? 10 : 5)" :key="p.purchaser_id">
              <td>{{ p.purchaser_name || p.purchaser_id }}</td>
              <td class="num" :style="{ color: p.ratio > 0.15 ? '#f43f5e' : '#334155' }">
                <el-tooltip :content="`${fmtWan(p.inventory_amount)}万 / 总库存金额`" placement="top">
                  <span>{{ (p.ratio * 100).toFixed(1) }}%</span>
                </el-tooltip>
              </td>
              <td class="num" style="font-size:11px;color:#94a3b8">{{ fmtWan(p.inventory_amount) }}万</td>
            </tr>
          </table>
        </ChartCard>

        <ChartCard title="📦 库龄结构分布">
          <div ref="agePieRef" style="width:100%;height:100%"></div>
        </ChartCard>

        <ChartCard :title="'💡 智能库存优化建议 TOP ' + (isFullscreen ? 10 : 5)">
          <table class="mini-table" v-if="optimizeSuggest?.length">
            <tr v-for="item in optimizeSuggest.slice(0, isFullscreen ? 10 : 5)" :key="item.name">
              <td>
                <el-tooltip :content="item.name" placement="top" :disabled="(item.name || '').length <= 20">
                  <span>{{ truncateText(item.name) }}</span>
                </el-tooltip>
              </td>
              <td class="num" style="color:#f43f5e">{{ item.current.toFixed(2) }} 万</td>
            </tr>
          </table>
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.hub-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  margin: -16px;
  padding: 16px;
  box-sizing: border-box;
}

// ═══ Dashboard 顶部标题栏 ═══
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  margin-bottom: 12px;
  flex-shrink: 0;

  .header-title {
    background: linear-gradient(90deg, var(--db-title-from, #1e3a8a), var(--db-title-to, #3b82f6));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    font-size: 16px;
    font-weight: 700;
    -webkit-text-fill-color: transparent;
  }

  .header-time {
    color: var(--db-time-color, #64748b);
    font-family: 'Courier New', monospace;
    font-size: 14px;
    font-weight: 600;
  }

  .header-fs-btn {
    cursor: pointer;
    font-size: 18px;
    color: #64748b;
    transition: color 0.2s;
    &:hover { color: #3b82f6; }
  }
}

.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
}
.kpi-box { background: #fff; border-radius: 8px; padding: 14px 18px; border: 1px solid #e2e8f0; border-left-width: 3px;
  .kpi-label { font-size: 12px; color: #64748b; margin-bottom: 4px; }
  .kpi-num { font-size: 24px; font-weight: 800; color: #1e293b; }
  .kpi-sub { font-size: 11px; color: #94a3b8; margin-top: 4px; }
}

.path-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;
  @media (max-width: 768px) { grid-template-columns: 1fr; }
}
.path-card { border-radius: 10px; padding: 18px 20px; border: 1px solid #e2e8f0; border-top-width: 3px; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
  &:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
  .path-icon { font-size: 32px; margin-bottom: 8px; }
  .path-title { font-size: 16px; font-weight: 700; margin-bottom: 2px; }
  .path-subtitle { font-size: 13px; color: #64748b; margin-bottom: 4px; }
  .path-desc { font-size: 11px; color: #64748b; }
}

.chart-grid { display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: 1fr 1fr; gap: 12px; flex: 1; min-height: 0;
  @media (max-width: 1024px) { grid-template-columns: 1fr; }
  .chart-card { display: flex; flex-direction: column; min-height: 0; }
  // 让 card body 填满、子组件的 echarts 容器自适应
  :deep(.el-card__body) { flex: 1; display: flex; flex-direction: column; min-height: 0; }
  :deep(.chart) { width: 100% !important; flex: 1; min-height: 180px; }
}
.mini-table { width: 100%; font-size: 13px; border-collapse: collapse;
  td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; }
  .num { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
}

</style>
