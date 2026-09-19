<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getInventoryWideReport } from '@/api/modules/dataTable'
import type { InventoryWideRow, InventoryWideSummary } from '@/api/modules/dataTable'
import ErrorResult from '@/components/common/ErrorResult.vue'
import { formatDays, formatAmount } from '@/utils/format'
import { filterExcluded } from '@/utils/excludeMaterials'
import { exportCsv, exportExcel, type ExportHeader } from '@/utils/exportData'

const loading = ref(false)
const error = ref<string | null>(null)
const exporting = ref(false)
const rows = ref<InventoryWideRow[]>([])
const total = ref(0)
const summary = ref<InventoryWideSummary | null>(null)
const pageSize = ref(50)
const currentPage = ref(1)
const sortBy = ref('inventory_amount')
const sortOrder = ref('desc')
const filters = ref<Record<string, string>>({})

// ================================================================
// 全部列定义（37 列）—— 默认只显示核心 14 列，其余可在「列管理」勾选
// ================================================================
const allColumns = ref([
  // —— WMS 标识 / 维度 ——
  { key: 'material_code', label: '物料编码', visible: true, width: 110 },
  { key: 'material_name', label: '物料名称', visible: true, width: 180 },
  { key: 'material_group_code', label: '物料类别', visible: false, width: 110 },
  { key: 'batch_code', label: '批次', visible: true, width: 120 },
  { key: 'purchase_batch', label: '采购批次', visible: false, width: 120 },
  { key: 'project_code', label: '项目编码', visible: true, width: 140 },
  { key: 'project_name', label: '项目名称', visible: true, width: 200 },
  { key: 'project_type', label: '项目类型', visible: true, width: 110 },
  { key: 'owner_project_type', label: '项目类型(台账)', visible: false, width: 120 },
  { key: 'purchaser_name', label: '采购人', visible: true, width: 100 },
  { key: 'submitter_name', label: '提报人', visible: false, width: 100 },
  { key: 'contact_name', label: '联系人(项目负责人)', visible: false, width: 140 },
  { key: 'inbound_date', label: '入库日期', visible: true, width: 100 },
  { key: 'putaway_date', label: '上架日期', visible: false, width: 100 },

  // —— 数量 ——
  { key: 'original_quantity', label: '原始数量', visible: true, width: 100 },
  { key: 'current_quantity', label: '当前数量', visible: true, width: 100 },
  { key: 'used_quantity', label: '已用数量', visible: false, width: 100 },
  { key: 'pick_quantity', label: '领用数量', visible: false, width: 100 },
  { key: 'repair_quantity', label: '维修数量', visible: false, width: 100 },
  { key: 'scrap_quantity', label: '报废数量', visible: false, width: 100 },
  { key: 'repaired_quantity', label: '修复数量', visible: false, width: 100 },

  // —— 单价 / 单位 / 供应商 ——
  { key: 'unit_price', label: '单价', visible: true, width: 110 },
  { key: 'unit', label: '单位', visible: false, width: 80 },
  { key: 'supplier_code', label: '供应商', visible: false, width: 100 },

  // —— WMS 金额（项目分摊后）+ 分摊因子 ——
  { key: 'inbound_amount', label: '入库金额', visible: true, width: 130 },
  { key: 'claimed_amount', label: '领用金额', visible: true, width: 130 },
  { key: 'inventory_amount', label: '库存金额', visible: true, width: 130 },
  { key: 'project_ratio', label: '项目分摊因子', visible: false, width: 120 },

  // —— 领用率 / 库龄 ——
  { key: 'claim_rate', label: '领用率(%)', visible: false, width: 100 },
  { key: 'age_days', label: '库龄(天)', visible: false, width: 100 },

  // —— ERP 金额（批次级，元）——
  { key: 'erp_recv_all', label: '全部收货金额', visible: false, width: 130 },
  { key: 'erp_reversal_all', label: '全部冲销金额', visible: false, width: 130 },
  { key: 'erp_net_in_all', label: '全部净入库金额', visible: false, width: 140 },
  { key: 'erp_out_all', label: '全部出库金额', visible: false, width: 130 },
  { key: 'erp_recv_year', label: '当年收货金额', visible: false, width: 130 },
  { key: 'erp_reversal_year', label: '当年冲销金额', visible: false, width: 130 },
  { key: 'erp_net_in_year', label: '当年净入库金额', visible: false, width: 140 },
  { key: 'erp_out_year', label: '当年出库金额', visible: false, width: 130 },

  // —— 最佳估计库存 ——
  { key: 'best_inventory_amt', label: '最佳估计库存', visible: false, width: 140 },
])

