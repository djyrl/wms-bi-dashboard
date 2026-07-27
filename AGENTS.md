# AGENTS.md — 采购库存 BI Dashboard

> 本文档面向需要在此项目中工作的 AI 编程助手。若你尚未阅读本文，请先通读。

## 1. 项目概述

本项目是一个面向 **WMS（仓库管理系统）采购库存** 的企业级 BI 仪表盘，用于分析入库、领用、库存结构、库龄、项目/采购人维度、异常检测等 22+ 项指标。

系统包含两部分运行形态：

1. **Flask REST API** (`backend/app.py`)：为前端提供 `/api/wms/...` 数据接口，并托管生产构建后的前端静态文件。
2. **MCP Server** (`backend/mcp_server.py`)：将相同的分析能力以 MCP 工具形式暴露给 AI 客户端，支持 `stdio`、`SSE`、`streamable-http` 三种传输模式。

### 1.1 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 + Flask + flask-cors + psycopg2-binary + mcp SDK |
| 数据库 | 人大金仓 KingbaseES（兼容 PostgreSQL），业务库名为 `garden_wms` |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus 2.x + ECharts 6.x + Pinia + Vue Router 4 |
| 构建 | Vite（开发时代理 `/api` → Flask；生产构建输出到 `frontend/dist`） |
| 容器化 | Docker 多阶段构建 + docker-compose 双服务部署 |

### 1.2 项目结构

```
bi-dashboard/
├── backend/                         # Flask 后端 + MCP Server
│   ├── app.py                       # Flask 应用入口、所有 API 路由
│   ├── mcp_server.py                # MCP Server 入口，暴露 22+ 个工具
│   ├── db_config.py                 # 数据库连接配置（环境变量驱动）
│   ├── utils.py                     # 数据库连接、查询、Decimal→float 转换
│   ├── requirements.txt             # Python 依赖
│   ├── summary.py                   # KPI 总览计算
│   ├── claim_indicators.py        # 采购领用率指标
│   ├── structure_indicators.py    # 库存结构指标
│   ├── time_indicators.py         # 库龄/时间指标
│   ├── dimension_indicators.py    # 项目/采购人维度分析
│   ├── top_indicators.py          # TOP 排行 + 智能备货建议
│   ├── other_indicators.py        # 时序、异常检测、批次消化、批次报表
│   ├── cross_indicators.py        # 项目交叉分析（矩阵/趋势/来源分布）
│   ├── kpi_checklist.py           # KPI 考核清单包装器
│   ├── compute_indicators.py      # 旧版指标计算（被新模块替代，但部分逻辑仍保留）
│   ├── compute_kpi_checklist.py   # 旧版 KPI 计算（高性能自包含实现）
│   ├── import_erp_catalog.py    # ERP 物料目录导入 ETL
│   ├── import_erp_zmmrp226.py   # ERP 项目需求计划导入 ETL
│   ├── data/                      # 开发环境模拟数据
│   │   └── generate_data.py       # 14 个模拟指标接口的数据生成
│   └── sql/                       # 数据库视图/索引/缓存表 DDL
│       ├── 00_deploy_order.sql
│       ├── 01_v_project_inventory_wide_optimized.sql
│       ├── 02_indexes.sql
│       ├── 03_dim_cache_tables.sql
│       └── ...
├── frontend/                        # Vue 3 + Vite 前端
│   ├── package.json
│   ├── vite.config.ts               # Vite 配置、代理、自动导入
│   ├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
│   └── src/
│       ├── main.ts                  # 应用启动入口
│       ├── App.vue
│       ├── api/                     # Axios 请求封装 + 按模块 API
│       │   ├── request.ts           # axios 实例 + 拦截器
│       │   └── modules/
│       ├── router/                  # Vue Router 配置（hash 模式）
│       ├── stores/                  # Pinia 状态管理
│       │   └── modules/
│       ├── views/                   # 页面（按主题/路径划分）
│       ├── components/              # 业务组件（charts / tables / common / inventory）
│       ├── composables/           # 组合式函数（useECharts、useClock）
│       ├── types/                 # TypeScript 类型定义
│       ├── utils/                 # 工具函数
│       └── styles/                # SCSS 样式（variables / reset / global）
├── docker-compose.yml               # 生产部署：bi-dashboard + wms-mcp
├── Dockerfile                       # 多阶段镜像：构建前端 + 运行 Flask
├── .env.example                     # 数据库连接配置模板
├── .mcp.json                        # 本地 MCP 配置（stdio 模式）
└── README.md                        # ⚠️ 已过时，以本文档为准
```

### 1.3 数据源与计算策略

- 核心事实表：`wms_inventory`（库存台账）、`wms_project_inventory`（项目库存台账）、`wms_inventory_log`（库存变动日志）、`wms_material`（物料主数据）。
- ERP 解析表：`wbs_zmmrp048_parsed`（物料/项目/采购人）、`wbs_zmmrp226_parsed`（需求计划）。
- 星型视图层：见 `backend/sql/00_schema_overview.sql`。
  - 核心宽表：`v_project_inventory_wide`
  - 报表视图：`v_rpt_inventory_report`、`v_rpt_outbound_summary`
