<script setup lang="ts">
import { computed, ref, provide } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './Sidebar.vue'

const route = useRoute()
const isFullscreen = computed(() => route.meta?.fullscreen === true)

const sidebarCollapsed = ref(false)
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

provide('sidebarCollapsed', sidebarCollapsed)
provide('toggleSidebar', toggleSidebar)

const sidebarWidth = computed(() =>
  sidebarCollapsed.value ? '64px' : '220px',
)
</script>

<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside
      :width="sidebarWidth"
      class="app-sidebar"
    >
      <Sidebar />
    </el-aside>

    <!-- 右侧区域 -->
    <el-container class="app-right">
      <!-- 顶部栏 
      <el-header height="56px" class="app-header">
        <Header />
      </el-header>-->
      
      <!-- 主内容区 -->
      <el-main class="app-main" :class="{ 'app-main--fullscreen': isFullscreen }">
        <router-view v-slot="{ Component: RouteComponent }">
          <transition name="fade" mode="out-in">
            <component :is="RouteComponent" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style lang="scss" scoped>
.app-container {
  height: 100vh;
  overflow: hidden;
}

.app-sidebar {
  transition: width 0.3s ease;
  overflow: hidden;
}

.app-right {
  display: flex;
  flex-direction: column;
}

.app-header {
  padding: 0;
  flex-shrink: 0;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  background: $bg-color;
  padding: 16px;

  &--fullscreen {
    padding: 0;
    overflow: hidden;
  }
}
</style>
