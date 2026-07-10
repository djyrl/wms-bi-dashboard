<script setup lang="ts">
import { onMounted } from 'vue'
import { useInventoryStore } from '@/stores/modules/inventory'
import { storeToRefs } from 'pinia'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import SectionHeader from '@/components/inventory/SectionHeader.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

// Theme 1
import UsageRateTrend from '@/components/inventory/claim/UsageRateTrend.vue'
import InboundOutboundCompare from '@/components/inventory/claim/InboundOutboundCompare.vue'
import WaterLevelChart from '@/components/inventory/claim/WaterLevelChart.vue'
import AnomalyCalendar from '@/components/inventory/claim/AnomalyCalendar.vue'

// Theme 2
import ProjectTreemap from '@/components/inventory/structure/ProjectTreemap.vue'
import BuyerRanking from '@/components/inventory/structure/BuyerRanking.vue'
import CategoryBubble from '@/components/inventory/structure/CategoryBubble.vue'
import BatchProgress from '@/components/inventory/structure/BatchProgress.vue'

// Theme 3
import AgePyramid from '@/components/inventory/time/AgePyramid.vue'
import AgeTrend from '@/components/inventory/time/AgeTrend.vue'
import SluggishHeatmap from '@/components/inventory/time/SluggishHeatmap.vue'
import AgeGauge from '@/components/inventory/time/AgeGauge.vue'

// Theme 4
import SluggishTable from '@/components/inventory/actions/SluggishTable.vue'
import OverstockChart from '@/components/inventory/actions/OverstockChart.vue'
import CleanupProgress from '@/components/inventory/actions/CleanupProgress.vue'
import OptimizeSuggest from '@/components/inventory/actions/OptimizeSuggest.vue'

import { MONTHS, CATEGORIES } from '@/stores/modules/inventory'

const store = useInventoryStore()
const {
  loading, error, kpiCards,
  claimUsageRate, claimInOut, claimWaterLevel, claimAnomaly,
  structureProjectTree, structureBuyerRank, structureCategoryBubble, structureBatch, structureBatchLabels,
  timePyramid, timeTrend, timeHeatmapData, timeGauge,
  topSluggish, topOverstock, topCleanup, topSuggest,
} = storeToRefs(store)

const SAMPLE = store.SAMPLE

