<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useTheme2Store } from '@/stores/modules/theme2'
import { storeToRefs } from 'pinia'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import SectionHeader from '@/components/inventory/SectionHeader.vue'
import KpiCards from '@/components/inventory/KpiCards.vue'

import ProjectTreemap from '@/components/inventory/structure/ProjectTreemap.vue'
import BuyerRanking from '@/components/inventory/structure/BuyerRanking.vue'
import CategoryBubble from '@/components/inventory/structure/CategoryBubble.vue'
import BatchProgress from '@/components/inventory/structure/BatchProgress.vue'

const store = useTheme2Store()
const {
  loading,
  error,
  kpiCards,
  structureProjectTree,
  structureBuyerRank,
  structureCategoryBubble,
  structureBatch,
  structureBatchLabels,
} = storeToRefs(store)

const projectTreemapRef = ref<InstanceType<typeof ProjectTreemap>>()

function handleRefreshTreemap() {
  projectTreemapRef.value?.refresh()
}

onMounted(() => {
  store.loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载项目分析数据..." class="theme2-dashboard">
    <ErrorResult v-if="error" :message="error" @retry="store.loadAllData()" />

    <template v-if="!error">
      <!-- ═══ KPI 总览 ═══ -->
      <KpiCards :cards="kpiCards" />

      <!-- ═══════════ 主题二：结构指标 ═══════════ 
      <SectionHeader :num="2" title="结构指标 · 定位库存来源" desc="按项目/采购人/类别逐层下钻，找到库存形成的关键来源" color="#f59e0b" />
-->
      <div class="chart-grid">
        <ChartCard title="🌳 按项目维度 · 库存金额分布">
          <template #actions>
            <el-button size="small" text @click="handleRefreshTreemap">🔄 刷新</el-button>
            <span class="card-subtitle">矩形面积=库存金额，颜色=领用率</span>
          </template>
          <ProjectTreemap ref="projectTreemapRef" :data="structureProjectTree" />
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
    </template>
  </div>
</template>

<style lang="scss" scoped>
.theme2-dashboard {
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
