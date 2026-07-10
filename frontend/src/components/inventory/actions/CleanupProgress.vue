<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { CleanupItem } from '@/types/inventory'

const props = defineProps<{ data: CleanupItem[] }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['项目', '总库存(万)', '已处置(万)', '待处置(万)', '完成率']
const detailRows = computed(() =>
  props.data.map(d => [d.project, d.total, d.cleaned, d.remain, d.rate + '%'] as (string | number)[])
)

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const names = props.data.map(d => d.project)
  const cleaned = props.data.map(d => d.cleaned)
  const remain = props.data.map(d => d.remain)
  const totals = props.data.map(d => d.total)

  chart.setOption({
    tooltip: { trigger: 'axis', formatter: (p: { dataIndex: number }[]) => {
      const i = p[0].dataIndex
      return `${names[i]}<br/>已处置: ¥${cleaned[i]}万 (${(cleaned[i] / totals[i] * 100).toFixed(0)}%)<br/>待处置: ¥${remain[i]}万`
    }},
    legend: { top: 0, textStyle: { color: '#94a3b8', fontSize: 10 }, data: ['已处置', '待处置'] },
    grid: { top: 40, right: 20, bottom: 20, left: 60 },
    xAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', fontSize: 10 }, inverse: true },
    series: [
      { name: '已处置', type: 'bar', stack: 'total', data: cleaned, itemStyle: { color: '#10b981' }, barWidth: 16, label: { show: true, position: 'inside', color: '#fff', fontSize: 9, formatter: (p: { dataIndex: number }) => cleaned[p.dataIndex] > 400 ? `${(cleaned[p.dataIndex] / totals[p.dataIndex] * 100).toFixed(0)}%` : '' } },
      { name: '待处置', type: 'bar', stack: 'total', data: remain, itemStyle: { color: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, borderRadius: [0, 6, 6, 0] }, label: { show: true, position: 'right', color: '#94a3b8', fontSize: 9, formatter: (p: { dataIndex: number }) => `${(remain[p.dataIndex] / totals[p.dataIndex] * 100).toFixed(0)}%` } },
    ],
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
