<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme4Store } from '@/stores/modules/theme4'
import { storeToRefs } from 'pinia'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import SluggishTable from '@/components/inventory/actions/SluggishTable.vue'
import OverstockChart from '@/components/inventory/actions/OverstockChart.vue'
import CleanupProgress from '@/components/inventory/actions/CleanupProgress.vue'
import OptimizeSuggest from '@/components/inventory/actions/OptimizeSuggest.vue'

const store = useTheme4Store()
const {
  loading,
  error,
  kpiCards,
  sluggishList,
  overstockList,
  cleanupList,
  suggestList,
} = storeToRefs(store)

onMounted(() => {
  store.loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载行动计划数据..." class="theme4-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="store.loadAllData()" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══ 4.1 TOP15 呆滞物料清单（全宽表格） ═══ -->
      <ChartCard title="📋 TOP15 呆滞物料 · 处置优先级清单">
        <template #actions>
          <span class="card-subtitle">按「金额×库龄」综合评分排序</span>
        </template>
        <SluggishTable :data="sluggishList" />
      </ChartCard>

      <!-- ═══ 4.2 超量备货 + 4.3 处置进度 ═══ -->
      <!-- <div class="chart-grid">
        <ChartCard title="📊 TOP10 超量备货物料">
          <template #actions>
            <span class="card-subtitle">当前库存 / 安全库存上限</span>
          </template>
          <OverstockChart :data="overstockList" />
        </ChartCard>
        <ChartCard title="✅ 处置计划执行进度">
          <template #actions>
            <span class="card-subtitle">各项目呆滞物资清理完成率</span>
          </template>
          <CleanupProgress :data="cleanupList" />
        </ChartCard>
      </div> -->

      <!-- ═══ 4.4 智能备货优化建议 ═══ -->
      <!-- <div class="chart-grid"> -->
        <ChartCard title="💡 智能备货优化建议">
          <template #actions>
            <span class="card-subtitle">基于日均消耗量推荐安全库存调整</span>
          </template>
          <OptimizeSuggest :data="suggestList" />
        </ChartCard>
      <!-- </div> -->
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme4-dashboard {
  padding: 0 0 24px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 4px;

  > .el-card {
    display: flex;
    flex-direction: column;

    :deep(.el-card__body) {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
  }
}

.card-subtitle {
  font-size: 10px;
  color: #94a3b8;
}

@media (max-width: 1024px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
