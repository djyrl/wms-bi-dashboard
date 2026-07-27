import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import { initECharts } from './utils/echarts'

// 全局样式（variables.scss 仅含 SCSS 变量，通过 vite additionalData 注入）
import './styles/reset.scss'
import './styles/element-overrides.scss'
import './styles/global.scss'

const app = createApp(App)

// Element Plus（中文语言包）
app.use(ElementPlus, { locale: zhCn })

// 全局注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Router
app.use(router)

// 初始化 ECharts（按需注册）
initECharts()

app.mount('#app')
