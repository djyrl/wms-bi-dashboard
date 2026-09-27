<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { ProjectTreeNode } from '@/types/inventory'

const props = defineProps<{ data: ProjectTreeNode[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['项目编码', '项目名称', '库存金额(万)', '领用率(%)']
// 明细表显示全部数据（含未关联项目）
const detailRows = computed(() => props.data.filter(d => d.projectCode).map(d => [d.projectCode, d.projectName, Number(d.value).toFixed(2), d.usageRate] as (string | number)[]))
// ECharts 只显示已关联项目名称的项目
const chartData = computed(() => props.data.filter(d => d.name !== '(未关联)' && d.projectName !== '(未关联)'))

function render() {
  if (!chartRef.value || !chartData.value.length) return
  chart.init(chartRef.value)

  // 领用率分档：与采购人图统一（<60 红 / 60~75 黄 / ≥75 绿），60% 为 KPI 达标线
  const usageColor = (r: number) => r < 60 ? '#f43f5e' : r < 75 ? '#f59e0b' : '#10b981'

  chart.setOption({
    tooltip: { formatter: (p: { name: string; value: number; data?: { usageRate?: number } }) => `${p.name}<br/>库存金额: <b>¥${Number(p.value).toFixed(2)}万</b><br/>领用率: ${p.data?.usageRate ?? '-'}%` },
    series: [{
      type: 'treemap', roam: false, width: '96%', height: '85%', left: '2%', top: 10,
      label: { show: true, formatter: (p: { name: string; value: number }) => `${p.name}\n¥${Number(p.value).toFixed(2)}万`, fontSize: 11, color: '#fff' },
      upperLabel: { show: true, height: 24, color: '#94a3b8', fontSize: 11 },
      itemStyle: { borderColor: '#111827', borderWidth: 3, gapWidth: 2 },
      levels: [{ itemStyle: { borderColor: '#0a0e17', borderWidth: 4, gapWidth: 2 }, upperLabel: { show: true } }],
      data: chartData.value.map(d => ({ ...d, itemStyle: { color: usageColor(d.usageRate) } })),
    }],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })

defineExpose({ refresh: render })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 300px; }
</style>