- Python 计算策略：优先使用轻量 SQL 聚合，复杂指标在 Python 内存中计算；`compute_kpi_checklist.py` 采用“一次拉明细 + 3 条聚合 SQL”的高性能方案。

## 2. 开发环境搭建

### 2.1 启动后端

```bash
cd backend
# 建议使用项目自带的 venv，Python 3.11 或 3.12
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

后端默认监听 `http://0.0.0.0:5001`。

### 2.2 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器默认监听 `http://localhost:5173`，Vite 会自动将 `/api` 开头的请求代理到 `http://127.0.0.1:5001`。

### 2.3 环境变量

复制 `.env.example` 为 `.env` 并填入真实值：

```bash
cp .env.example .env
```

关键变量：

| 变量 | 说明 |
|------|------|
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` | 业务数据库连接 |
| `DB_PASSWORD_BASE64` | **base64 编码**后的数据库密码，优先级高于明文 `DB_PASSWORD` |
| `DB_ERP_*` | ERP 源数据库（可选，导入脚本使用；默认回退到 `DB_*`） |
| `STATIC_FOLDER` | 生产环境前端静态文件目录，Docker 中设置为 `/app/static` |
| `MCP_HOST` / `MCP_PORT` / `MCP_TRANSPORT` | MCP Server 监听配置 |

密码编码方式：

```bash
echo -n "你的密码" | base64
```

## 3. 构建与部署

### 3.1 前端生产构建

```bash
cd frontend
npm run build        # 输出到 frontend/dist/
npm run preview      # 本地预览构建结果
```

### 3.2 Docker 构建与运行

```bash
# 构建镜像
docker build -t bi-dashboard:latest .

# 启动双服务（需先准备 .env）
docker-compose up -d
```

`docker-compose.yml` 会启动：

- `wms-api`：Flask + 前端静态文件，宿主机 `8088` → 容器 `5001`
- `wms-mcp`：MCP Server，宿主机 `8766` → 容器 `8766`，传输模式 `streamable-http`

### 3.3 Dockerfile 说明

多阶段构建：

1. **Stage 1** (`node:22-alpine`)：安装前端依赖并执行 `vite build`。
2. **Stage 2** (`python:3.12-slim`)：安装 Python 依赖，复制后端代码，并将 `dist` 复制到 `/app/static`；清理 `__pycache__` 与 `data`。

注意：Docker 构建使用清华 PyPI 镜像 `https://pypi.tuna.tsinghua.edu.cn/simple`。

## 4. API 接口说明

### 4.1 响应格式

所有接口统一返回：

```json
{
  "code": 0,
  "data": { ... }
}
```

`code != 0` 表示失败，`msg` 字段会包含错误信息。

### 4.2 主要接口分类

| 前缀 | 说明 |
|------|------|
| `/api/...` | 模拟数据接口（仅开发环境 `data/generate_data.py` 存在时注册） |
| `/api/wms/inventory` 等 | WMS 四张核心表原始查询（`wms_inventory`、`wms_project_inventory`、`wms_material`、`wms_inbound_order`） |
| `/api/wms/indicators/...` | 真实数据库指标计算接口（22+ 个） |
| `/api/wms/indicators/kpi-checklist` | KPI 考核清单（K1-K9 + T1-T2） |
| `/api/wms/debug` | 在线诊断接口，逐个测试各计算模块 |
| `/api/wms/health` | 数据库连通性检查 |

常用指标接口示例：

- `GET /api/wms/indicators/summary` — KPI 总览
- `GET /api/wms/indicators/claim` — 采购领用率
- `GET /api/wms/indicators/structure` — 库存结构
- `GET /api/wms/indicators/time` — 库龄时间指标
- `GET /api/wms/indicators/claim/monthly` — 月度领用趋势
- `GET /api/wms/indicators/age-layers?min_amount=100000&min_age=365&max_age=1095`
- `GET /api/wms/indicators/inventory-report?sort_by=inventory_amount&sort_order=desc&limit=500&offset=0`

### 4.3 MCP Server

启动方式：

```bash
# stdio（本地 AI 客户端直接拉起）
python mcp_server.py

# SSE
python mcp_server.py --sse

# Streamable HTTP
python mcp_server.py --http
```

本地 MCP 配置已写入 `.mcp.json`（stdio 模式），指向 `backend/venv/bin/python backend/mcp_server.py`。

## 5. 代码组织与约定

### 5.1 后端

- **入口清晰**：Web 入口 `app.py`，MCP 入口 `mcp_server.py`，不要混用。
- **按指标域拆分**：每个指标类别一个模块（`claim_*.py`、`structure_*.py`、`time_*.py` 等），避免在 `app.py` 中写 SQL。
- **数据库访问**：统一从 `db_config.py` 读取配置，使用 `psycopg2` + `RealDictCursor`。
- **Decimal 处理**：查询返回的 `Decimal` 必须通过 `_f()` 或 `_rows_to_float()` 转为 `float`，再参与 JSON 序列化。
- **异常处理**：Web 路由统一 `try/except`，返回 `{"code": -1, "msg": ...}`；MCP 工具依赖底层异常上抛，由 SDK 处理。

