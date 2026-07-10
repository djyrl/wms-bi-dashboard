<script setup lang="ts">
import { onMounted } from 'vue'
import { useTheme3Store } from '@/stores/modules/theme3'
import { storeToRefs } from 'pinia'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import AgePyramid from '@/components/inventory/time/AgePyramid.vue'
import AgeTrend from '@/components/inventory/time/AgeTrend.vue'
import SluggishHeatmap from '@/components/inventory/time/SluggishHeatmap.vue'
import AgeGauge from '@/components/inventory/time/AgeGauge.vue'

const store = useTheme3Store()
const {
  loading,
  error,
  months,
  kpiCards,
  agePyramid,
  ageTrend,
  sluggishHeatmap,
  heatmapCategories,
  heatmapAgeLabels,
  ageGauge,
} = storeToRefs(store)

onMounted(() => {
  store.loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载库龄分析数据..." class="theme3-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="store.loadAllData()" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══ 第一行：库龄金字塔 + 平均库龄趋势 ═══ -->
      <div class="chart-grid">
        <ChartCard title="⏳ 库存库龄分布 · 金字塔">
          <template #actions>
            <span class="card-subtitle">横向对比库龄段金额与SKU数</span>
          </template>
          <AgePyramid :data="agePyramid" />
        </ChartCard>
        <ChartCard title="📈 平均库龄月度趋势">
          <template #actions>
            <span class="card-subtitle">整体库龄健康度变化方向</span>
          </template>
          <AgeTrend :data="ageTrend" :months="months" />
        </ChartCard>
      </div>

      <!-- ═══ 第二行：滞留热力图 + 库龄预警 ═══ -->
      <div class="chart-grid">
        <ChartCard title="🔥 滞留库存热力图 · 物料类别 × 库龄段">
          <template #actions>
            <span class="card-subtitle">聚焦右下角（超长库龄）</span>
          </template>
          <SluggishHeatmap
            :data="sluggishHeatmap"
            :categories="heatmapCategories"
            :ageLabels="heatmapAgeLabels"
          />
        </ChartCard>
        <ChartCard title="🚨 库龄预警 · 各项目超标情况">
          <template #actions>
            <span class="card-subtitle">超过90天库龄的库存占比</span>
          </template>
          <AgeGauge :data="ageGauge" />
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme3-dashboard {
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
