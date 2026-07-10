<script setup lang="ts">
defineProps<{
  num: number
  title: string
  desc?: string
  color: string
}>()
</script>

<template>
  <div class="section-row">
    <span class="section-num" :style="{ background: color }">{{ num }}</span>
    <span class="section-title" :style="{ color }">{{ title }}</span>
    <span v-if="desc" class="section-desc">{{ desc }}</span>
  </div>
</template>

<style lang="scss" scoped>
.section-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 28px 0 8px;
}

.section-num {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
}

.section-title {
  font-size: 17px;
  font-weight: 700;
}

.section-desc {
  font-size: 12px;
  color: #94a3b8;
  margin-left: 4px;
}
</style>