onMounted(() => {
  store.loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载库存分析数据..." class="inventory-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="store.loadAllData()" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══════════ 主题一：领用指标 ═══════════ -->
      <SectionHeader :num="1" title="领用指标 · 识别库存形成情况" desc="总体控制，发现库存异常增长信号" color="#f43f5e" />

      <div class="chart-grid">
        <ChartCard title="📉 物资领用率月度趋势">
          <template #actions>
            <span class="card-subtitle">领用金额 / (期初库存 + 本期入库) × 100%</span>
          </template>
          <UsageRateTrend :data="claimUsageRate" :months="MONTHS" />
        </ChartCard>
        <ChartCard title="📦 入库金额 vs 领用金额 对比">
          <template #actions>
            <span class="card-subtitle">当月入库多、领用少 → 库存净增</span>
          </template>
          <InboundOutboundCompare :data="claimInOut" :months="MONTHS" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="📊 在库水位变化 · 安全库存偏离度">
          <WaterLevelChart :data="claimWaterLevel" />
        </ChartCard>
        <ChartCard title="⚠️ 库存异常变动预警日历">
          <template #actions>
            <span class="card-subtitle">单日入库/领用偏离均值2σ的事件</span>
          </template>
          <AnomalyCalendar :data="claimAnomaly" />
        </ChartCard>
      </div>

      <!-- ═══════════ 主题二：结构指标 ═══════════ -->
      <SectionHeader :num="2" title="结构指标 · 定位库存来源" desc="按项目/采购人/类别逐层下钻，找到库存形成的关键来源" color="#f59e0b" />

      <div class="chart-grid">
        <ChartCard title="🌳 按项目维度 · 库存金额分布">
          <template #actions>
            <span class="card-subtitle">矩形面积 = 库存金额，点击可下钻</span>
          </template>
          <ProjectTreemap :data="structureProjectTree" />
        </ChartCard>
        <ChartCard title="👤 按采购负责人 · 库存贡献排行">
          <template #actions>
            <span class="card-subtitle">定位高库存的责任主体</span>
          </template>
          <BuyerRanking :data="structureBuyerRank" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="🏷 按物料类别 · 库存金额与领用率">
          <template #actions>
            <span class="card-subtitle">气泡大小=库存金额，颜色=领用率</span>
          </template>
          <CategoryBubble :data="structureCategoryBubble" />
        </ChartCard>
        <ChartCard title="📦 按入库批次 · 库存消化进度">
          <template #actions>
            <span class="card-subtitle">批次入库后逐月剩余库存占比</span>
          </template>
          <BatchProgress :data="structureBatch" :labels="structureBatchLabels" />
        </ChartCard>
      </div>

      <!-- ═══════════ 主题三：时间指标 ═══════════ -->
      <SectionHeader :num="3" title="时间指标 · 识别滞留库存" desc="库龄结构变化，精准定位长期未动物料" color="#8b5cf6" />

      <div class="chart-grid">
        <ChartCard title="⏳ 库存库龄分布 · 金字塔">
          <template #actions>
            <span class="card-subtitle">横向对比库龄段金额与SKU数</span>
          </template>
          <AgePyramid :data="timePyramid" />
        </ChartCard>
        <ChartCard title="📈 平均库龄月度趋势">
          <template #actions>
            <span class="card-subtitle">整体库龄健康度变化方向</span>
          </template>
          <AgeTrend :data="timeTrend" :months="MONTHS" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="🔥 滞留库存热力图 · 物料类别 × 库龄段">
          <template #actions>
            <span class="card-subtitle">颜色越深=库存金额越高，聚焦右下角(超长库龄)</span>
          </template>
          <SluggishHeatmap :data="timeHeatmapData" :categories="CATEGORIES" :age-labels="SAMPLE.heatmapAgeLabels" />
        </ChartCard>
        <ChartCard title="🚨 库龄预警仪表 · 各项目超标情况">
          <template #actions>
            <span class="card-subtitle">超过90天库龄的库存占比</span>
          </template>
          <AgeGauge :data="timeGauge" />
        </ChartCard>
      </div>

      <!-- ═══════════ 主题四：TOP指标 · 问题清单 ═══════════ -->
      <SectionHeader :num="4" title="TOP指标 · 问题清单 & 行动计划" desc="按优先级排序，每一项都有明确的处置建议" color="#10b981" />

      <div class="chart-grid">
        <ChartCard title="📋 TOP9 呆滞物料 · 处置优先级清单">
          <template #actions>
            <span class="card-subtitle">按「金额×库龄」综合评分排序</span>
          </template>
          <SluggishTable :data="topSluggish" />
        </ChartCard>
        <ChartCard title="📊 TOP10 超量备货物料">
          <template #actions>
            <span class="card-subtitle">当前库存 / 安全库存上限</span>
          </template>
          <OverstockChart :data="topOverstock" />
        </ChartCard>
      </div>

      <div class="chart-grid">
        <ChartCard title="✅ 处置计划执行进度">
          <template #actions>
            <span class="card-subtitle">各项目呆滞物资清理完成率</span>
          </template>
          <CleanupProgress :data="topCleanup" />
        </ChartCard>
        <ChartCard title="💡 智能备货优化建议">
          <template #actions>
            <span class="card-subtitle">基于日均消耗量推荐安全库存调整</span>
          </template>
          <OptimizeSuggest :data="topSuggest" />
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.inventory-dashboard {
  padding: 0 0 24px;
}

/* ── CSS Grid 布局（与参考 HTML 一致）── */
.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 4px;

  /* 所有卡片自动等高，图表完美对齐 */
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
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
