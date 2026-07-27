<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getSourceStructure } from '@/api/modules/inventoryReport'
import type { SourceStructureRow } from '@/api/modules/inventoryReport'

const loading = ref(false)
const rows = ref<SourceStructureRow[]>([])
const totalAmount = ref(0)

const summary = computed(() => ({
  total_inventory: rows.value.reduce((s, r) => s + r.inventory_amount, 0),
}))

async function loadData() {
  loading.value = true
  try {
    const res = await getSourceStructure()
    rows.value = res.rows
    totalAmount.value = res.total_amount
  } finally {
    loading.value = false
  }
}

function fmtWan(v: number) { return (v / 10000).toFixed(2) + '万' }
function fmtRatio(v: number) { return v.toFixed(1) + '%' }

const indexMethod = (idx: number) => idx + 1

onMounted(loadData)
</script>

<template>
  <div class="report-page">
    <div class="page-header">
      <h2>🏗️ 库存来源结构表</h2>
      <span class="page-desc">按项目归属分析库存金额构成</span>
    </div>

    <!-- KPI 汇总 -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-icon t3">🏗️</div>
        <div class="kpi-info">
          <div class="kpi-label">库存金额汇总</div>
          <div class="kpi-value" style="color: #8b5cf6">{{ fmtWan(summary.total_inventory) }}<span class="kpi-unit">万元</span></div>
        </div>
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" stripe height="calc(100vh - 280px)"
      style="width: 100%" :default-sort="{ prop: 'inventory_amount', order: 'descending' }">
      <el-table-column type="index" :index="indexMethod" label="序号" width="60" fixed />
      <el-table-column prop="source_name" label="来源（项目）" min-width="300" show-overflow-tooltip>
        <template #default="{ row }"><strong>{{ row.source_name }}</strong></template>
      </el-table-column>
      <el-table-column prop="inventory_amount" label="库存金额" width="180" sortable>
        <template #default="{ row }">{{ fmtWan(row.inventory_amount) }}</template>
      </el-table-column>
      <el-table-column prop="ratio" label="金额占比" width="180">
        <template #default="{ row }">
          <div class="ratio-cell">
            <el-progress :percentage="Math.min(row.ratio, 100)" :stroke-width="18"
              :color="row.ratio > 10 ? '#f56c6c' : row.ratio > 5 ? '#e6a23c' : '#67c23a'" />
            <span class="ratio-text">{{ fmtRatio(row.ratio) }}</span>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style lang="scss" scoped>
.report-page { background: #fff; border-radius: 8px; padding: 20px; }
.page-header { margin-bottom: 20px; h2 { margin: 0 0 6px 0; font-size: 20px; } .page-desc { color: #909399; font-size: 13px; } }
.ratio-cell { display: flex; align-items: center; gap: 8px; .el-progress { flex: 1; } .ratio-text { width: 52px; text-align: right; font-size: 13px; color: #606266; } }
.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding-bottom: 16px; }
.kpi-card { background: var(--el-bg-color-overlay); border: 1px solid var(--el-border-color-light); border-radius: 10px; padding: 20px 22px; display: flex; align-items: center; gap: 14px; }
.kpi-icon { width: 50px; height: 50px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; &.t1 { background: #eff6ff; } &.t2 { background: #fffbeb; } &.t3 { background: #f5f3ff; } }
.kpi-label { font-size: 14px; color: #909399; }
.kpi-value { font-size: 24px; font-weight: 700; .kpi-unit { font-size: 13px; font-weight: 400; color: #909399; margin-left: 4px; } }
</style>
