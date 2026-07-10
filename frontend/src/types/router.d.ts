import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** 页面标题 */
    title?: string
    /** 侧边栏图标（Element Plus Icons 名称） */
    icon?: string
    /** 是否在侧边栏隐藏 */
    hidden?: boolean
    /** 是否需要权限 */
    requiresAuth?: boolean
  }
}
