<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { getKpiChecklist } from '@/api/modules/kpiChecklist'
import type { KpiChecklistRes, KpiItem } from '@/api/modules/kpiChecklist'
import { getErpClaim } from '@/api/modules/theme1'
import type { ErpClaimSplit } from '@/api/modules/theme1'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import { formatDays } from '@/utils/format'
import { filterExcluded } from '@/utils/excludeMaterials'

const loading = ref(false)
const error = ref<string | null>(null)

const summary = ref<KpiChecklistRes['summary'] | null>(null)
const erpClaim = ref<ErpClaimSplit | null>(null)
const coreKpis = ref<Record<string, KpiItem>>({})
const constraintKpis = ref<Record<string, KpiItem>>({})
const structureKpis = ref<KpiChecklistRes['structure_kpis'] | null>(null)
const topKpis = ref<KpiChecklistRes['top_kpis'] | null>(null)

// 过滤掉排除物资的 TOP 数据
const filteredTopKpis = computed(() => {
  if (!topKpis.value) return null
  return {
    ...topKpis.value,
    T1: topKpis.value.T1 ? { ...topKpis.value.T1, items: filterExcluded(topKpis.value.T1.items || []) } : undefined,
    T2: topKpis.value.T2 ? {
      ...topKpis.value.T2,
      by_amount: filterExcluded(topKpis.value.T2.by_amount || []),
      by_quantity: filterExcluded(topKpis.value.T2.by_quantity || []),
    } : undefined,
  }
})

async function loadAllData() {
  loading.value = true
  error.value = null
  try {
    const [data, ec] = await Promise.all([getKpiChecklist(), getErpClaim()])
    summary.value = data.summary
    erpClaim.value = ec
    coreKpis.value = data.core_kpis
    constraintKpis.value = data.constraint_kpis
    structureKpis.value = data.structure_kpis
    topKpis.value = data.top_kpis
  } catch (e: any) {
    console.error('KPI考核清单数据加载失败:', e)
    error.value = e?.message || '数据加载失败'
  } finally {
    loading.value = false
  }
}

// 核心考核 KPI 条目（便于迭代）
const coreKpiList = computed(() => {
  const list = Object.values(coreKpis.value)
  if (!erpClaim.value) return list
  return list.map(kpi => {
    if (kpi.key === 'K1') {
      const ec = erpClaim.value!.year
      return {
        ...kpi,
        value: ec.claim_rate_amount,
        formula: `出库金额 / 入库金额 × 100%（${ec.total_outbound_amount?.toFixed(0) ?? 0}万 / ${ec.total_inbound_amount?.toFixed(0) ?? 0}万）`,
        detail: {
          ...kpi.detail,
          inbound_amount_wan: ec.total_inbound_amount,
          claimed_amount_wan: ec.total_outbound_amount,
          unclaimed_amount_wan: ec.unclaimed_amount,
        },
      }
    }
    return kpi
  })
})
const constraintKpiList = computed(() => Object.values(constraintKpis.value))

// 状态颜色与标签
const statusConfig: Record<string, { color: string; label: string; bg: string }> = {
  ok:      { color: '#10b981', label: '达标',   bg: '#ecfdf5' },
  warning: { color: '#f59e0b', label: '关注',   bg: '#fffbeb' },
  alert:   { color: '#f43f5e', label: '预警',   bg: '#fef2f2' },
  info:    { color: '#3b82f6', label: '观测',   bg: '#eff6ff' },
}

// 状态图标的映射
const statusIcon: Record<string, string> = {
  ok:      '✅',
  warning: '⚠️',
  alert:   '🔴',
  info:    '📊',
}

