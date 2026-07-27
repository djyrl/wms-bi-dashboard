<script setup lang="ts">
import type { KpiCardData } from '@/types/inventory'

defineProps<{
  cards: KpiCardData[]
}>()
</script>

<template>
  <div class="kpi-row" :style="{ gridTemplateColumns: `repeat(${cards.length}, 1fr)` }">
    <div v-for="(card, i) in cards" :key="i" class="kpi-card">
      <div class="kpi-icon" :class="`t${i + 1}`">{{ card.icon }}</div>
      <div class="kpi-info">
        <div class="kpi-label">{{ card.label }}</div>
        <div class="kpi-value" :style="{ color: card.color }">
          {{ card.value.toFixed(2) }}<span class="kpi-unit">{{ card.unit }}</span>
        </div>
        <div class="kpi-change" :class="card.changeType">{{ card.change }}</div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding-bottom: 16px;
}

.kpi-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: border-color 0.3s;

  &:hover {
    border-color: rgba(59, 130, 246, 0.3);
  }
}

.kpi-icon {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;

  &.t1 { background: rgba(244, 63, 94, 0.12); }
  &.t2 { background: rgba(245, 158, 11, 0.12); }
  &.t3 { background: rgba(139, 92, 246, 0.12); }
  &.t4 { background: rgba(16, 185, 129, 0.12); }
}

.kpi-info {
  flex: 1;
  min-width: 0;
}

.kpi-label {
  font-size: 11px;
  color: #94a3b8;
  letter-spacing: 0.5px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 800;
  font-family: 'SF Mono', 'Fira Code', monospace;
  line-height: 1.2;
}

.kpi-unit {
  font-size: 15px;
  font-weight: 500;
}

.kpi-change {
  font-size: 11px;
  margin-top: 2px;

  &.up { color: #10b981; }
  &.down { color: #f43f5e; }
}

@media (max-width: 1024px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .kpi-row { grid-template-columns: 1fr; }
}
</style>
