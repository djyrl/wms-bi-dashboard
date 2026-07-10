<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useDashboardStore } from '@/stores/modules/dashboard'
import { storeToRefs } from 'pinia'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiOverview from '@/components/kpi/KpiOverview.vue'
import ClaimGauge from '@/components/charts/ClaimGauge.vue'
import AgeStructureChart from '@/components/charts/AgeStructureChart.vue'
import DonutChart from '@/components/charts/DonutChart.vue'
import DimensionPanel from '@/components/tables/DimensionPanel.vue'
import TopRankings from '@/components/tables/TopRankings.vue'

const store = useDashboardStore()
const { loading, error, structure } = storeToRefs(store)

const projectDonutData = computed(() =>
  structure.value?.project_ratios.map(p => ({ name: p.project_name, value: p.inventory_amount })) || []
)
const purchaserDonutData = computed(() =>
  structure.value?.purchaser_ratios.map(p => ({ name: p.purchaser_name, value: p.inventory_amount })) || []
)

onMounted(() => {
  store.loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载采购库存数据...">
    <ErrorResult v-if="error" :message="error" @retry="store.loadAllData()" />

    <template v-if="!error">
      <!-- ① Overview: KPI 卡片 -->
      <KpiOverview />

      <!-- ② 库存领用指标 -->
      <el-row :gutter="16" class="charts-section">
        <el-col :span="24">
          <ChartCard title="领用率（金额 & 数量）">
            <ClaimGauge />
          </ChartCard>
        </el-col>
      </el-row>

      <!-- ③ 库存时间分析 + ④ 库存结构 -->
      <el-row :gutter="16" class="charts-section">
        <el-col :xs="24" :lg="12">
          <ChartCard title="库龄结构分布">
            <AgeStructureChart />
          </ChartCard>
        </el-col>
        <el-col :xs="24" :lg="6">
          <DonutChart title="项目库存占比" :data="projectDonutData" height="340px" />
        </el-col>
        <el-col :xs="24" :lg="6">
          <DonutChart title="采购人库存占比" :data="purchaserDonutData" height="340px" />
        </el-col>
      </el-row>

      <!-- ⑤ 项目 & 采购人维度 -->
      <el-row :gutter="16" class="charts-section">
        <el-col :span="24">
          <DimensionPanel />
        </el-col>
      </el-row>

      <!-- ⑥ TOP 排行 -->
      <el-row :gutter="16" class="charts-section">
        <el-col :span="24">
          <TopRankings />
        </el-col>
      </el-row>
    </template>
  </div>
</template>
