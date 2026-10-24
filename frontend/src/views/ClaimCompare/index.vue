<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getClaimCompare } from '@/api/modules/theme1'
import type { ClaimCompareRes, ClaimCompareScope } from '@/api/modules/theme1'
import ErrorResult from '@/components/common/ErrorResult.vue'

type ScopeKey = 'flow' | 'cohort'

const loading = ref(false)
const error = ref<string | null>(null)
const scope = ref<ScopeKey>('flow')
const data = ref<ClaimCompareRes | null>(null)

const SCOPE_LABELS: Record<ScopeKey, string> = {
  flow: '发生月份口径（本月领用 ÷ 本月入库）',
  cohort: '上架月份口径（按上架月归集批次，累计领用）',
}

const current = computed<ClaimCompareScope | null>(() => {
  if (!data.value) return null
  return data.value[scope.value]
})

const yearLabel = computed(() => data.value?.year ?? '')

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await getClaimCompare()
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function fmtAmount(v: number): string {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtRate(v: number): string {
  return v.toFixed(2) + '%'
}

function rateClass(v: number): string {
  if (v > 100) return 'rate rate--over'
  if (v <= 0) return 'rate rate--zero'
  return 'rate'
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="page">
    <ErrorResult v-if="error" :message="error" @retry="load" />
    <template v-if="!error">
      <div class="head">
        <h2>领用率双口径对比 · WMS vs ERP</h2>
        <el-radio-group v-model="scope">
          <el-radio-button value="flow">发生月份</el-radio-button>
          <el-radio-button value="cohort">上架月份</el-radio-button>
        </el-radio-group>
      </div>

      <template v-if="current">
        <p class="hint">{{ SCOPE_LABELS[scope] }}（金额单位：万元）</p>

        <!-- 当年累计汇总 -->
        <div class="summary">
          <div class="summary-title">当年累计（{{ yearLabel }}-01-01 ~ 今天）</div>
          <table class="summary-table">
            <thead>
              <tr>
                <th></th>
                <th>入库(万)</th>
                <th>领用(万)</th>
                <th>领用率</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="tag tag--wms">WMS</td>
                <td>{{ fmtAmount(current.summary.wms_inbound) }}</td>
                <td>{{ fmtAmount(current.summary.wms_claimed) }}</td>
                <td :class="rateClass(current.summary.wms_rate)">{{ fmtRate(current.summary.wms_rate) }}</td>
              </tr>
              <tr>
                <td class="tag tag--erp">ERP</td>
                <td>{{ fmtAmount(current.summary.erp_inbound) }}</td>
                <td>{{ fmtAmount(current.summary.erp_claimed) }}</td>
                <td :class="rateClass(current.summary.erp_rate)">{{ fmtRate(current.summary.erp_rate) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 月度明细 -->
        <el-table :data="current.rows" border stripe size="default" class="detail">
          <el-table-column prop="month" label="月" width="100" fixed />
          <el-table-column label="WMS（系统）" align="center">
            <el-table-column label="入库(万)" align="right" width="120">
              <template #default="{ row }">{{ fmtAmount(row.wms_inbound) }}</template>
            </el-table-column>
            <el-table-column label="领用(万)" align="right" width="120">
              <template #default="{ row }">{{ fmtAmount(row.wms_claimed) }}</template>
            </el-table-column>
            <el-table-column label="领用率" align="right" width="110">
              <template #default="{ row }"><span :class="rateClass(row.wms_rate)">{{ fmtRate(row.wms_rate) }}</span></template>
            </el-table-column>
          </el-table-column>
          <el-table-column label="ERP" align="center">
            <el-table-column label="入库(万)" align="right" width="120">
              <template #default="{ row }">{{ fmtAmount(row.erp_inbound) }}</template>
            </el-table-column>
            <el-table-column label="领用(万)" align="right" width="120">
              <template #default="{ row }">{{ fmtAmount(row.erp_claimed) }}</template>
            </el-table-column>
            <el-table-column label="领用率" align="right" width="110">
              <template #default="{ row }"><span :class="rateClass(row.erp_rate)">{{ fmtRate(row.erp_rate) }}</span></template>
            </el-table-column>
          </el-table-column>
        </el-table>

        <p class="note">
          说明：上架月份口径仅覆盖当前仍在库的批次，早期已领空的批次不计入，故月份覆盖较窄（如 2026 年只到 6–10 月）；
          发生月份口径覆盖全部出入库流水。当月领用率可超过 100%，表示当月领用的货物有一部分来自前几月入库。
        </p>
      </template>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0 0 24px; }
h2 { font-size: 20px; margin: 0; }
.head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 8px; flex-wrap: wrap; }
.hint { color: #64748b; font-size: 13px; margin: 0 0 12px; }

.summary { margin-bottom: 16px; }
.summary-title { font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 8px; }
.summary-table { width: 100%; max-width: 520px; border-collapse: collapse; font-size: 13px; }
.summary-table th, .summary-table td { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: right; }
.summary-table th { background: #f1f5f9; color: #475569; font-weight: 600; }
.summary-table td:first-child { text-align: left; }
.tag { font-weight: 700; }
.tag--wms { color: #2563eb; }
.tag--erp { color: #16a34a; }

.detail { width: 100%; }
.rate { font-weight: 600; color: #475569; }
.rate--over { color: #dc2626; }
.rate--zero { color: #94a3b8; }

.note { color: #94a3b8; font-size: 12px; line-height: 1.6; margin-top: 12px; }
</style>
