<script setup lang="ts">
import { inject, ref } from 'vue'
import { useClock } from '@/composables/useClock'

const sidebarCollapsed = inject('sidebarCollapsed', ref(false))
const toggleSidebar = inject('toggleSidebar', () => {})
const { currentTime } = useClock()

function handleToggle() {
  toggleSidebar()
}
</script>

<template>
  <div class="navbar">
    <div class="navbar-left">
      <!-- 侧边栏折叠按钮 -->
      <el-button
        text
        @click="handleToggle"
      >
        <el-icon :size="20">
          <Fold v-if="!sidebarCollapsed" />
          <Expand v-else />
        </el-icon>
      </el-button>
    </div>

    <div class="navbar-right">
      <!-- 时钟 -->
      <span class="navbar-clock">{{ currentTime }}</span>

      <!-- 用户信息占位 -->
      <el-tag effect="plain" round size="small">
        BI 管理员
      </el-tag>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid $border-color;
  box-shadow: $shadow;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.navbar-clock {
  font-size: 13px;
  color: $text-secondary;
}

@media (max-width: 768px) {
  .navbar-clock {
    display: none;
  }
}
</style>
