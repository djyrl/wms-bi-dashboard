# 📊 BI Dash — 智能分析仪表盘

一个企业级 BI 前端可视化项目，Flask 后端提供 RESTful API，前端使用 Vue 3 + TypeScript + ECharts 渲染丰富的图表。

## 项目结构

```
bi-dashboard/
├── backend/
│   ├── app.py                  # Flask 应用，API 路由
│   ├── requirements.txt        # Python 依赖
│   └── data/
│       └── generate_data.py    # 模拟数据生成
├── frontend/                   # Vite + Vue 3 + TypeScript 项目
│   ├── index.html              # Vite 入口 HTML
│   ├── package.json
│   ├── vite.config.ts          # Vite 配置（代理、自动导入）
│   ├── tsconfig.json
│   └── src/
│       ├── main.ts             # 应用启动入口
│       ├── App.vue             # 根组件
│       ├── api/                # API 层
│       │   ├── request.ts      # Axios 实例 + 拦截器
│       │   └── modules/        # 按模块划分的 API
│       ├── router/             # 路由配置
│       ├── stores/             # Pinia 状态管理
│       ├── composables/        # 组合式函数（useECharts, useClock）
│       ├── utils/              # 工具函数
│       ├── types/              # TypeScript 类型定义
│       ├── layout/             # 布局组件（侧边栏 + 顶栏 + 主内容）
│       ├── components/         # 业务组件
│       │   ├── charts/         # ECharts 图表组件（×5）
│       │   ├── kpi/            # KPI 卡片组件
│       │   ├── tables/         # 数据表格组件（×2）
│       │   └── common/         # 通用组件
│       ├── views/              # 页面
│       │   ├── Dashboard/      # 仪表盘页面
│       │   └── errors/         # 404 等错误页面
│       └── styles/             # SCSS 样式
└── README.md
```

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

API 服务运行在 `http://127.0.0.1:5001`

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`，前端开发服务器会自动将 `/api` 请求代理到后端。

### 3. 生产构建

```bash
cd frontend
npm run build     # 输出到 dist/
npm run preview   # 预览构建结果
```

## API 接口一览

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| GET | `/api/summary` | KPI 摘要（营收、订单、客单价、客户数） | — |
| GET | `/api/revenue_trend` | 营收 + 成本 + 利润趋势 | `granularity=monthly\|weekly` |
| GET | `/api/category_distribution` | 品类销售占比 | — |
| GET | `/api/regional_sales` | 区域销售排行 | — |
| GET | `/api/top_products` | 热销产品 TOP N | `limit=10` |
| GET | `/api/sales_funnel` | 销售转化漏斗 | — |
| GET | `/api/monthly_comparison` | 月度同比（今年 vs 去年） | — |
| GET | `/api/customer_sources` | 客户来源渠道分布 | — |

所有接口返回统一格式：
```json
{
  "code": 0,
  "data": { ... }
}
```

## 仪表盘包含的可视化

| 模块 | 图表类型 | 说明 |
|------|----------|------|
| KPI 卡片 | 统计卡片 ×4 | 总营收、订单数、客单价、客户数 |
| 营收趋势 | 柱状图 + 折线图 | 营收/成本（柱）+ 利润（线），支持按月/按周切换 |
| 月度同比 | 双折线图 | 今年 vs 去年，每月对比 |
| 品类分布 | 环形图 | 8 个品类的销售占比 |
| 区域销售 | 数据表格 | 7 大区域排行，含订单数 & 均配送天数 |
| TOP 产品 | 数据表格 | 热销 TOP 10，前三名高亮 |
| 销售漏斗 | 漏斗图 | 浏览 → 加购 → 咨询 → 下单 → 支付 → 收货 |
| 客户来源 | 环形图 | 6 大获客渠道占比 |

## 技术栈

- **后端**: Python 3 + Flask + flask-cors
- **前端**: Vue 3 + TypeScript + Vite + Element Plus 2.x + ECharts 5.x + Pinia + Vue Router 4
- **构建**: Vite（开发代理自动转发 API，生产构建 Tree Shaking）
- **开发体验**: TypeScript 类型检查、SCSS 变量系统、unplugin 自动导入
