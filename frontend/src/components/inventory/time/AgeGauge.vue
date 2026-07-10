<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { AgeGaugeItem } from '@/types/inventory'

const props = defineProps<{ data: AgeGaugeItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['项目', '平均库龄(天)', '≥90天占比(%)']
const detailRows = computed(() =>
  props.data.map(d => [d.project, d.avgAgeDays, d.over90Rate] as (string | number)[]),
)

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const names = props.data.map(d => d.project)
  const ages = props.data.map(d => d.avgAgeDays)
  const rates = props.data.map(d => d.over90Rate)
  const xMax = Math.ceil(Math.max(...ages) * 1.2)

  // 按 ≥90天占比 着色：≤15% 绿色，15-30% 黄色，>30% 红色
  const barColors = rates.map(r =>
    r > 30 ? '#f43f5e' : r > 15 ? '#f59e0b' : '#10b981',
  )

  chart.setOption({
    tooltip: {
      formatter: (p: { name: string; dataIndex: number }) => {
        const idx = p.dataIndex
        return `${p.name}<br/>平均库龄: <b>${ages[idx]} 天</b><br/>≥90天占比: <b>${rates[idx]}%</b>`
      },
    },
    grid: { top: 15, right: 55, bottom: 20, left: 70 },
    xAxis: { type: 'value', name: '天', max: xMax, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', fontSize: 10 }, inverse: true },
    series: [{
      type: 'bar',
      data: ages.map((v, i) => ({
        value: v,
        itemStyle: { color: barColors[i], borderRadius: [0, 6, 6, 0] },
      })),
      barWidth: 16,
      label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10, formatter: '{c}天' },
      markLine: { silent: true, symbol: 'none', data: [
        { xAxis: 45, label: { formatter: '警戒 45天', color: '#f59e0b' }, lineStyle: { color: '#f59e0b', type: 'dashed' } },
        { xAxis: 90, label: { formatter: '危险 90天', color: '#f43f5e' }, lineStyle: { color: '#f43f5e', type: 'dashed' } },
      ] },
    }],
  })
}

onMounted(render)
watch(() => props.data, render, { deep: true })
</script>

<template>
  <div ref="chartRef" class="chart" />
  <DataDetail :headers="detailHeaders" :rows="detailRows" />
</template>

<style lang="scss" scoped>
.chart { width: 100%; height: 280px; }
</style>
