<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import { formatDays } from '@/utils/format'
import type { AgeGaugeItem } from '@/types/inventory'

const props = defineProps<{ data: AgeGaugeItem[]; hideDetail?: boolean }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const detailHeaders = ['项目编码', '项目名称', '平均库龄', '≥90天占比(%)']
const detailRows = computed(() =>
  props.data.map(d => [d.project, d.projectName, formatDays(d.avgAgeDays), d.over90Rate.toFixed(1) + '%'] as (string | number)[]),
)

function shortName(name: string, code: string): string {
  if (!name || name === code) return code.length > 10 ? code.slice(0, 10) + '…' : code
  return name.length > 10 ? name.slice(0, 10) + '…' : name
}

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const names = props.data.map(d => shortName(d.projectName ?? d.project, d.project))
  const fullNames = props.data.map(d => d.projectName || d.project)
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
        const amt = props.data[idx]?.unclaimedAmount
        const amtStr = amt != null ? `¥${(amt / 10000).toFixed(2)}万` : '--'
        return `${fullNames[idx]}<br/>平均库龄: <b>${formatDays(ages[idx])}</b><br/>库存金额: <b>${amtStr}</b>`
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
      label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10, formatter: (p: { value: number }) => formatDays(p.value) },
      markLine: { silent: true, symbol: 'none', data: [
        { xAxis: 365, label: { formatter: '警戒 365天', color: '#f59e0b' }, lineStyle: { color: '#f59e0b', type: 'dashed' } },
        { xAxis: 730, label: { formatter: '危险 730', color: '#f43f5e' }, lineStyle: { color: '#f43f5e', type: 'dashed' } },
      ] },
    }],
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
.chart { width: 100%; height: 280px; }
</style>
