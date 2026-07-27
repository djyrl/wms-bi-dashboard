<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { drillBatches } from '@/api/modules/dashboard'
import { formatAmount, formatDays, formatPercent } from '@/utils/format'
import type { ProcurementBatch } from '@/types/dashboard'

const route = useRoute()
const router = useRouter()

const dimension = (route.params.dimension as string) || 'project'
const id = Number(route.params.id)

const loading = ref(false)
const batches = ref<ProcurementBatch[]>([])
const dimensionName = ref('')

// 聚合统计
const stats = ref({ total: 0, claimed: 0, unclaimed: 0, claimRate: 0, avgAge: 0 })

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, number> = {}
    if (dimension === 'project') params.project_id = id
    else if (dimension === 'purchaser') params.purchaser_id = id
    else if (dimension === 'material') params.material_id = id

    const result = await drillBatches(params)
    batches.value = result

    if (result.length) {
      dimensionName.value = dimension === 'project'
        ? result[0].project?.name || ''
        : dimension === 'purchaser'
          ? result[0].purchaser?.name || ''
          : result[0].material?.name || ''

      stats.value.total = result.reduce((s, b) => s + b.inbound_amount, 0)
      stats.value.claimed = result.reduce((s, b) => s + b.claimed_amount, 0)
      stats.value.unclaimed = result.reduce((s, b) => s + b.inventory_amount, 0)
      stats.value.claimRate = stats.value.total ? (stats.value.claimed / stats.value.total * 100) : 0
      stats.value.avgAge = stats.value.unclaimed
        ? result.reduce((s, b) => s + b.inventory_amount * b.inventory_age_days, 0) / stats.value.unclaimed
        : 0
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

function goBack() { router.back() }
</script>

<template>
  <div v-loading="loading">
    <!-- 返回按钮 -->
    <div class="drill-header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <h2>{{ dimension === 'project' ? '项目' : dimension === 'purchaser' ? '采购人' : '物资' }}: {{ dimensionName }}</h2>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="drill-stats">
      <el-col :span="8">
        <el-statistic title="入库金额" :value="stats.total">
          <template #default>{{ formatAmount(stats.total) }}</template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="领用金额" :value="stats.claimed">
          <template #default>{{ formatAmount(stats.claimed) }}</template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="领用率" :value="stats.claimRate">
          <template #default>{{ stats.claimRate.toFixed(1) }}%</template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="未消耗金额" :value="stats.unclaimed">
          <template #default>{{ formatAmount(stats.unclaimed) }}</template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="平均库龄(加权)" :value="stats.avgAge">
          <template #default>{{ formatDays(stats.avgAge) }}</template>
        </el-statistic>
      </el-col>
      <el-col :span="8">
        <el-statistic title="批次数" :value="batches.length" />
      </el-col>
    </el-row>

    <!-- 批次明细表 -->
    <el-card shadow="hover" style="margin-top:16px">
      <template #header><span>采购批次明细 ({{ batches.length }} 条)</span></template>
      <el-table :data="batches" stripe max-height="500">
        <el-table-column prop="batch_no" label="批次号" width="140" />
        <el-table-column label="物资" min-width="120">
          <template #default="{ row }">{{ row.material?.name }}</template>
        </el-table-column>
        <el-table-column label="入库日期" width="110">
          <template #default="{ row }">{{ row.inbound_date }}</template>
        </el-table-column>
        <el-table-column label="入库金额" align="right" width="110">
          <template #default="{ row }">{{ formatAmount(row.inbound_amount) }}</template>
        </el-table-column>
        <el-table-column label="领用金额" align="right" width="110">
          <template #default="{ row }">{{ formatAmount(row.claimed_amount) }}</template>
        </el-table-column>
        <el-table-column label="库存金额" align="right" width="110">
          <template #default="{ row }">
            <strong :style="{ color: row.inventory_amount > 100000 ? '#ef4444' : '' }">
              {{ formatAmount(row.inventory_amount) }}
            </strong>
          </template>
        </el-table-column>
        <el-table-column label="领用率" align="right" width="80">
          <template #default="{ row }">{{ formatPercent(row.claim_rate_amount * 100) }}</template>
        </el-table-column>
        <el-table-column label="库龄" align="right" width="80">
          <template #default="{ row }">{{ formatDays(row.inventory_age_days) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.drill-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 16px;
  h2 { font-size: 18px; margin: 0; }
}
.drill-stats { margin-bottom: 8px; }
</style>
