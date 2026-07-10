<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme1Store } from '@/stores/modules/theme1'
import { storeToRefs } from 'pinia'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import SectionHeader from '@/components/inventory/SectionHeader.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import UsageRateTrend from '@/components/inventory/claim/UsageRateTrend.vue'
import InboundOutboundCompare from '@/components/inventory/claim/InboundOutboundCompare.vue'
import WaterLevelChart from '@/components/inventory/claim/WaterLevelChart.vue'
import AnomalyCalendar from '@/components/inventory/claim/AnomalyCalendar.vue'

const store = useTheme1Store()
const {
  loading,
  error,
  weeks,
  kpiCards,
  claimUsageRate,
  claimInOut,
  claimWaterLevel,
  claimAnomaly,
} = storeToRefs(store)

onMounted(() => {
  store.loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载领用指标数据..." class="theme1-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="store.loadAllData()" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══════════ 主题一：领用指标 ═══════════ 
      <SectionHeader :num="1" title="领用指标 · 识别库存形成情况" desc="总体控制，发现库存异常增长信号" color="#f43f5e" />
-->
      <div class="chart-grid">
        <ChartCard title="📉 物资领用率周度趋势">
          <template #actions>
            <span class="card-subtitle">领用金额 / 本期入库 × 100%（最近12周）</span>
          </template>
          <UsageRateTrend :data="claimUsageRate" :months="weeks" />
        </ChartCard>
        <ChartCard title="📦 入库金额 vs 领用金额 对比">
          <template #actions>
            <span class="card-subtitle">入库多、领用少 → 库存净增（最近12周）</span>
          </template>
          <InboundOutboundCompare :data="claimInOut" :months="weeks" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="📊 在库物资 · 安全库存偏离度">
          <WaterLevelChart :data="claimWaterLevel" />
        </ChartCard>
        <ChartCard title="⚠️ 库存异常变动预警日历">
          <template #actions>
            <span class="card-subtitle">当周领用 > 半年均领用 × 20%（按周统计）</span>
          </template>
          <AnomalyCalendar :data="claimAnomaly" />
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme1-dashboard {
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
