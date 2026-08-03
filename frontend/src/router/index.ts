import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { setupGuards } from './guards'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'AnalysisHub',
    component: () => import('@/views/AnalysisHub/index.vue'),
    meta: { title: '分析总览', icon: 'HomeFilled' },
  },
  {
    path: '/indicator-overview',
    name: 'IndicatorOverview',
    component: () => import('@/views/IndicatorOverview/index.vue'),
    meta: {
      title: '指标一览',
      icon: 'List',
    },
  },
  {
    path: '/kpi-checklist',
    name: 'KpiChecklist',
    component: () => import('@/views/KpiChecklist/index.vue'),
    meta: {
      title: 'KPI考核清单',
      icon: 'Tickets',
    },
  },
  {
    path: '/kpi-checklist-range',
    name: 'KpiChecklistRange',
    component: () => import('@/views/KpiChecklistRange/index.vue'),
    meta: {
      title: 'KPI考核(时间区间)',
      icon: 'Timer',
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
    path: '/path1',
    name: 'Path1PurchaseUse',
    component: () => import('@/views/Path1PurchaseUse/index.vue'),
    meta: { title: '采消存分析', icon: 'TrendCharts' },
  },
  {
    path: '/path2',
    name: 'Path2Responsibility',
    component: () => import('@/views/Path2Responsibility/index.vue'),
    meta: { title: '责任归属', icon: 'PieChart' },
  },
  {
    path: '/path3',
    name: 'Path3AgingCleanup',
    component: () => import('@/views/Path3AgingCleanup/index.vue'),
    meta: { title: '库龄清理', icon: 'Timer' },
  },
  {
    path: '/data-table',
    name: 'DataTable',
    component: () => import('@/views/DataTable/index.vue'),
    meta: { title: '数据表格', icon: 'Grid' },
  },
  {
    path: '/cross-analysis',
    name: 'CrossAnalysis',
    component: () => import('@/views/CrossAnalysis/index.vue'),
    meta: {
      title: '交叉分析',
      icon: 'Grid',
    },
  },
  {
    path: '/inventory-report',
    name: 'InventoryReport',
    component: () => import('@/views/InventoryReport/index.vue'),
    meta: {
      title: '库存报表',
      icon: 'Document',
    },
  },
  {
    path: '/project-summary',
    name: 'ProjectSummary',
    component: () => import('@/views/InventoryReport/ProjectSummary.vue'),
    meta: {
      title: '项目汇总',
      icon: 'DataBoard',
    },
  },
  {
    path: '/purchaser-summary',
    name: 'PurchaserSummary',
    component: () => import('@/views/InventoryReport/PurchaserSummary.vue'),
    meta: {
      title: '采购人汇总',
      icon: 'User',
    },
  },
  {
    path: '/source-structure',
    name: 'SourceStructure',
    component: () => import('@/views/InventoryReport/InventorySource.vue'),
    meta: {
      title: '来源结构',
      icon: 'Histogram',
    },
  },
  {
    path: '/traceability',
    name: 'Traceability',
    component: () => import('@/views/Traceability/index.vue'),
    meta: {
      title: '库存追溯',
      icon: 'Connection',
    },
  },
  {
    path: '/theme4',
    name: 'Theme4',
    component: () => import('@/views/Theme4/index.vue'),
    meta: {
      title: '优化建议',
      icon: 'List',
    },
  },
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
