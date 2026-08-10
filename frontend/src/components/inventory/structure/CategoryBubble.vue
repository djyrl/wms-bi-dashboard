<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { CategoryBubbleItem } from '@/types/inventory'

const props = defineProps<{ data: CategoryBubbleItem[]; hideDetail?: boolean }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['物料类别', '库存(万)', '领用率(%)', 'SKU数']
const detailRows = computed(() => props.data.map(d => [d.name, d.inventory, d.usageRate, d.skuCount] as (string | number)[]))
// ECharts 排除「其他」
const chartData = computed(() => props.data.filter(d => d.name !== '其他'))

function render() {
  if (!chartRef.value || !chartData.value.length) return
  chart.init(chartRef.value)

  const items = chartData.value.map(d => ({
    ...d,
    inventoryWan: d.inventory,
  }))

  chart.setOption({
    tooltip: {
      formatter: (p: { name: string; value: number[] }) =>
        `${p.name}<br/>库存: <b>¥${p.value[0]}万</b><br/>领用率: ${p.value[1]}%<br/>SKU数: ${p.value[2]}`,
    },
    grid: { top: 30, right: 30, bottom: 40, left: 60 },
    xAxis: {
      name: '库存金额(万)',
      nameTextStyle: { color: '#94a3b8' },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    },
    yAxis: {
      name: '领用率 %',
      nameTextStyle: { color: '#94a3b8' },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    },
    series: [{
      type: 'scatter',
      data: items.map(d => [d.inventoryWan, d.usageRate, d.skuCount, d.name]),
      symbolSize: (p: number[]) => {
        // SKU数量映射为气泡大小：5~60px
        const size = 5 + (p[2] / Math.max(...items.map(d => d.skuCount), 1)) * 55
        return size
      },
      itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.4)', opacity: 0.8 },
      label: { show: true, position: 'top', color: '#94a3b8', fontSize: 10, formatter: (p: { data: number[] }) => p.data[3] },
      emphasis: { scale: 1.5 },
    }],
    visualMap: {
      show: false,
      dimension: 2,       // SKU数
      min: 0,
      max: Math.max(...items.map(d => d.skuCount), 1),
      inRange: { color: ['#3b82f6', '#f59e0b', '#f43f5e'] },
    },
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail v-if="!props.hideDetail" :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 300px; }
</style>
