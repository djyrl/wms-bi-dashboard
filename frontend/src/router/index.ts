import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { setupGuards } from './guards'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard/index.vue'),
    meta: {
      title: '仪表盘',
      icon: 'Monitor',
    },
  },
  {
    path: '/inventory',
    name: 'Inventory',
    component: () => import('@/views/Inventory/index.vue'),
    meta: {
      title: '库存分析驾驶舱',
      icon: 'TrendCharts',
    },
  },
  {
    path: '/theme1',
    name: 'Theme1',
    component: () => import('@/views/Theme1/index.vue'),
    meta: {
      title: '领用指标',
      icon: 'DataAnalysis',
    },
  },
  {
    path: '/theme2',
    name: 'Theme2',
    component: () => import('@/views/Theme2/index.vue'),
    meta: {
      title: '项目分析',
      icon: 'PieChart',
    },
  },
  {
    path: '/theme3',
    name: 'Theme3',
    component: () => import('@/views/Theme3/index.vue'),
    meta: {
      title: '库龄分析',
      icon: 'Timer',
    },
  },
  {
    path: '/theme4',
    name: 'Theme4',
    component: () => import('@/views/Theme4/index.vue'),
    meta: {
      title: '行动计划',
      icon: 'List',
    },
  },
  // {
  //   path: '/kpi-checklist',
  //   name: 'KpiChecklist',
  //   component: () => import('@/views/KpiChecklist/index.vue'),
  //   meta: {
  //     title: 'KPI考核清单',
  //     icon: 'Tickets',
  //   },
  // },
  // {
  //   path: '/drill/:dimension/:id',
  //   name: 'Drill',
  //   component: () => import('@/views/Drill/index.vue'),
  //   meta: {
  //     title: '维度下钻',
  //     icon: 'Search',
  //   },
  // },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/views/errors/404.vue'),
    meta: {
      title: '页面未找到',
      hidden: true,
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404',
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

setupGuards(router)

export default router
