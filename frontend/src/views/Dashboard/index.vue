<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import {
  getSummary,
  getClaimIndicators,
  getStructureIndicators,
  getTimeIndicators,
  getByProject,
  getByPurchaser,
  getTopUnclaimedAmount,
  getTopUnclaimedQuantity,
  getTopClaimedAmount,
  getTopClaimedQuantity,
} from '@/api/modules/dashboard'
import type {
  KpiSummary,
  ClaimIndicators,
  StructureIndicators,
  TimeIndicators,
  ProjectIndicator,
  PurchaserIndicator,
  ProcurementBatch,
} from '@/types/dashboard'

import ErrorResult from '@/components/common/ErrorResult.vue'
import ChartCard from '@/components/common/ChartCard.vue'
import KpiOverview from '@/components/kpi/KpiOverview.vue'
import ClaimGauge from '@/components/charts/ClaimGauge.vue'
import AgeStructureChart from '@/components/charts/AgeStructureChart.vue'
import DonutChart from '@/components/charts/DonutChart.vue'
import DimensionPanel from '@/components/tables/DimensionPanel.vue'
import TopRankings from '@/components/tables/TopRankings.vue'

const loading = ref(false)
const error = ref<string | null>(null)

const summary = ref<KpiSummary | null>(null)
const claim = ref<ClaimIndicators | null>(null)
const structure = ref<StructureIndicators | null>(null)
const time = ref<TimeIndicators | null>(null)
const projectIndicators = ref<ProjectIndicator[]>([])
const purchaserIndicators = ref<PurchaserIndicator[]>([])
const topUnclaimedAmount = ref<ProcurementBatch[]>([])
const topUnclaimedQuantity = ref<ProcurementBatch[]>([])
const topClaimedAmount = ref<any[]>([])
const topClaimedQuantity = ref<any[]>([])

const projectDonutData = computed(() =>
  structure.value?.project_ratios.map(p => ({ name: p.project_name, value: p.inventory_amount })) || []
)
const purchaserDonutData = computed(() =>
  structure.value?.purchaser_ratios.map(p => ({ name: p.purchaser_name, value: p.inventory_amount })) || []
)

async function loadAllData() {
  loading.value = true
  error.value = null
  try {
    const [
      s, c, st, t, pj, pr, ua, uq, ca, cq,
    ] = await Promise.all([
      getSummary(), getClaimIndicators(), getStructureIndicators(), getTimeIndicators(),
      getByProject(), getByPurchaser(),
      getTopUnclaimedAmount(10), getTopUnclaimedQuantity(10),
      getTopClaimedAmount(10), getTopClaimedQuantity(10),
    ])
    summary.value = s
    claim.value = c
    structure.value = st
    time.value = t
    projectIndicators.value = pj
    purchaserIndicators.value = pr
    topUnclaimedAmount.value = ua
    topUnclaimedQuantity.value = uq
    topClaimedAmount.value = ca
    topClaimedQuantity.value = cq
  } catch (e) {
    console.error('数据加载失败:', e)
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div v-loading="loading" element-loading-text="正在加载采购库存数据...">
    <ErrorResult v-if="error" :message="error" @retry="loadAllData" />

    <template v-if="!error">
      <!-- ① Overview: KPI 卡片 -->
      <KpiOverview :summary="summary" />

      <!-- ② 库存领用指标 -->
      <el-row :gutter="16" class="charts-section">
        <el-col :span="24">
          <ChartCard title="领用率（金额 & 数量）">
            <ClaimGauge :claim="claim" />
          </ChartCard>
        </el-col>
      </el-row>

      <!-- ③ 库存时间分析 + ④ 库存结构 -->
      <el-row :gutter="16" class="charts-section">
        <el-col :xs="24" :lg="12">
          <ChartCard title="库龄结构分布">
            <AgeStructureChart :time="time" />
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
          <DimensionPanel :project-indicators="projectIndicators" :purchaser-indicators="purchaserIndicators" />
        </el-col>
      </el-row>

      <!-- ⑥ TOP 排行 -->
      <el-row :gutter="16" class="charts-section">
        <el-col :span="24">
          <TopRankings
            :top-unclaimed-amount="topUnclaimedAmount"
            :top-unclaimed-quantity="topUnclaimedQuantity"
            :top-claimed-amount="topClaimedAmount"
            :top-claimed-quantity="topClaimedQuantity"
          />
        </el-col>
      </el-row>
    </template>
  </div>
</template>
