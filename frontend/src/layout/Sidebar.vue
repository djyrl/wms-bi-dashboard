<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const sidebarCollapsed = inject('sidebarCollapsed', ref(false))

// 从路由表生成菜单项（排除 hidden: true 的路由）
const menuItems = computed(() =>
  router
    .getRoutes()
    .filter((r) => !r.meta.hidden && r.name)
    .map((r) => ({
      index: r.path,
      title: r.meta.title || r.name,
      icon: r.meta.icon,
    })),
)

const activeMenu = computed(() => route.path)

function handleSelect(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="sidebar">
    <!-- Logo -->
    <!-- <div class="sidebar-logo">
      <span class="sidebar-logo__icon">📊</span>
      <span v-show="!sidebarCollapsed" class="sidebar-logo__text">
        BI<span class="sidebar-logo__accent">Dash</span>
      </span>
    </div> -->

    <!-- 菜单 -->
    <el-menu
      :default-active="activeMenu"
      :collapse="sidebarCollapsed"
      background-color="#001529"
      text-color="#ffffffa6"
      active-text-color="#fff"
      @select="handleSelect"
    >
      <el-menu-item
        v-for="item in menuItems"
        :key="item.index"
        :index="item.index"
      >
        <el-icon v-if="item.icon">
          <component :is="item.icon" />
        </el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<style lang="scss" scoped>
.sidebar {
  height: 100%;
  background-color: #001529;
  display: flex;
  flex-direction: column;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.sidebar-logo__icon {
  font-size: 22px;
}

.sidebar-logo__text {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.sidebar-logo__accent {
  color: #4f46e5;
}

// 菜单区撑满
.el-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}
</style>