const visibleColumns = computed(() => allColumns.value.filter(c => c.visible))

// 数值列右对齐 + 特殊格式化
const AMOUNT_KEYS = new Set([
  'unit_price', 'inbound_amount', 'claimed_amount', 'inventory_amount',
  'erp_recv_all', 'erp_reversal_all', 'erp_net_in_all', 'erp_out_all',
  'erp_recv_year', 'erp_reversal_year', 'erp_net_in_year', 'erp_out_year',
  'best_inventory_amt',
])
const QTY_KEYS = new Set([
  'original_quantity', 'current_quantity', 'used_quantity',
  'pick_quantity', 'repair_quantity', 'scrap_quantity', 'repaired_quantity',
])

function isNumericKey(key: string) {
  return AMOUNT_KEYS.has(key) || QTY_KEYS.has(key) || key === 'project_ratio' || key === 'claim_rate' || key === 'age_days'
}

function formatCell(key: string, v: unknown): string {
  if (v == null || v === '') return ''
  if (key === 'age_days') return formatDays(Number(v))
  if (key === 'project_ratio') return Number(v).toFixed(4)
  if (AMOUNT_KEYS.has(key)) return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (QTY_KEYS.has(key)) return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
  return String(v)
}

// ================================================================
// 列管理（复用 DataTable 的列选择逻辑）
// ================================================================
const columnPreview = ref<{ key: string; label: string; checked: boolean }[]>([])
const columnPickerVisible = ref(false)

function openColumnPicker() {
  columnPreview.value = allColumns.value.map(c => ({ key: c.key, label: c.label, checked: c.visible }))
}

function confirmColumns() {
  for (const p of columnPreview.value) {
    const col = allColumns.value.find(c => c.key === p.key)
    if (col) col.visible = p.checked
  }
  ;(document.activeElement as HTMLElement)?.blur()
}

function applyColumns() {
  confirmColumns()
  columnPickerVisible.value = false
}

// ================================================================
// 数据加载 / 排序 / 分页 / 导出
// ================================================================
async function loadData() {
  loading.value = true
  error.value = null
  try {
    const res = await getInventoryWideReport({
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    })
    rows.value = filterExcluded(res.rows)
    total.value = res.total
    summary.value = res.summary
  } catch (e: any) {
    error.value = e.message || '加载失败'
  }
  loading.value = false
}

async function handleExport(format: 'csv' | 'excel') {
  exporting.value = true
  try {
    const headers: ExportHeader[] = visibleColumns.value.map((c) => ({ key: c.key, label: c.label }))
    const res = await getInventoryWideReport({ sort_by: sortBy.value, sort_order: sortOrder.value, limit: 10000, offset: 0 })
    const rowsData = filterExcluded(res.rows) as unknown as Record<string, unknown>[]
    const filename = '明细宽表(WMS-ERP)'
    if (format === 'csv') {
      exportCsv(headers, rowsData, `${filename}.csv`)
    } else {
      exportExcel(headers, rowsData, `${filename}.xlsx`)
    }
    ElMessage.success(`已导出 ${rowsData.length} 条记录`)
  } catch (e: any) {
    ElMessage.error(e.message || '导出失败')
  }
  exporting.value = false
}

function onSortChange({ prop, order }: { prop: string | null; order: string | null }) {
  if (!prop) return
  sortBy.value = prop
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  loadData()
}

function onPageChange(page: number) {
  currentPage.value = page
  loadData()
}

// 客户端筛选（作用于当前页，与 DataTable 一致）
const filteredRows = computed(() => {
  const activeFilters = Object.entries(filters.value).filter(([, v]) => v)
  if (!activeFilters.length) return rows.value
  return rows.value.filter(row =>
    activeFilters.every(([key, val]) => {
      const cell = String(row[key as keyof InventoryWideRow] ?? '').toLowerCase()
      return cell.includes(val.toLowerCase())
    })
  )
})

onMounted(() => loadData())
</script>