// 格式化数值：保留两位小数，加千分位
function formatNumber(val: number | undefined | null): string {
  if (val == null) return '--'
  return Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 数据概览卡片
const overviewCards = computed(() => {
  if (!summary.value) return []
  const ec = erpClaim.value
  return [
     { icon: '📦', label: '当前库存', value: summary.value.current_inventory_wan, unit: '万元', color: '#f59e0b' },
    { icon: '📤', label: '出库总额', value: ec?.year?.total_outbound_amount ?? 0, unit: '万元', color: '#10b981' },
    { icon: '📥', label: '入库总额', value: ec?.year?.total_inbound_amount ?? 0, unit: '万元', color: '#3b82f6' },
   { icon: '📈', label: '综合领用率', value: ec?.year?.claim_rate_amount ?? 0, unit: '%', color: '#8b5cf6' },
  ]
})

// 时间维度
const timeRangeLabel = computed(() => {
  if (!summary.value) return ''
  const { data_start_date, data_end_date } = summary.value
  if (data_start_date && data_end_date) {
    return `数据范围：${data_start_date} ~ ${data_end_date}`
  }
  return ''
})

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载KPI考核清单..." class="kpi-checklist-page">

    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />

    <template v-if="!error && summary">
      <!-- ══════════════════════════════════════════════════ -->
      <!-- 页面标题 & 状态摘要 -->
      <!-- ══════════════════════════════════════════════════ -->
      <div class="page-header">
        <div class="page-header__left">
          <h2 class="page-title">📋 KPI 考核清单</h2>
          <span class="page-subtitle">更新于 {{ summary.update_time }}&nbsp;&nbsp;|&nbsp;&nbsp;{{ timeRangeLabel }}</span>
        </div>
        <div class="status-summary">
          <div class="status-chip ok">
            <span class="chip-dot" style="background:#10b981"></span>
            达标 {{ summary.ok_count }}
          </div>
          <div class="status-chip warning">
            <span class="chip-dot" style="background:#f59e0b"></span>
            关注 {{ summary.warning_count }}
          </div>
          <div class="status-chip alert">
            <span class="chip-dot" style="background:#f43f5e"></span>
            预警 {{ summary.alert_count }}
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════ -->
      <!-- 数据概览卡片 -->
      <!-- ══════════════════════════════════════════════════ -->
      <div class="overview-row">
        <div
          v-for="card in overviewCards"
          :key="card.label"
          class="overview-card"
          :style="{ borderTopColor: card.color }"
        >
          <div class="overview-card__icon">{{ card.icon }}</div>
          <div class="overview-card__content">
            <div class="overview-card__label">{{ card.label }}</div>
            <div class="overview-card__value" :style="{ color: card.color }">
              {{ typeof card.value === 'number' ? formatNumber(card.value) : card.value }}
              <span class="overview-card__unit">{{ card.unit }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════ -->
      <!-- 第一类：核心考核指标 K1-K3 -->
      <!-- ══════════════════════════════════════════════════ -->
      <div class="section">
        <div class="section-header">
          <span class="section-badge core">第一类</span>
          <span class="section-title">核心考核指标</span>
          <span class="section-desc">K1 · K2 · K3 — 反映采购消化质量与库存资金占用</span>
        </div>
        <div class="kpi-grid kpi-grid--3col">
          <div
            v-for="kpi in coreKpiList"
            :key="kpi.key"
            class="kpi-card"
            :class="`kpi-card--${kpi.status}`"
          >
            <div class="kpi-card__header">
              <span class="kpi-card__key">{{ kpi.key }}</span>
              <span class="kpi-card__name">{{ kpi.name }}</span>
              <span
                class="kpi-card__status"
                :style="{ color: statusConfig[kpi.status]?.color }"
              >
                {{ statusIcon[kpi.status] }} {{ statusConfig[kpi.status]?.label }}
              </span>
            </div>
            <div class="kpi-card__body">
              <div class="kpi-card__value-row">
                <span class="kpi-card__value" :style="{ color: statusConfig[kpi.status]?.color }">
                  {{ typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value }}
                </span>
                <span class="kpi-card__unit">{{ kpi.unit }}</span>
              </div>
              <div class="kpi-card__formula" v-if="kpi.formula">
                <span class="label">计算方式：</span>{{ kpi.formula }}
              </div>
              <div class="kpi-card__target">
                <span class="label">目标：</span>{{ kpi.target }}
              </div>
              <div class="kpi-card__detail" v-if="kpi.key === 'K1' && kpi.detail">
                <div class="detail-row">
                  <span>入库金额 (ERP)</span><span>{{ kpi.detail.inbound_amount_wan?.toLocaleString() }} 万元</span>
                </div>
                <div class="detail-row">
                  <span>出库金额 (ERP)</span><span>{{ kpi.detail.claimed_amount_wan?.toLocaleString() }} 万元</span>
                </div>
                <div class="detail-row">
                  <span>未领用金额</span><span>{{ kpi.detail.unclaimed_amount_wan?.toLocaleString() }} 万元</span>
                </div>
                <div class="detail-row">
                  <span>数量领用率</span><span>{{ erpClaim?.year?.claim_rate_quantity?.toLocaleString() }}%</span>
                </div>
              </div>
              <div v-if="kpi.key === 'K3' && kpi.detail?.age_structure" class="kpi-card__detail">
                <div class="detail-row" v-for="seg in kpi.detail.age_structure" :key="seg.range">
                  <span>{{ seg.range }}</span>
                  <span>{{ (seg.ratio * 100).toFixed(2) }}% ({{ seg.count }}笔)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════ -->
      <!-- 第二类：约束类考核指标 K4-K5 -->
      <!-- ══════════════════════════════════════════════════ -->
      <div class="section">
        <div class="section-header">
          <span class="section-badge constraint">第二类</span>
          <span class="section-title">约束类考核指标</span>
          <span class="section-desc">K4 · K5 — 控制新增库存，约束项目采购</span>
        </div>
        <div class="kpi-grid kpi-grid--2col">
          <div
            v-for="kpi in constraintKpiList"
            :key="kpi.key"
            class="kpi-card"
            :class="`kpi-card--${kpi.status}`"
          >
            <div class="kpi-card__header">
              <span class="kpi-card__key">{{ kpi.key }}</span>
              <span class="kpi-card__name">{{ kpi.name }}</span>
              <span
                class="kpi-card__status"
                :style="{ color: statusConfig[kpi.status]?.color }"
              >
                {{ statusIcon[kpi.status] }} {{ statusConfig[kpi.status]?.label }}
              </span>
            </div>
            <div class="kpi-card__body">
              <div class="kpi-card__value-row">
                <span class="kpi-card__value" :style="{ color: statusConfig[kpi.status]?.color }">
                  {{ typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value }}
                </span>
                <span class="kpi-card__unit">{{ kpi.unit }}</span>
              </div>
              <div class="kpi-card__target">
                <span class="label">目标：</span>{{ kpi.target }}
              </div>
              <!-- K4 详细 -->
              <div v-if="kpi.key === 'K4' && kpi.detail" class="kpi-card__detail">
                <div class="detail-row">
                  <span>未领用占比</span><span>{{ kpi.detail.unclaimed_ratio }}%</span>
                </div>
                <div class="detail-row">
                  <span>入库总额</span><span>{{ kpi.detail.total_inbound_wan?.toLocaleString() }} 万元</span>
                </div>
                <div class="detail-row">
                  <span>领用总额</span><span>{{ kpi.detail.total_claimed_wan?.toLocaleString() }} 万元</span>
                </div>
              </div>
              <!-- K5 项目详情表 -->
              <div v-if="kpi.key === 'K5' && kpi.detail?.projects" class="kpi-card__table-wrap">
                <table class="mini-table">
                  <thead>
                    <tr>
                      <th>项目</th>
                      <th>未消耗(万元)</th>
                      <th>领用率</th>
                      <th>平均库龄</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in kpi.detail.projects.filter(p => p.project_code).slice(0, 5)" :key="p.project_code">
                      <td><span class="proj-name">{{ p.project_name || '-' }}</span></td>
                      <td>{{ p.unclaimed_amount_wan?.toLocaleString() }}</td>
                      <td>
                        <span :style="{ color: p.claim_rate >= 60 ? '#10b981' : p.claim_rate >= 30 ? '#f59e0b' : '#f43f5e' }">
                          {{ p.claim_rate }}%
                        </span>
                      </td>
                      <td>{{ formatDays(p.avg_age_days) }}</td>
                    </tr>
                  </tbody>
                </table>
                <div v-if="kpi.detail.total_count > 5" class="table-more">
                  共 {{ kpi.detail.total_count }} 个项目，仅展示前5项
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════ -->
      <!-- 第三类：结构分析指标 K6-K9 -->
      <!-- ══════════════════════════════════════════════════ -->
      <div class="section">
        <div class="section-header">
          <span class="section-badge structure">第三类</span>
          <span class="section-title">结构分析指标</span>
          <span class="section-desc">K6 · K7 · K8 · K9 — 多维度库存画像</span>
        </div>

        <!-- K6 库存结构 — 项目库存占比（含人员信息） -->
        <ChartCard title="K6 · 库存结构分析 — 项目库存占比">
          <table class="mini-table" v-if="structureKpis?.K6?.project_ratios?.length">
            <thead>
              <tr><th>项目</th><th>计划提报人</th><th>项目负责人</th><th>库存(万元)</th><th>占比</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in structureKpis.K6.project_ratios.filter(p => p.project_code).slice(0, 8)" :key="p.project_code">
                <td>{{ p.project_name || '-' }}</td>
                <td>{{ p.project_submitter || '-' }}</td>
                <td>{{ p.project_contact || '-' }}</td>
                <td>{{ p.inventory_amount_wan?.toLocaleString() }}</td>
                <td>
                  <div class="ratio-bar">
                    <div class="ratio-bar__fill" :style="{ width: p.ratio + '%', background: '#3b82f6' }"></div>
                    <span>{{ p.ratio }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </ChartCard>

        <!-- K7 时间分析 -->
        <ChartCard title="K7 · 时间分析">
          <div class="time-metrics" v-if="structureKpis?.K7">
            <el-tooltip content="= Σ(库存金额 × 库龄天数) / Σ(库存金额)，按物理批次去重计算" placement="top">
              <div class="time-metric-card">
                <div class="time-metric-card__value">{{ formatDays(structureKpis.K7.avg_age_weighted_days) }}</div>
                <div class="time-metric-card__label">加权平均库龄（天）</div>
              </div>
            </el-tooltip>
            <el-tooltip content="= 库龄 ≥ 365天的库存金额 / 总库存金额" placement="top">
              <div class="time-metric-card">
                <div class="time-metric-card__value">{{ structureKpis.K7.aged_ratio_1y }}%</div>
                <div class="time-metric-card__label">长库龄占比（≥1年）</div>
              </div>
            </el-tooltip>
          </div>
          <!-- 库龄结构分段 -->
          <div class="age-bar-wrap" v-if="structureKpis?.K7?.age_structure">
            <div
              v-for="seg in structureKpis.K7.age_structure"
              :key="seg.range"
              class="age-bar"
            >
              <div class="age-bar__label">{{ seg.range }}</div>
              <div class="age-bar__track">
                <div
                  class="age-bar__fill"
                  :style="{
                    width: Math.max((seg.ratio * 100), 1) + '%',
                    background: seg.range.includes('≥5') ? '#f43f5e' : seg.range.includes('3~5') ? '#f59e0b' : seg.range.includes('1~3') ? '#3b82f6' : '#10b981'
                  }"
                ></div>
              </div>
              <div class="age-bar__pct">{{ (seg.ratio * 100).toFixed(2) }}%</div>
            </div>
          </div>
        </ChartCard>

        <!-- K8 项目分析 -->
        <ChartCard title="K8 · 项目分析">
          <div class="kpi-table-wrap" v-if="structureKpis?.K8?.items?.length">
            <table class="data-table">
              <thead>
                <tr>
                  <th>项目名称</th>
                  <th>领用率</th>
                  <th>库存金额(万元)</th>
                  <th>平均库龄(天)</th>
                  <th>超90天占比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in structureKpis.K8.items.filter(p => p.project_code).slice(0, 15)" :key="p.project_code">
                  <td>
                    <span class="proj-name">{{ p.project_name || '-' }}</span>
                  </td>
                  <td>
                    <span
                      class="rate-tag"
                      :style="{
                        color: p.claim_rate >= 60 ? '#10b981' : p.claim_rate >= 30 ? '#f59e0b' : '#f43f5e',
                        background: p.claim_rate >= 60 ? '#ecfdf5' : p.claim_rate >= 30 ? '#fffbeb' : '#fef2f2',
                      }"
                    >
                      {{ p.claim_rate }}%
                    </span>
                  </td>
                  <td>{{ (p.inventory_amount_wan || 0).toLocaleString() }}</td>
                  <td>{{ formatDays(p.avg_age_days) }}</td>
                  <td>{{ p.over90_ratio || 0 }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </ChartCard>

        <!-- K9 采购人分析 -->
        <ChartCard title="K9 · 采购人分析">
          <div class="kpi-table-wrap" v-if="structureKpis?.K9?.items?.length">
            <table class="data-table">
              <thead>
                <tr>
                  <th>采购人</th>
                  <th>领用率</th>
                  <th>未消耗库存(万元)</th>
                  <th>平均库龄(天)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in structureKpis.K9.items.slice(0, 15)" :key="p.purchaser_name">
                  <td>{{ p.purchaser_name }}</td>
                  <td>
                    <span
                      class="rate-tag"
                      :style="{
                        color: p.claim_rate >= 60 ? '#10b981' : p.claim_rate >= 30 ? '#f59e0b' : '#f43f5e',
                        background: p.claim_rate >= 60 ? '#ecfdf5' : p.claim_rate >= 30 ? '#fffbeb' : '#fef2f2',
                      }"
                    >
                      {{ p.claim_rate }}%
                    </span>
                  </td>
                  <td>{{ (p.unclaimed_amount_wan || 0).toLocaleString() }}</td>
                  <td>{{ formatDays(p.avg_age_days) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </ChartCard>
      </div>

      <!-- ══════════════════════════════════════════════════ -->
      <!-- 第四类：TOP类指标 T1-T2 -->
      <!-- ══════════════════════════════════════════════════ -->
      <div class="section">
        <div class="section-header">
          <span class="section-badge top">第四类</span>
          <span class="section-title">TOP 指标</span>
          <!-- <span class="section-desc">T1 · T2 — 每月必须输出，用于责任到人、优化备货</span> -->
        </div>

        <!-- T1 未领用库存TOP10 -->
        <ChartCard title="T1 · 未领用库存 TOP10（金额）— 责任到项目、跟踪处理">
          <div class="kpi-table-wrap" v-if="topKpis?.T1?.items?.length">
            <table class="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>物料编码</th>
                  <th>物料名称</th>
                  <th>库存金额(万元)</th>
                  <th>数量</th>
                  <th>库龄(天)</th>
                  <th>归属项目</th>
                  <th>采购人</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in filteredTopKpis.T1.items"
                  :key="item.material_code"
                  :class="{ 'row-alert': item.age_days > 365 }"
                >
                  <td>
                    <span class="rank-badge" :class="item.rank <= 3 ? `rank-${item.rank}` : ''">
                      {{ item.rank }}
                    </span>
                  </td>
                  <td><code>{{ item.material_code }}</code></td>
                  <td>{{ item.material_name }}</td>
                  <td class="num">{{ item.inventory_amount_wan?.toLocaleString() }}</td>
                  <td>{{ item.current_quantity }} {{ item.unit }}</td>
                  <td>
                    <span :style="{ color: item.age_days > 365 ? '#f43f5e' : item.age_days > 180 ? '#f59e0b' : '#10b981' }">
                      {{ formatDays(item.age_days) }}
                    </span>
                  </td>
                  <td>{{ item.owner_project_name || '-' || '-' }}</td>
                  <td>{{ item.purchaser_name || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </ChartCard>

        <!-- T2 领用TOP10 -->
        <ChartCard title="T2 · 领用 TOP10">
          <el-tabs type="border-card" v-if="topKpis?.T2">
            <el-tab-pane label="按金额排序">
              <table class="data-table" v-if="filteredTopKpis?.T2.by_amount?.length">
                <thead>
                  <tr>
                    <th style="text-align:center">#</th>
                    <th>物料编码</th>
                    <th>物料名称</th>
                    <th style="text-align:right">领用金额(万元)</th>
                    <th style="text-align:right">入库金额(万元)</th>
                    <th>入库日期</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in filteredTopKpis?.T2.by_amount" :key="item.material_code">
                    <td>
                      <span class="rank-badge" :class="item.rank <= 3 ? `rank-${item.rank}` : ''">
                        {{ item.rank }}
                      </span>
                    </td>
                    <td><code>{{ item.material_code }}</code></td>
                    <td>{{ item.material_name }}</td>
                    <td class="num">{{ item.claimed_amount_wan?.toLocaleString() }}</td>
                    <td class="num">{{ item.inbound_amount_wan?.toLocaleString() }}</td>
                    <td>{{ item.inbound_date }}</td>
                  </tr>
                </tbody>
              </table>
            </el-tab-pane>
            <el-tab-pane label="按数量排序">
              <table class="data-table" v-if="filteredTopKpis?.T2.by_quantity?.length">
                <thead>
                  <tr>
                    <th style="text-align:center">#</th>
                    <th>物料编码</th>
                    <th>物料名称</th>
                    <th style="text-align:right">领用数量</th>
                    <th style="text-align:right">入库数量</th>
                    <th>入库日期</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in filteredTopKpis?.T2.by_quantity" :key="item.material_code">
                    <td>
                      <span class="rank-badge" :class="item.rank <= 3 ? `rank-${item.rank}` : ''">
                        {{ item.rank }}
                      </span>
                    </td>
                    <td><code>{{ item.material_code }}</code></td>
                    <td>{{ item.material_name }}</td>
                    <td class="num">{{ item.claimed_quantity?.toLocaleString() }}</td>
                    <td class="num">{{ item.inbound_quantity?.toLocaleString() }}</td>
                    <td>{{ item.inbound_date }}</td>
                  </tr>
                </tbody>
              </table>
            </el-tab-pane>
          </el-tabs>
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
// ═══ 页面整体 ═══
.kpi-checklist-page {
  padding: 0 0 32px;
  color: #1e293b;
}

// ═══ 页面头部 ═══
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 700;
}

.page-subtitle {
  font-size: 13px;
  color: #94a3b8;
}

.status-summary {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.status-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 4px 14px;
  border-radius: 20px;
  font-weight: 500;
  &.ok      { background: #ecfdf5; color: #065f46; }
  &.warning { background: #fffbeb; color: #92400e; }
  &.alert   { background: #fef2f2; color: #991b1b; }
}

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

// ═══ 概览卡片行 ═══
.overview-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.overview-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-top: 3px solid #3b82f6;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  transition: transform 0.15s;

  &:hover {
    transform: translateY(-2px);
  }
}

.overview-card__icon {
  font-size: 32px;
}

.overview-card__label {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.overview-card__value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.overview-card__unit {
  font-size: 13px;
  font-weight: 400;
  color: #94a3b8;
  margin-left: 2px;
}

// ═══ Section 分组 ═══
.section {
  margin-bottom: 28px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-badge {
  display: inline-block;
  padding: 2px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;

  &.core       { background: #3b82f6; }
  &.constraint { background: #f59e0b; }
  &.structure  { background: #8b5cf6; }
  &.top        { background: #10b981; }
}

.section-title {
  font-size: 17px;
  font-weight: 600;
}

.section-desc {
  font-size: 12px;
  color: #94a3b8;
}

// ═══ KPI 卡片网格 ═══
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;

  &--3col {
    grid-template-columns: repeat(3, 1fr);
  }

  &--2col {
    grid-template-columns: repeat(2, 1fr);
  }
}

// ═══ KPI 卡片 ═══
.kpi-card {
  background: #fff;
  border-radius: 10px;
  border-left: 4px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  overflow: hidden;

  &--ok      { border-left-color: #10b981; }
  &--warning { border-left-color: #f59e0b; }
  &--alert   { border-left-color: #f43f5e; }
  &--info    { border-left-color: #3b82f6; }
}

.kpi-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px 0;
}

.kpi-card__key {
  display: inline-block;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 3px;
}

.kpi-card__name {
  font-size: 14px;
  font-weight: 600;
  flex: 1;
}

.kpi-card__status {
  font-size: 13px;
  font-weight: 500;
}

.kpi-card__body {
  padding: 12px 20px 18px;
}

.kpi-card__value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}

.kpi-card__value {
  font-size: 32px;
  font-weight: 800;
  line-height: 1;
}

.kpi-card__unit {
  font-size: 14px;
  color: #94a3b8;
}

.kpi-card__formula,
.kpi-card__target {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;

  .label {
    color: #94a3b8;
  }
}

// 详情行
.kpi-card__detail,
.kpi-card__detail-grid {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
}

.kpi-card__detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 24px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 3px 0;
  color: #475569;
}

// ═══ 迷你表格 ═══
.kpi-card__table-wrap {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;

  th, td {
    padding: 5px 8px;
    text-align: left;
    border-bottom: 1px solid #f1f5f9;
  }

  th {
    color: #94a3b8;
    font-weight: 500;
    font-size: 11px;
  }
}

.table-more {
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
  padding: 6px;
}

.proj-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}

// ═══ 结构分析网格 ═══
.structure-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.structure-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.structure-col__title {
  margin: 0 0 12px;
  font-size: 14px;
  color: #475569;
}

.ratio-bar {
  display: flex;
  align-items: center;
  gap: 8px;

  &__fill {
    height: 6px;
    border-radius: 3px;
  }

  span {
    font-size: 12px;
    color: #64748b;
  }
}

// ═══ 时间指标卡片 ═══
.time-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.time-metric-card {
  text-align: center;
  padding: 16px;
  background: #f8fafc;
  border-radius: 10px;

  &__value {
    font-size: 28px;
    font-weight: 700;
    color: #3b82f6;
  }

  &__label {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 4px;
  }
}

// 库龄分段条
.age-bar-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.age-bar {
  display: flex;
  align-items: center;
  gap: 12px;

  &__label {
    width: 70px;
    font-size: 12px;
    color: #64748b;
    text-align: right;
  }

  &__track {
    flex: 1;
    height: 22px;
    background: #f1f5f9;
    border-radius: 4px;
    overflow: hidden;
  }

  &__fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
    min-width: 2px;
  }

  &__pct {
    width: 50px;
    font-size: 13px;
    font-weight: 600;
    color: #334155;
  }
}

// ═══ 数据表格 ═══
.kpi-table-wrap {
  max-height: 520px;
  overflow-y: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th {
    background: #f8fafc;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    color: #64748b;
    font-size: 12px;
    position: sticky;
    top: 0;
    z-index: 1;
    border-bottom: 2px solid #e2e8f0;
  }

  td {
    padding: 9px 12px;
    border-bottom: 1px solid #f1f5f9;
    color: #334155;
  }

  tbody tr:hover {
    background: #f8fafc;
  }

  .num {
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  code {
    font-size: 11px;
    background: #f1f5f9;
    padding: 2px 5px;
    border-radius: 3px;
  }
}

.row-alert {
  background: #fef2f2;
}

// 排名徽章
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  background: #f1f5f9;
  color: #64748b;

  &.rank-1 { background: #fef3c7; color: #b45309; }
  &.rank-2 { background: #e2e8f0; color: #475569; }
  &.rank-3 { background: #fed7aa; color: #9a3412; }
}

// 领用率标签
.rate-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

// ═══ 响应式 ═══
@media (max-width: 1200px) {
  .overview-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .kpi-grid {
    grid-template-columns: 1fr;
  }
  .structure-grid {
    grid-template-columns: 1fr;
  }
  .time-metrics {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .overview-row {
    grid-template-columns: 1fr;
  }
  .time-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
