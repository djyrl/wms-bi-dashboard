<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { getInventoryReport } from '@/api/modules/inventoryReport'
import type { InventoryReportRow, InventoryReportSummary } from '@/api/modules/inventoryReport'
import { formatDays } from '@/utils/format'

// ---- 状态 ----
const loading = ref(false)
const rows = ref<InventoryReportRow[]>([])
const total = ref(0)
const summary = ref<InventoryReportSummary>({ total_inbound: 0, total_claimed: 0, total_inventory: 0 })

const sortParams = reactive({
  sort_by: 'inventory_amount',
  sort_order: 'desc' as 'asc' | 'desc',
})

const pageParams = reactive({
  page: 1,
  page_size: 50,
})

// ---- 加载数据 ----
async function loadData() {
  loading.value = true
  try {
    const res = await getInventoryReport({
      sort_by: sortParams.sort_by,
      sort_order: sortParams.sort_order,
      limit: pageParams.page_size,
      offset: (pageParams.page - 1) * pageParams.page_size,
    })
    rows.value = res.rows
    total.value = res.total
    summary.value = res.summary
  } finally {
    loading.value = false
  }
}

// ---- 切换排序 ----
function onSortChange({ prop, order }: { prop: string | null; order: string | null }) {
  if (!prop || !order) return
  sortParams.sort_by = prop
  sortParams.sort_order = order === 'ascending' ? 'asc' : 'desc'
  pageParams.page = 1
  loadData()
}

// ---- 分页 ----
function onPageChange(page: number) {
  pageParams.page = page
  loadData()
}
function onSizeChange(size: number) {
  pageParams.page_size = size
  pageParams.page = 1
  loadData()
}

// ---- 格式化 ----
function fmtWan(v: number) {
  return (v / 10000).toFixed(2) + '万'
}
function fmtRate(v: number) {
  return v.toFixed(1) + '%'
}

// ---- 领用率颜色 ----
function rateColor(rate: number) {
  if (rate >= 80) return 'success'
  if (rate >= 50) return 'warning'
  return 'danger'
}

// ---- 库龄预警 ----
function ageClass(days: number) {
  if (days > 365) return 'age-warn'
  return ''
}

const indexMethod = (idx: number) => (pageParams.page - 1) * pageParams.page_size + idx + 1

onMounted(loadData)
</script>

<template>
  <div class="report-page">
    <div class="page-header">
      <h2>批次追溯表</h2>
      <span class="page-desc">按批次维度展示入库 / 领用 / 库存明细，点击列头排序</span>
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
      height="calc(100vh - 200px)"
      style="width: 100%"
      @sort-change="onSortChange"
      :default-sort="{ prop: 'inventory_amount', order: 'descending' }"
    >
      <el-table-column type="index" :index="indexMethod" label="序号" width="60" fixed />
      <el-table-column prop="purchase_batch" label="采购批次" width="160" fixed />
      <el-table-column prop="material_name" label="物资名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="project_name" label="项目标识" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.project_name || row.project_code || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="purchaser_name" label="采购人" width="100" />
      <el-table-column prop="inbound_date" label="入库日期" width="120" sortable="custom" />
      <el-table-column prop="inbound_amount" label="入库金额" width="130" sortable="custom">
        <template #default="{ row }">
          {{ fmtWan(row.inbound_amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="claimed_amount" label="领用金额" width="130" sortable="custom">
        <template #default="{ row }">
          {{ fmtWan(row.claimed_amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="inventory_amount" label="库存金额" width="130" sortable="custom">
        <template #default="{ row }">
          <strong>{{ fmtWan(row.inventory_amount) }}</strong>
        </template>
      </el-table-column>
      <el-table-column prop="claim_rate" label="领用率" width="160" sortable="custom">
        <template #default="{ row }">
          <div class="rate-cell">
            <el-progress
              :percentage="Math.min(row.claim_rate, 100)"
              :color="rateColor(row.claim_rate) === 'success' ? '#67c23a' : rateColor(row.claim_rate) === 'warning' ? '#e6a23c' : '#f56c6c'"
              :stroke-width="14"
            />
            <span class="rate-text">{{ fmtRate(row.claim_rate) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="age_days" label="库龄(天)" width="110" sortable="custom">
        <template #default="{ row }">
          <span :class="ageClass(row.age_days)">{{ formatDays(row.age_days) }}</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="pageParams.page"
        v-model:page-size="pageParams.page_size"
        :page-sizes="[30, 50, 100, 200]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.report-page {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
  h2 {
    margin: 0 0 6px 0;
    font-size: 20px;
  }
  .page-desc {
    color: #909399;
    font-size: 13px;
  }
}

.rate-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  .el-progress {
    flex: 1;
  }
  .rate-text {
    width: 48px;
    text-align: right;
    font-size: 13px;
    color: #606266;
  }
}

.age-warn {
  color: #f56c6c;
  font-weight: 600;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding-bottom: 16px;
}

.kpi-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: border-color 0.3s;
  &:hover { border-color: rgba(59, 130, 246, 0.3); }
}

.kpi-icon {
  width: 50px; height: 50px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; flex-shrink: 0;
  &.t1 { background: rgba(59, 130, 246, 0.12); }
  &.t2 { background: rgba(245, 158, 11, 0.12); }
  &.t3 { background: rgba(139, 92, 246, 0.12); }
}

.kpi-info { flex: 1; min-width: 0; }
.kpi-label { font-size: 11px; color: #94a3b8; letter-spacing: 0.5px; }
.kpi-value { font-size: 26px; font-weight: 800; font-family: 'SF Mono', 'Fira Code', monospace; line-height: 1.2; }
.kpi-unit { font-size: 14px; font-weight: 500; }
</style>
