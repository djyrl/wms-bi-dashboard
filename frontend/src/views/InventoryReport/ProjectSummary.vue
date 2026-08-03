<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { getProjectSummary } from '@/api/modules/inventoryReport'
import type { ProjectSummaryRow } from '@/api/modules/inventoryReport'
import { formatDays } from '@/utils/format'

// ---- 状态 ----
const loading = ref(false)
const rows = ref<ProjectSummaryRow[]>([])

const sortParams = reactive({
  sort_by: 'inventory_amount',
  sort_order: 'desc' as 'asc' | 'desc',
})

// ---- KPI 汇总 ----
const summary = computed(() => ({
  total_inbound: rows.value.reduce((s, r) => s + r.inbound_amount, 0),
  total_claimed: rows.value.reduce((s, r) => s + r.claimed_amount, 0),
  total_inventory: rows.value.reduce((s, r) => s + r.inventory_amount, 0),
}))

// ---- 加载 ----
async function loadData() {
  loading.value = true
  try {
    const res = await getProjectSummary({
      sort_by: sortParams.sort_by,
      sort_order: sortParams.sort_order,
    })
    rows.value = res.rows
  } finally {
    loading.value = false
  }
}

// ---- 排序 ----
function onSortChange({ prop, order }: { prop: string | null; order: string | null }) {
  if (!prop || !order) return
  sortParams.sort_by = prop
  sortParams.sort_order = order === 'ascending' ? 'asc' : 'desc'
  loadData()
}

// ---- 格式化 ----
function fmtWan(v: number) { return (v / 10000).toFixed(2) + '万' }
function fmtRate(v: number | null) { return v != null ? v.toFixed(1) + '%' : '-' }
function fmtDays(v: number) { return v != null ? formatDays(v) : '-' }
function rateColor(rate: number) {
  if (rate >= 80) return 'success'
  if (rate >= 50) return 'warning'
  return 'danger'
}

const indexMethod = (idx: number) => idx + 1

onMounted(loadData)
</script>

<template>
  <div class="report-page">
    <div class="page-header">
      <h2>📊 项目库存追溯汇总表</h2>
      <span class="page-desc">按项目维度汇总入库/领用/库存/领用率/平均库龄，点击列头排序</span>
    </div>

    <!-- KPI 汇总 -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-icon t1">📦</div>
        <div class="kpi-info">
          <div class="kpi-label">入库金额汇总</div>
          <div class="kpi-value" style="color: #3b82f6">{{ fmtWan(summary.total_inbound) }}<span class="kpi-unit">万元</span></div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon t2">📤</div>
        <div class="kpi-info">
          <div class="kpi-label">领用金额汇总</div>
          <div class="kpi-value" style="color: #f59e0b">{{ fmtWan(summary.total_claimed) }}<span class="kpi-unit">万元</span></div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon t3">🏗️</div>
        <div class="kpi-info">
          <div class="kpi-label">库存金额汇总</div>
          <div class="kpi-value" style="color: #8b5cf6">{{ fmtWan(summary.total_inventory) }}<span class="kpi-unit">万元</span></div>
        </div>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      stripe
      height="calc(100vh - 280px)"
      style="width: 100%"
      @sort-change="onSortChange"
      :default-sort="{ prop: 'inventory_amount', order: 'descending' }"
    >
      <el-table-column type="index" :index="indexMethod" label="序号" width="60" fixed />
      <el-table-column prop="project_name" label="项目" min-width="220" fixed show-overflow-tooltip>
        <template #default="{ row }">
          <strong>{{ row.project_name }}</strong>
        </template>
      </el-table-column>
      <el-table-column prop="project_code" label="项目编号" width="180" show-overflow-tooltip />
      <el-table-column prop="inbound_amount" label="入库金额" width="140" sortable="custom">
        <template #default="{ row }">
          {{ fmtWan(row.inbound_amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="claimed_amount" label="领用金额" width="140" sortable="custom">
        <template #default="{ row }">
          {{ fmtWan(row.claimed_amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="inventory_amount" label="库存金额" width="140" sortable="custom">
        <template #default="{ row }">
          <strong>{{ fmtWan(row.inventory_amount) }}</strong>
        </template>
      </el-table-column>
      <el-table-column prop="claim_rate" label="领用率" width="180" sortable="custom">
        <template #default="{ row }">
          <div class="rate-cell">
            <template v-if="row.claim_rate != null">
              <el-progress
                :percentage="Math.min(row.claim_rate, 100)"
                :color="rateColor(row.claim_rate) === 'success' ? '#67c23a' : rateColor(row.claim_rate) === 'warning' ? '#e6a23c' : '#f56c6c'"
                :stroke-width="16"
              />
              <span class="rate-text">{{ fmtRate(row.claim_rate) }}</span>
            </template>
            <span v-else class="rate-text" style="color:#c0c4cc">-</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="avg_age_days" label="平均库龄" width="120" sortable="custom">
        <template #default="{ row }">
          {{ fmtDays(row.avg_age_days) }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style lang="scss" scoped>
.report-page { background: #fff; border-radius: 8px; padding: 20px; }
.page-header { margin-bottom: 20px; h2 { margin: 0 0 6px 0; font-size: 20px; } .page-desc { color: #909399; font-size: 13px; } }
.rate-cell { display: flex; align-items: center; gap: 8px; .el-progress { flex: 1; } .rate-text { width: 48px; text-align: right; font-size: 13px; color: #606266; } }
.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding-bottom: 16px; }
.kpi-card { background: var(--el-bg-color-overlay); border: 1px solid var(--el-border-color-light); border-radius: 10px; padding: 20px 22px; display: flex; align-items: center; gap: 14px; }
.kpi-icon { width: 50px; height: 50px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; &.t1 { background: #eff6ff; } &.t2 { background: #fffbeb; } &.t3 { background: #f5f3ff; } }
.kpi-label { font-size: 14px; color: #909399; }
.kpi-value { font-size: 24px; font-weight: 700; .kpi-unit { font-size: 13px; font-weight: 400; color: #909399; margin-left: 4px; } }
</style>
