<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/modules/dashboard'
import { storeToRefs } from 'pinia'
import { formatAmount, formatPercent, formatDays, claimRateColor } from '@/utils/format'

const router = useRouter()
const store = useDashboardStore()
const { projectIndicators, purchaserIndicators } = storeToRefs(store)

const activeTab = ref<'project' | 'purchaser'>('project')

const projectColumns = [
  { prop: 'project_name', label: '项目名称', minWidth: 160 },
  { prop: 'inbound_amount', label: '入库金额', align: 'right' as const },
  { prop: 'claimed_amount', label: '领用金额', align: 'right' as const },
  { prop: 'unclaimed_amount', label: '未消耗金额', align: 'right' as const },
  { prop: 'claim_rate', label: '领用率', align: 'right' as const },
  { prop: 'avg_age_days', label: '平均库龄', align: 'right' as const },
]

const purchaserColumns = [
  { prop: 'purchaser_name', label: '采购人', minWidth: 100 },
  { prop: 'department', label: '部门', width: 100 },
  { prop: 'inbound_amount', label: '入库金额', align: 'right' as const },
  { prop: 'claimed_amount', label: '领用金额', align: 'right' as const },
  { prop: 'unclaimed_amount', label: '未消耗金额', align: 'right' as const },
  { prop: 'claim_rate', label: '领用率', align: 'right' as const },
  { prop: 'avg_age_days', label: '平均库龄', align: 'right' as const },
]

function onProjectRowClick(row: { project_id: number }) {
  router.push(`/drill/project/${row.project_id}`)
}

function onPurchaserRowClick(row: { purchaser_id: number }) {
  router.push(`/drill/purchaser/${row.purchaser_id}`)
}
</script>

<template>
  <el-card class="dimension-panel" shadow="hover">
    <template #header>
      <div class="card-header">
        <span>维度分析</span>
        <el-radio-group v-model="activeTab" size="small">
          <el-radio-button value="project">按项目</el-radio-button>
          <el-radio-button value="purchaser">按采购人</el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <!-- 项目维度 -->
    <el-table
      v-if="activeTab === 'project'"
      :data="projectIndicators"
      stripe
      max-height="340"
      highlight-current-row
      @row-click="onProjectRowClick"
      style="cursor: pointer"
    >
      <el-table-column v-for="col in projectColumns" :key="col.prop" v-bind="col">
        <template v-if="['inbound_amount','claimed_amount','unclaimed_amount'].includes(col.prop)" #default="{ row }">
          {{ formatAmount(row[col.prop]) }}
        </template>
        <template v-else-if="col.prop === 'claim_rate'" #default="{ row }">
          <span :style="{ color: claimRateColor(row.claim_rate), fontWeight: 700 }">
            {{ formatPercent(row.claim_rate) }}
          </span>
        </template>
        <template v-else-if="col.prop === 'avg_age_days'" #default="{ row }">
          {{ formatDays(row.avg_age_days) }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 采购人维度 -->
    <el-table
      v-if="activeTab === 'purchaser'"
      :data="purchaserIndicators"
      stripe
      max-height="340"
      highlight-current-row
      @row-click="onPurchaserRowClick"
      style="cursor: pointer"
    >
      <el-table-column v-for="col in purchaserColumns" :key="col.prop" v-bind="col">
        <template v-if="['inbound_amount','claimed_amount','unclaimed_amount'].includes(col.prop)" #default="{ row }">
          {{ formatAmount(row[col.prop]) }}
        </template>
        <template v-else-if="col.prop === 'claim_rate'" #default="{ row }">
          <span :style="{ color: claimRateColor(row.claim_rate), fontWeight: 700 }">
            {{ formatPercent(row.claim_rate) }}
          </span>
        </template>
        <template v-else-if="col.prop === 'avg_age_days'" #default="{ row }">
          {{ formatDays(row.avg_age_days) }}
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
