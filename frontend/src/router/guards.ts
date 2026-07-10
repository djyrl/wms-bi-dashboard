import type { Router } from 'vue-router'

export function setupGuards(router: Router) {
  router.beforeEach((to, _from, next) => {
    // 设置页面标题
    document.title = `${to.meta.title || 'BI Dash'} | BI 智能分析平台`

    // TODO: 权限校验预留点
    // if (to.meta.requiresAuth && !userStore.isLoggedIn) next('/login')

    next()
  })
}
