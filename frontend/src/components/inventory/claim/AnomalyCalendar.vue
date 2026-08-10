<script setup lang="ts">
import { computed, onMounted, watch, ref } from 'vue'
import { useECharts } from '@/composables/useECharts'
import DataDetail from '@/components/inventory/DataDetail.vue'
import type { AnomalyDay } from '@/types/inventory'

const props = defineProps<{ data: AnomalyDay[]; hideDetail?: boolean }>()
const chartRef = ref<HTMLDivElement>()
const chart = useECharts()

const dates = computed(() => props.data.map(d => d.date))
const inbound = computed(() => props.data.map(d => d.inbound_amount))
const claimed = computed(() => props.data.map(d => d.claimed_amount))
const types = computed(() => props.data.map(d => d.type))
const labels = computed(() => props.data.map(d => d.label))
const huanbiValues = computed(() => props.data.map(d => d.huanbi))

const detailHeaders = ['日期', '入库(万元)', '领用(万元)', '状态', '环比']
const detailRows = computed(() =>
  props.data.map(d => [
    d.date,
    d.inbound_amount.toFixed(2),
    d.claimed_amount.toFixed(2),
    d.label,
    d.huanbi != null ? (d.huanbi > 0 ? '↑' : '↓') + Math.abs(d.huanbi) + '%' : '-',
  ] as (string | number)[])
)

function render() {
  if (!chartRef.value || !props.data.length) return
  chart.init(chartRef.value)

  const anomalyIndices = types.value.map((t, i) => t === 1 ? i : -1).filter(i => i !== -1)

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const idx = params[0].dataIndex
        let html = `<div style="font-weight:700;margin-bottom:6px;">${dates.value[idx]}</div>`
        html += `<div>入库: <span style="color:#3b82f6;font-weight:600;">${inbound.value[idx].toFixed(2)}</span> 万元</div>`
        html += `<div>领用: <span style="color:#10b981;font-weight:600;">${claimed.value[idx].toFixed(2)}</span> 万元</div>`
        if (types.value[idx] === 1) {
          html += `<div style="color:#f43f5e;margin-top:4px;">⚠ ${labels.value[idx]}</div>`
        } else {
          html += `<div style="color:#10b981;margin-top:4px;">✓ 正常</div>`
        }
        const hb = huanbiValues.value[idx]
        if (hb != null) {
          const color = hb > 0 ? '#f43f5e' : '#10b981'
          const arrow = hb > 0 ? '↑' : '↓'
          html += `<div style="color:${color};margin-top:2px;">环比${arrow}${Math.abs(hb)}%</div>`
        }
        return html
      },
    },
    legend: {
      data: ['入库金额', '领用金额', '异常标记'],
      textStyle: { color: '#64748b', fontSize: 11 },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates.value,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, rotate: 30 },
    },
    yAxis: {
      type: 'value',
      name: '金额（万元）',
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    series: [
      {
        name: '入库金额',
        type: 'bar',
        data: inbound.value,
        barWidth: '35%',
        itemStyle: {
          color: '#3b82f6',
          borderRadius: [3, 3, 0, 0],
        },
        animationDelay: (idx: number) => idx * 30,
      },
      {
        name: '领用金额',
        type: 'bar',
        data: claimed.value,
        barWidth: '35%',
        itemStyle: {
          color: '#10b981',
          borderRadius: [3, 3, 0, 0],
        },
        animationDelay: (idx: number) => idx * 30 + 100,
      },
      {
        name: '异常标记',
        type: 'scatter',
        data: anomalyIndices.map(i => ({
          value: [i, Math.max(inbound.value[i], claimed.value[i])],
          labelStr: labels.value[i],
        })),
        symbol: 'triangle',
        symbolSize: 16,
        symbolRotate: 180,
        itemStyle: { color: '#f43f5e' },
        emphasis: {
          scale: 1.5,
          itemStyle: { color: '#dc2626' },
        },
        z: 10,
      },
    ],
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
