<script setup lang="ts">
import { computed } from 'vue'
import { useDashboardStore } from '@/stores/modules/dashboard'
import { storeToRefs } from 'pinia'
import { formatAmount, formatNumber, formatDays } from '@/utils/format'
import type { ProcurementBatch } from '@/types/dashboard'

const store = useDashboardStore()
const { topTab, topUnclaimedAmount, topUnclaimedQuantity, topClaimedAmount, topClaimedQuantity } = storeToRefs(store)

const currentData = computed<ProcurementBatch[]>(() => {
  switch (topTab.value) {
    case 'unclaimed-amount': return topUnclaimedAmount.value
    case 'unclaimed-quantity': return topUnclaimedQuantity.value
    case 'claimed-amount': return topClaimedAmount.value
    case 'claimed-quantity': return topClaimedQuantity.value
    default: return []
  }
})

const currentTab = computed({
  get: () => topTab.value,
  set: (v) => store.switchTopTab(v),
})

const isUnclaimed = computed(() => topTab.value.startsWith('unclaimed'))
const isAmount = computed(() => topTab.value.endsWith('amount'))
</script>

<template>
  <el-card class="top-panel" shadow="hover">
    <template #header>
      <div class="card-header">
        <span>TOP 10 排行</span>
        <el-radio-group v-model="currentTab" size="small">
          <el-radio-button value="unclaimed-amount">未领用金额</el-radio-button>
          <el-radio-button value="unclaimed-quantity">未领用数量</el-radio-button>
          <el-radio-button value="claimed-amount">领用金额</el-radio-button>
          <el-radio-button value="claimed-quantity">领用数量</el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <el-table :data="currentData" stripe max-height="400">
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="batch_no" label="批次号" width="140" />
      <el-table-column label="物资" min-width="120">
        <template #default="{ row }">{{ row.material?.name }}</template>
      </el-table-column>
      <el-table-column label="项目" min-width="140">
        <template #default="{ row }">{{ row.project?.name }}</template>
      </el-table-column>
      <el-table-column label="采购人" width="80">
        <template #default="{ row }">{{ row.purchaser?.name }}</template>
      </el-table-column>
      <el-table-column v-if="isAmount" label="金额" align="right" width="120" sortable>
        <template #default="{ row }">
          <strong>{{ formatAmount(isUnclaimed ? row.inventory_amount : row.claimed_amount) }}</strong>
        </template>
      </el-table-column>
      <el-table-column v-else label="数量" align="right" width="100" sortable>
        <template #default="{ row }">
          {{ formatNumber(isUnclaimed ? row.inventory_quantity : row.claimed_quantity) }}
        </template>
      </el-table-column>
      <el-table-column label="库龄" align="right" width="80">
        <template #default="{ row }">{{ formatDays(row.inventory_age_days) }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