<template>
  <div v-loading="loading" class="data-wide-page">
    <ErrorResult v-if="error" :message="error" @retry="loadData" />

    <template v-if="!error">
      <!-- 汇总条 -->
      <div v-if="summary" class="summary-strip">
        <div class="summary-item"><span>WMS 入库</span><b>{{ formatAmount(summary.total_inbound) }}</b></div>
        <div class="summary-item"><span>WMS 领用</span><b>{{ formatAmount(summary.total_claimed) }}</b></div>
        <div class="summary-item"><span>WMS 库存</span><b>{{ formatAmount(summary.total_inventory) }}</b></div>
        <div class="summary-item erp"><span>ERP 收货(全部)</span><b>{{ formatAmount(summary.erp_recv_all) }}</b></div>
        <div class="summary-item erp"><span>ERP 出库(全部)</span><b>{{ formatAmount(summary.erp_out_all) }}</b></div>
        <div class="summary-item erp"><span>ERP 净入库(当年)</span><b>{{ formatAmount(summary.erp_net_in_year) }}</b></div>
        <div class="summary-item best"><span>最佳估计库存</span><b>{{ formatAmount(summary.best_inventory_total) }}</b></div>
      </div>

      <!-- 列管理 -->
      <div class="toolbar">
        明细宽表（WMS × ERP 批次级联）
        <span class="total-info">共 {{ total }} 条</span>
        <div class="toolbar-right">
          <el-dropdown @command="handleExport">
            <el-button size="small" :loading="exporting">
              导出 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
                <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-popover :visible="columnPickerVisible" trigger="click" :width="460" @show="openColumnPicker">
            <template #reference>
              <el-button size="small" @click="columnPickerVisible = true">列管理</el-button>
            </template>
            <div class="column-grid">
              <el-checkbox v-for="col in columnPreview" :key="col.key" v-model="col.checked" size="small">{{ col.label }}</el-checkbox>
            </div>
            <div style="margin-top:6px;display:flex;gap:6px">
              <el-button size="small" text @click="columnPreview.forEach(c => c.checked = true)">全选</el-button>
              <el-button size="small" text @click="columnPreview.forEach(c => c.checked = false)">全取消</el-button>
            </div>
            <div style="margin-top:6px;display:flex;justify-content:space-between">
              <el-button size="small" @click="columnPickerVisible = false">取消</el-button>
              <el-button size="small" type="primary" @click="applyColumns">确认</el-button>
            </div>
          </el-popover>
        </div>
      </div>

      <!-- 表格 -->
      <el-table
        :data="filteredRows"
        stripe
        border
        size="small"
        max-height="calc(100vh - 260px)"
        @sort-change="onSortChange"
        :default-sort="{ prop: 'inventory_amount', order: 'descending' }"
      >
        <el-table-column type="index" label="#" width="50" fixed />
        <el-table-column
          v-for="col in visibleColumns"
          :key="col.key"
          :prop="col.key"
          :label="col.label"
          :width="col.width"
          :align="isNumericKey(col.key) ? 'right' : 'left'"
          sortable="custom"
          show-overflow-tooltip
        >
          <template #header>
            <div>
              {{ col.label }}
              <el-input
                v-model="filters[col.key]"
                size="small"
                placeholder="筛选"
                clearable
                style="margin-top:4px"
                @click.stop
              />
            </div>
          </template>
          <template #default="{ row }">
            <span :style="col.key === 'inventory_amount' && row[col.key] > 0 ? 'color:#f43f5e;font-weight:600' : ''">
              {{ formatCell(col.key, row[col.key]) }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          :page-sizes="[20, 50, 100, 500]"
          @current-change="onPageChange"
          @size-change="loadData"
        />
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.data-wide-page { padding: 0 0 24px; }
.summary-strip {
  display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; justify-content: center;
  .summary-item {
    display: flex; flex-direction: column; gap: 2px;
    padding: 6px 12px; border-radius: 6px; background: #f8fafc; border: 1px solid #e2e8f0;
    span { font-size: 12px; color: #64748b; }
    b { font-size: 15px; color: #0f172a; font-variant-numeric: tabular-nums; }
    &.erp b { color: #2563eb; }
    &.best b { color: #f43f5e; }
  }
}
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.total-info { color: #94a3b8; font-size: 13px; }
.column-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; }
.pagination { margin-top: 16px; display: flex; justify-content: center; }
</style>