### 5.2 前端

- **Vue 3 Composition API**：所有 `.vue` 文件使用 `<script setup lang="ts">`。
- **状态管理**：Pinia store 按页面/主题拆分，位于 `src/stores/modules/`。推荐组合式写法（`ref` + `computed` + `actions`）。
- **API 层**：所有 HTTP 请求通过 `src/api/request.ts` 中的 axios 实例；按模块拆分 `src/api/modules/*.ts`。
- **自动导入**：
  - `unplugin-auto-import` 自动导入 `vue`、`vue-router`、`pinia`。
  - `unplugin-vue-components` 自动导入 Element Plus 组件。
  - 自动生成 `src/auto-imports.d.ts` 与 `src/components.d.ts`，无需手动维护。
- **路径别名**：`@` 指向 `src/`。
- **样式**：SCSS 变量通过 `vite.config.ts` 的 `additionalData` 全局注入；主题变量位于 `src/styles/variables.scss`。
- **ECharts**：按需注册，位于 `src/utils/echarts.ts`；组件内使用 `useECharts` 组合式函数。

### 5.3 命名约定

- Python：模块名小写 + 下划线；函数/变量 snake_case；类 CamelCase；中文注释。
- TypeScript/Vue：组件名 PascalCase；组合式函数 `useXxx`；store 文件 camelCase；类型定义 PascalCase。

## 6. 测试策略

**当前项目没有专门的测试套件。** 验证变更的方式：

1. **后端接口**：启动 Flask 后访问 `/api/wms/debug` 与 `/api/wms/health`。
2. **MCP Server**：使用支持 MCP 的客户端直接调用 `get_kpi_summary` 等工具。
3. **前端**：`npm run build` 通过 TypeScript 类型检查；`npm run dev` 手动验证页面与图表。

如果你新增核心指标，请同时：

- 在 `backend/app.py` 添加对应 `/api/wms/indicators/...` 路由。
- 在 `backend/mcp_server.py` 添加 `@mcp.tool()` 工具。
- 在 `frontend/src/api/modules/` 添加前端调用函数（如页面需要）。
- 在 `/api/wms/debug` 的诊断列表中加入该函数，方便线上排查。

## 7. 安全注意事项

- `.env` 文件包含数据库密码（base64 编码），已加入 `.gitignore`，**不要提交到仓库**。
- `DB_CONFIG` 与 `DB_CONFIG_CCCK` 两套配置：前者用于 ERP 源数据导入，后者用于业务报表。本地默认值不同，生产环境务必通过环境变量覆盖。
- Docker 镜像构建时不会携带 `.env`，运行时通过 `docker-compose.yml` 注入。
- 后端没有身份认证层；生产部署时建议在网关或反向代理层增加认证。
- 所有 SQL 查询使用参数化查询（`%s` + `params`），禁止字符串拼接 SQL。

## 8. 常见修改路径

| 需求 | 主要文件 |
|------|----------|
| 新增一个 WMS 指标 | 新建 `backend/xxx_indicators.py` → `app.py` 路由 → `mcp_server.py` 工具 → 前端 API/store |
| 调整 KPI 考核阈值 | `backend/kpi_checklist.py` / `backend/compute_kpi_checklist.py` |
| 修改数据库连接 | `backend/db_config.py`、`.env` |
| 新增前端页面 | `frontend/src/views/` → `frontend/src/router/index.ts` → `frontend/src/layout/Sidebar.vue` |
| 新增图表组件 | `frontend/src/components/charts/` 或 `frontend/src/components/inventory/` |
| 调整主题/颜色 | `frontend/src/styles/variables.scss` |
| ERP 数据导入 | `backend/import_erp_catalog.py`、`backend/import_erp_zmmrp226.py` |
| 数据库视图变更 | `backend/sql/` 中对应 DDL，按 `00_deploy_order.sql` 顺序部署 |

## 9. 提示与陷阱

- `README.md` 描述的是早期通用销售 BI 原型，**已过时**。实际业务是 WMS 采购库存分析，以本文档和代码注释为准。
- 模拟数据接口（`/api/...`）与真实数据接口（`/api/wms/...`）同时存在；前端当前混合调用两者，修改时注意不要破坏路由前缀约定。
- `data/generate_data.py` 仅在本地开发时存在；Docker 构建会删除 `data/` 目录，生产镜像只走真实数据库。
- 修改 Python 指标模块后，建议立即访问 `/api/wms/debug` 验证，该接口会返回每个函数的执行状态与耗时。
- 类型文件 `frontend/src/auto-imports.d.ts` 与 `components.d.ts` 由 Vite 插件自动生成，通常不需要手动编辑。
