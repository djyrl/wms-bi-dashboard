<script setup lang="ts">
import { computed } from 'vue'
import { useDashboardStore } from '@/stores/modules/dashboard'
import { storeToRefs } from 'pinia'
import { formatAmount, formatPercent, formatDays } from '@/utils/format'

const store = useDashboardStore()
const { summary } = storeToRefs(store)

interface KpiCard {
  label: string; value: string; sub?: string; color?: string
}

const cards = computed<KpiCard[]>(() => {
  const s = summary.value
  if (!s) return []
  return [
    { label: '总入库金额', value: formatAmount(s.total_inbound_amount), sub: `${s.batch_count} 批次` },
    { label: '总领用金额', value: formatAmount(s.total_claimed_amount), color: '#10b981' },
    { label: '整体领用率', value: formatPercent(s.overall_claim_rate), color: s.overall_claim_rate >= 80 ? '#10b981' : s.overall_claim_rate >= 50 ? '#f59e0b' : '#ef4444' },
    { label: '当前库存金额', value: formatAmount(s.total_inventory_amount), color: '#ef4444' },
    { label: '长库龄占比(≥1年)', value: formatPercent(s.aged_ratio_1y), color: s.aged_ratio_1y > 50 ? '#ef4444' : '#f59e0b' },
    { label: '加权平均库龄', value: formatDays(s.avg_age_weighted_days), color: s.avg_age_weighted_days > 365 ? '#ef4444' : '#10b981' },
  ]
})
</script>

<template>
  <el-row :gutter="16" class="kpi-section">
    <el-col v-for="(c, i) in cards" :key="i" :xs="12" :sm="8" :lg="4">
      <el-card shadow="hover" class="kpi-card">
        <div class="kpi-card__label">{{ c.label }}</div>
        <div class="kpi-card__value" :style="{ color: c.color }">{{ c.value }}</div>
        <div v-if="c.sub" class="kpi-card__sub">{{ c.sub }}</div>
      </el-card>
    </el-col>
  </el-row>
</template>

<style lang="scss" scoped>
.kpi-card { margin-bottom: 8px; }
.kpi-card__label { font-size: 13px; color: $text-secondary; margin-bottom: 6px; }
.kpi-card__value { font-size: 24px; font-weight: 700; }
.kpi-card__sub { font-size: 12px; color: $text-secondary; margin-top: 4px; }
</style>
