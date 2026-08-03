<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getInventoryReport } from '@/api/modules/dataTable'
import type { InventoryRow } from '@/api/modules/dataTable'
import ErrorResult from '@/components/common/ErrorResult.vue'
import { formatDays } from '@/utils/format'
import { exportCsv, exportExcel, type ExportHeader } from '@/utils/exportData'

const loading = ref(false)
const error = ref<string | null>(null)
const exporting = ref(false)
const rows = ref<InventoryRow[]>([])
const total = ref(0)
const pageSize = ref(50)
const currentPage = ref(1)
const sortBy = ref('inventory_amount')
const sortOrder = ref('desc')
const filters = ref<Record<string, string>>({})

const allColumns = ref([
  { key: 'material_code', label: '物料编码', visible: true, width: 110 },
  { key: 'material_name', label: '物料名称', visible: true, width: 180 },
  { key: 'batch_code', label: '批次', visible: true, width: 120 },
  { key: 'project_code', label: '项目编码', visible: true, width: 140 },
  { key: 'project_name', label: '项目名称', visible: true, width: 200 },
  { key: 'project_type', label: '项目类型', visible: true, width: 110 },
  { key: 'purchaser_name', label: '采购人', visible: true, width: 100 },
  { key: 'inbound_date', label: '入库日期', visible: true, width: 100 },
  { key: 'putaway_date', label: '上架日期', visible: false, width: 100 },
  { key: 'original_quantity', label: '原始数量', visible: true, width: 100 },
  { key: 'current_quantity', label: '当前数量', visible: true, width: 100 },
  { key: 'used_quantity', label: '已用数量', visible: false, width: 100 },
  { key: 'unit_price', label: '单价', visible: true, width: 90 },
  { key: 'inbound_amount', label: '入库金额', visible: true, width: 110 },
  { key: 'claimed_amount', label: '领用金额', visible: true, width: 110 },
  { key: 'inventory_amount', label: '库存金额', visible: true, width: 110 },
  { key: 'claim_rate', label: '领用率(%)', visible: true, width: 100 },
  { key: 'age_days', label: '库龄(天)', visible: true, width: 90 },
  { key: 'unit', label: '单位', visible: false, width: 80 },
  { key: 'supplier_code', label: '供应商', visible: false, width: 100 },
  { key: 'purchase_batch', label: '采购批次', visible: false, width: 120 },
  { key: 'pick_quantity', label: '领用数量', visible: false, width: 100 },
  { key: 'repair_quantity', label: '维修数量', visible: false, width: 100 },
  { key: 'scrap_quantity', label: '报废数量', visible: false, width: 100 },
  { key: 'repaired_quantity', label: '修复数量', visible: false, width: 100 },
])

const visibleColumns = computed(() => allColumns.value.filter(c => c.visible))

const columnPreview = ref<{ key: string; label: string; checked: boolean }[]>([])
const columnPickerVisible = ref(false)

function openColumnPicker() {
  columnPreview.value = allColumns.value.map(c => ({ key: c.key, label: c.label, checked: c.visible }))
}

function confirmColumns() {
  const preview = columnPreview.value
  for (const p of preview) {
    const col = allColumns.value.find(c => c.key === p.key)
    if (col) col.visible = p.checked
  }
  ;(document.activeElement as HTMLElement)?.blur()
}

function applyColumns() {
  confirmColumns()
  columnPickerVisible.value = false
}

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const res = await getInventoryReport({
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    })
    rows.value = res.rows
    total.value = res.total
  } catch (e: any) {
    error.value = e.message || '加载失败'
  }
  loading.value = false
}

async function handleExport(format: 'csv' | 'excel') {
  exporting.value = true
  try {
    const headers: ExportHeader[] = visibleColumns.value.map((c) => ({ key: c.key, label: c.label }))
    const res = await getInventoryReport({ sort_by: sortBy.value, sort_order: sortOrder.value, limit: 10000, offset: 0 })
    const rows = res.rows as unknown as Record<string, unknown>[]
    const filename = '批次追溯明细表'
    if (format === 'csv') {
      exportCsv(headers, rows, `${filename}.csv`)
    } else {
      exportExcel(headers, rows, `${filename}.xlsx`)
    }
    ElMessage.success(`已导出 ${rows.length} 条记录`)
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

const filteredRows = computed(() => {
  const activeFilters = Object.entries(filters.value).filter(([, v]) => v)
  if (!activeFilters.length) return rows.value
  return rows.value.filter(row =>
    activeFilters.every(([key, val]) => {
      const cell = String(row[key as keyof InventoryRow] ?? '').toLowerCase()
      return cell.includes(val.toLowerCase())
    })
  )
})

onMounted(() => loadData())
</script>

<template>
  <div v-loading="loading" class="data-table-page">
    <ErrorResult v-if="error" :message="error" @retry="loadData" />

    <template v-if="!error">
      <!-- 列管理 -->
      <div class="toolbar">
        明细表（批次追溯表）
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
          <el-popover :visible="columnPickerVisible" trigger="click" :width="420" @show="openColumnPicker">
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
        max-height="calc(100vh - 180px)"
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
              {{ col.key === 'age_days' ? formatDays(row[col.key]) : row[col.key] ?? '' }}
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
.data-table-page { padding: 0 0 24px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.total-info { color: #94a3b8; font-size: 13px; }
.column-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; }
.pagination { margin-top: 16px; display: flex; justify-content: center; }
</style>
