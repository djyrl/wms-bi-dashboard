# BI Dashboard 数据依赖与血缘关系文档

> 本文档描述 BI Dashboard 系统中所有指标的数据来源、计算链路、字段映射关系。
> 从数据库原始表 → SQL 视图 → Python 计算模块 → Flask API → 前端 TypeScript 模块 → 页面组件，逐层追溯。
> 字段名保留英文原文并附中文解释，整体描述使用中文。

---

## 目录

1. [数据库原始表](#1-数据库原始表)
2. [SQL 视图层](#2-sql-视图层)
3. [Python 计算模块](#3-python-计算模块)
4. [Flask API 路由](#4-flask-api-路由)
5. [前端 API 模块](#5-前端-api-模块)
6. [前端页面消费关系](#6-前端页面消费关系)
7. [字段映射速查表](#7-字段映射速查表)
8. [关键计算公式对照](#8-关键计算公式对照)
9. ["当前库存总额"统一改造记录](#9-当前库存总额统一改造记录)

---

## 1. 数据库原始表

### 1.1 WMS 域（`garden_report` schema）

| 表名 | 用途 | 关键过滤条件 |
|------|------|-------------|
| `wms_inventory` | 物理库存（货位级） | `del_flag = '0'`（未删除）, `warehouse_code = 'A00'`（主仓库）, `status = 1`（可用） |
| `wms_inventory_log` | 库存变更流水 | `change_type` 区分出库类型：31=领用出库(pick), 34=维修出库(repair), 35=报废出库(scrap), 36=维修后出库(repaired) |
| `wms_project_inventory` | 项目库存台账 | 记录每个批次归属哪个项目，一个批次可关联多个项目 |
| `wms_material` | 物料主数据 | 物料编码(material_code)、名称(material_name)、规格(material_description)、单位(material_unit) |
| `wms_location` | 货位数据 | 货位编码、货位类型 |
| `wms_warehouse` | 仓库数据 | 仓库编码(warehouse_code)、仓库名称 |

### 1.2 ERP 域（`public` schema）

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `public.erp_catalog_mb51` | SAP 物料凭证（2021年5月至今） | 过滤 `werks = '2635'`（工厂编码）。核心数据在 JSON 列 `row_json` 中：`MATNR`（物料编码 / material_code）、`DMBTR`（金额 / amount）、`MENGE`（数量 / quantity）、`bwart`（移动类型 / movement type）、`charg`（批次 / batch_code）、`BLDAT`（凭证日期 / document_date） |

### 1.3 ERP 主数据

| 表名 | 用途 |
|------|------|
| `wbs_zmmrp226_parsed` | ERP 需求计划，含项目主数据（项目编码、项目名称、计划类别） |
| `wbs_zmmrp048_parsed` | ERP 项目/物料主数据，含采购人(purchaser_name)、部门(department_name)、项目提交人(project_submitter) |

### 1.4 BI 快照表（`garden_report` schema）

| 表名 | 对应 Python 函数 | 内容 |
|------|-----------------|------|
| `bi_kpi_summary` | `summary.get_summary()` | 核心 KPI 汇总 |
| `bi_claim_indicators` | `claim_indicators.get_claim_indicators()` | 领用率指标（全部历史 / 当年） |
| `bi_structure_indicators` | `structure_indicators.get_structure_indicators()` | 项目/采购人库存占比 |
| `bi_age_indicators` | `time_indicators.get_time_indicators()` | 库龄结构、加权平均库龄 |
| `bi_dimension_project` | `dimension_indicators.get_by_project()` | 按项目维度指标 |
| `bi_dimension_purchaser` | `dimension_indicators.get_by_purchaser()` | 按采购人维度指标 |
| `bi_top_ranking` | `top_indicators.get_top_*()` | TOP 10 排行（4种排名类型） |
| `bi_time_series` | `other_indicators.get_claim_monthly/daily/weekly()` | 领用率时序数据 |
| `bi_batch_digest` | `other_indicators.get_batch_digest()` | 批次消化进度 |
| `bi_anomaly_detection` | `other_indicators.get_anomaly_daily()` | 逐日异常检测 |
| `bi_kpi_checklist` | `kpi_checklist.get_kpi_checklist()` | KPI 考核清单（K1-K9, T1-T2） |
| `bi_safety_stock` | `structure_indicators.get_structure_by_category()` | 安全库存偏离度 |
| `bi_inventory_report` | `other_indicators.get_inventory_report()` | 采购批次库存报表 |
| `bi_category_bubble` | `other_indicators.get_category_bubble()` | 物料类别气泡图数据 |

> 以上 14 张快照表由 `backend/bi_snapshot.py` 每日定时任务写入。

---

## 2. SQL 视图层

### 2.1 维度缓存视图

#### `dim_material_cache`（物料维度缓存）

- **源表**：`wms_material` FULL OUTER JOIN `wbs_zmmrp048_parsed`
- **关键列**：`material_code`（物料编码）、`material_name`（物料名称）、`material_unit`（物料单位）、`material_group_code`（物料组编码）、`material_description`（物料规格描述）

#### `dim_project_cache`（项目维度缓存）

- **源表**：`wbs_zmmrp226_parsed` LEFT JOIN `wbs_zmmrp048_parsed`
- **关键列**：`project_code`（项目编码）、`project_name`（项目名称）、`plan_category`（计划类别）、`purchaser_name`（采购人姓名）、`department_name`（部门名称）、`project_submitter`（项目提交人）、`project_contact`（项目联系人）

#### `dim_outbound_log_cache`（出库日志缓存）

- **源表**：`wms_inventory` JOIN `wms_inventory_log`
- **过滤**：`change_type IN ('31', '34', '35', '36')`
- **关键列**：`tenant_id`（租户ID）、`material_code`（物料编码）、`batch_code`（批次编码）、`erp_inventory`（ERP库存标识）、`total_outbound_quantity`（出库总数量 / total outbound qty）、`pick_quantity`（领用数量 / pick qty, change_type=31）、`repair_quantity`（维修数量 / repair qty, change_type=34）、`scrap_quantity`（报废数量 / scrap qty, change_type=35）、`repaired_quantity`（维修后数量 / repaired qty, change_type=36）

### 2.2 核心宽表

#### `v_project_inventory_wide`（项目库存宽表）— **整个 BI 系统的唯一数据中枢**

- **文件**：`backend/sql/01_v_project_inventory_wide_optimized.sql`
- **构建逻辑**：
  1. `inv_agg` CTE：将 `wms_inventory` 按 `(tenant_id, material_code, batch_code, erp_inventory)` 聚合，消除多货位导致的行膨胀
  2. LEFT JOIN `wms_project_inventory` → 项目归属
  3. LEFT JOIN `dim_material_cache` → 物料名称/规格
  4. LEFT JOIN `dim_project_cache` → 项目名称/采购人
  5. LEFT JOIN `dim_outbound_log_cache` → 出库量

- **视图内计算字段**：

| 字段名 | 计算方式 | 中文说明 |
|--------|---------|---------|
| `v_unit_price` | `SUM(current_quantity × unit_price) / SUM(current_quantity)`（若数量合计为0则取 `MAX(unit_price)`） | 加权平均单价（元） |
| `v_total_price` | `SUM(current_quantity × unit_price)` | 批次库存总金额（元） |
| `age_days` | `EXTRACT(DAY FROM CURRENT_DATE - COALESCE(inbound_date, create_date))` | 库龄（天） |
| `total_outbound_quantity` | 从 `dim_outbound_log_cache` 获取 | 累计出库总数量 |
| `pick_quantity` | change_type=31 的出库量 | 领用出库数量 |
| `repair_quantity` | change_type=34 的出库量 | 维修出库数量 |
| `scrap_quantity` | change_type=35 的出库量 | 报废出库数量 |
| `repaired_quantity` | change_type=36 的出库量 | 维修后出库数量 |

### 2.3 ERP 视图

#### `v_batch_lifecycle`（批次全生命周期）

- **文件**：`backend/sql/04_erp_inventory_views.sql`
- **构建逻辑**：ERP 批次数据（`erp_catalog_mb51` 聚合）FULL OUTER JOIN WMS 批次数据（`v_project_inventory_wide` DISTINCT ON）

| 字段名 | 计算方式 | 中文说明 |
|--------|---------|---------|
| `erp_inbound_amt` | `SUM(DMBTR)` WHERE bwart IN ('101','102') | ERP 入库金额（101毛收货+102冲销） |
| `erp_outbound_amt` | `SUM(DMBTR)` WHERE bwart IN ('201','221','222','Z61','Z62') | ERP 出库金额 |
| `erp_balance_amt` | `SUM(DMBTR)` 全部移动类型净额 | ERP 账面余额 |
| `wms_inventory_amt` | 来自 WMS 的 `v_total_price` | WMS 当前库存金额 |
| `best_inventory_amt` | 若 WMS>0 取 WMS，否则取 `GREATEST(erp_balance_amt, 0)` | **最优库存金额**（WMS优先、ERP兜底） |
| `batch_status` | 枚举：'在库' / 'ERP有余额_WMS无' / '已消耗完' / '负余额_异常' | 批次状态 |
| `erp_wms_gap_amt` | `wms_inventory_amt - erp_balance_amt`（两者都>0时） | ERP与WMS库存差异金额 |

#### `v_monthly_inventory_timeline`（月度库存时间线）

- **源表**：`erp_catalog_mb51`
- **计算**：`SUM(net_amt_change) OVER (ORDER BY month)` 窗口函数，从 2021-05 起逐月累加

---

## 3. Python 计算模块

### 3.1 `utils.py` — 公共工具层（最关键的计算入口）

#### `_BATCH_AMOUNTS_SQL`（utils.py:195）

物理批次去重的 SQL CTE。以 `v_project_inventory_wide` 为源，执行 `DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)`。

| 计算字段 | 公式 | 中文说明 |
|----------|------|---------|
| `batch_inbound` | `original_quantity × unit_price` | 批次入库金额（以当前加权均价重估） |
| `batch_claimed` | `total_outbound_quantity × unit_price` | 批次领用金额 = 四项出库明细之和 |
| `batch_inventory` | `total_price`（即 `v_total_price`） | 批次当前库存金额 |
| `batch_pick` | `pick_quantity × unit_price` | 领用出库金额 |
| `batch_repair` | `repair_quantity × unit_price` | 维修出库金额 |
| `batch_scrap` | `scrap_quantity × unit_price` | 报废出库金额 |
| `batch_repaired` | `repaired_quantity × unit_price` | 维修后出库金额 |

> **恒等式**：`batch_pick + batch_repair + batch_scrap + batch_repaired = batch_claimed`

#### `_PROJECT_RATIO_SQL`

项目分配比例计算 CTE。当一个批次关联多个项目时，按项目库存在该批次中的占比分配。

| 字段 | 公式 | 中文说明 |
|------|------|---------|
| `project_ratio` | `pi_current_quantity / SUM(pi_current_quantity) OVER (同批次)` | 项目分配比例。若无项目数据则回退为 1.0 |

#### `_get_batch_rows()`（utils.py:433）

从 `batch_amounts` CTE 读取所有物理批次的三个核心金额和四个出库明细金额，返回 Python 对象列表。

---

### 3.2 各模块数据流

#### `summary.py` → `get_summary()`

| API 返回字段 | 计算方式 | 中文说明 | 单位 |
|-------------|---------|---------|------|
| `total_inbound_amount` | `Σ(batch_inbound) / 10000` | 入库总金额 | 万元 |
| `total_claimed_amount` | `Σ(batch_claimed) / 10000` | 领用总金额 | 万元 |
| `total_inventory_amount` | `Σ(batch_inventory) / 10000` | **当前库存总金额**（WMS 数据源） | 万元 |
| `claim_rate` | `total_claimed / total_inbound × 100` | 领用率 | % |
| `avg_age_weighted_days` | `Σ(batch_inventory × age_days) / Σ(batch_inventory)` | 金额加权平均库龄 | 天 |
| `aged_amount_1y` | `Σ(batch_inventory WHERE age_days ≥ 365)` | 长库龄库存金额（≥1年） | 元 |
| `aged_ratio_1y` | `aged_amount_1y / Σ(batch_inventory)` | 长库龄库存占比 | 小数 |
| `total_records` | 去重后的批次数 | 批次总数 | 个 |

#### `claim_indicators.py` → `get_claim_indicators()`

按入库日期（`inbound_date`）拆分"全部历史"和"当年"两个维度的领用率。

#### `structure_indicators.py` → `get_structure_indicators()`

| API 返回字段 | 计算方式 | 中文说明 |
|-------------|---------|---------|
| `project_ratios[]` | 每组含 `project_code`（项目编码）、`project_name`（项目名称）、`inventory_amount`（库存金额，=batch_inventory × project_ratio）、`ratio`（占比） | 按项目拆分的库存占比列表 |
| `purchaser_ratios[]` | 同上，按采购人维度聚合 | 按采购人拆分的库存占比列表 |
| `current_inventory_amount` | 按 project_ratio 分配后汇总 | 库存总金额（⚠️ 此口径与 summary 不同，见第9节说明） |

#### `erp_inventory.py` → `get_erp_claim_indicators()`

直接查询 `erp_catalog_mb51`，按 `bwart`（移动类型）聚合。

**`_query_erp_claim_aggregates()`**：

| 聚合字段 | SQL 条件 | 中文说明 |
|----------|---------|---------|
| `gross_inbound` | `bwart = '101'` | 101毛收货金额 |
| `reversal` | `bwart = '102'` | 102冲销金额（负数） |
| `outbound` | `bwart IN ('201','221','222','Z61','Z62')` | 出库金额（含生产领用、销售出库、报废等） |

**`_build_erp_claim_metrics()` 计算公式**：

| 指标 | 公式 | 中文说明 |
|------|------|---------|
| `total_inbound_amount` | `gross_inbound / 10000` | 毛入库总金额（万元） |
| `reversal_amount` | `|reversal| / 10000` | 冲销金额，取绝对值（万元） |
| `net_inbound_amount` | `(gross_inbound + reversal) / 10000` | **净入库** = 101毛收货 + 102冲销（102为负值）（万元） |
| `total_outbound_amount` | `outbound / 10000` | 出库总额（万元） |
| `unclaimed_amount` | `net_inbound - outbound`（换算万元后） | **未领用金额** = 净入库 − 出库（万元） |
| `claim_rate_amount` | `outbound / (gross_inbound + reversal) × 100` | 领用率（按金额）（%） |
| `erp_inventory` | `Σ(best_inventory_amt) / 10000`，来自 `v_batch_lifecycle` | ERP库存金额（WMS优先+ERP兜底）（万元） |

> **核心恒等式**：`101毛收货 − 102冲销 = 净入库 = 出库总额 + 未领用金额`

#### `time_indicators.py` → `get_time_indicators()`

| API 返回字段 | 计算方式 | 中文说明 |
|-------------|---------|---------|
| `age_structure[]` | 按库龄分段统计 `inventory_amount` | 库龄金字塔。`range`（库龄段标签，如"≤1年"、"1~3年"）、`amount`（该段库存金额）、`count`（SKU数） |
| `avg_age_weighted_days` | 同 summary | 加权平均库龄（天） |
| `aged_amount_1y` | 同 summary | ≥1年长库龄金额（元） |
| `aged_ratio_1y` | `aged_amount_1y / total_inventory_amount` | ≥1年长库龄占比 |

---

## 4. Flask API 路由

全部挂载在 `backend/app.py`，前缀 `/api/wms/indicators/`。

### 4.1 核心 KPI（Theme1 相关）

| 路由 | 处理函数 | 说明 |
|------|---------|------|
| `GET /summary` | `summary.get_summary()` | WMS KPI 总览 |
| `GET /claim` | `claim_indicators.get_claim_indicators()` | 领用率指标 |
| `GET /claim/monthly` | `other_indicators.get_claim_monthly()` | 领用率月度趋势 |
| `GET /claim/daily` | `other_indicators.get_claim_daily()` | 领用率日度趋势 |
| `GET /claim/weekly` | `other_indicators.get_claim_weekly()` | 领用率周度趋势 |
| `GET /claim/yearly` | `other_indicators.get_claim_yearly()` | 领用率年度趋势 |
| `GET /structure/by-category` | `structure_indicators.get_structure_by_category()` | 按物料编码的安全库存偏离度 |
| `GET /anomaly/daily` | `other_indicators.get_anomaly_daily()` | 逐日异常检测 |

### 4.2 ERP 相关

| 路由 | 处理函数 | 说明 |
|------|---------|------|
| `GET /erp-claim` | `erp_inventory.get_erp_claim_indicators()` | ERP 领用率（全部/当年拆分） |
| `GET /erp-claim-monthly` | `erp_inventory.get_erp_claim_monthly()` | ERP 领用率月度趋势 |
| `GET /erp-age` | `erp_inventory.get_erp_age_indicators()` | ERP 库龄指标 |
| `GET /erp-age-monthly` | `erp_inventory.get_erp_age_monthly()` | ERP 库龄月度趋势 |

### 4.3 库存结构 & 维度（Theme2 相关）

| 路由 | 处理函数 | 说明 |
|------|---------|------|
| `GET /structure` | `structure_indicators.get_structure_indicators()` | 库存结构（项目/采购人占比） |
| `GET /by-project` | `dimension_indicators.get_by_project()` | 按项目维度 |
| `GET /by-purchaser` | `dimension_indicators.get_by_purchaser()` | 按采购人维度 |
| `GET /category/bubble` | `other_indicators.get_category_bubble()` | 物料类别气泡图 |
| `GET /batch/digest` | `other_indicators.get_batch_digest()` | 批次消化进度 |

### 4.4 库龄时间（Theme3 相关）

| 路由 | 处理函数 | 说明 |
|------|---------|------|
| `GET /time` | `time_indicators.get_time_indicators()` | 库龄时间指标 |
| `GET /age-layers` | `time_indicators.get_age_layers()` | 库龄分层明细 |
| `GET /age/monthly` | `time_indicators.get_age_monthly()` | 库龄月度趋势 |
| `GET /age/heatmap` | `time_indicators.get_age_heatmap()` | 库龄热力图 |

### 4.5 TOP 排行（Theme4 相关）

| 路由 | 处理函数 | 说明 |
|------|---------|------|
| `GET /top/unclaimed-amount` | `top_indicators.get_top_unclaimed_amount()` | 未领用库存 TOP，按金额 |
| `GET /top/unclaimed-quantity` | `top_indicators.get_top_unclaimed_quantity()` | 未领用库存 TOP，按数量 |
| `GET /top/claimed-amount` | `top_indicators.get_top_claimed_amount()` | 领用 TOP，按金额 |
| `GET /top/claimed-quantity` | `top_indicators.get_top_claimed_quantity()` | 领用 TOP，按数量 |
| `GET /optimize-suggest` | `top_indicators.get_optimize_suggest()` | 智能备货优化建议 |

### 4.6 报表 & 交叉分析

| 路由 | 处理函数 | 说明 |
|------|---------|------|
| `GET /inventory-report` | `other_indicators.get_inventory_report()` | 批次库存报表（支持排序分页） |
| `GET /project-summary` | `dimension_indicators.get_project_summary()` | 项目库存追溯汇总表 |
| `GET /purchaser-summary` | `dimension_indicators.get_purchaser_summary()` | 采购人库存追溯汇总表 |
| `GET /source-structure` | `structure_indicators.get_source_structure()` | 库存来源结构表 |
| `GET /kpi-checklist` | `kpi_checklist.get_kpi_checklist()` | KPI 考核清单 |

---

## 5. 前端 API 模块

### 5.1 `frontend/src/api/modules/theme1.ts`

| 导出函数 | 请求路由 | TypeScript 返回类型 | 说明 |
|----------|---------|-------------------|------|
| `getWmsSummary()` | `GET /summary` | `WmsSummary` | WMS 核心 KPI 汇总 |
| `getWmsClaim()` | `GET /claim` | — | WMS 领用率 |
| `getClaimMonthly()` | `GET /claim/monthly` | — | 领用率月度趋势 |
| `getClaimDaily()` | `GET /claim/daily` | — | 领用率日度趋势 |
| `getClaimWeekly()` | `GET /claim/weekly` | — | 领用率周度趋势 |
| `getClaimYearly()` | `GET /claim/yearly` | — | 领用率年度趋势 |
| `getStructureByCategory()` | `GET /structure/by-category` | `{ data: CategoryItem[] }` | 按物料类别安全库存偏离 |
| `getAnomalyDaily()` | `GET /anomaly/daily` | — | 逐日异常检测 |
| `getErpClaim()` | `GET /erp-claim` | `ErpClaimSplit` | ERP 领用率 |
| `getErpClaimMonthly()` | `GET /erp-claim-monthly` | — | ERP 领用率月度 |
| `getErpAge()` | `GET /erp-age` | — | ERP 库龄 |
| `getErpAgeMonthly()` | `GET /erp-age-monthly` | — | ERP 库龄月度 |

> **`WmsSummary` 类型定义**（theme1.ts:76）：
> ```typescript
> {
>   total_inbound_amount: number    // 入库总金额（万元）
>   total_claimed_amount: number    // 领用总金额（万元）
>   total_inventory_amount: number  // 当前库存总金额（万元）← 系统统一数据源
>   claim_rate: number              // 领用率（%）
>   avg_age_weighted_days: number   // 加权平均库龄（天）
>   aged_amount_1y: number          // ≥1年长库龄金额（万元）
>   aged_ratio_1y: number           // ≥1年长库龄占比
>   total_records: number           // 总批次数（去重后）
> }
> ```

> **`ErpClaimSplit` 类型定义**（theme1.ts:155）：
> ```typescript
> {
>   current_year: number            // 当前年份
>   all: ErpClaimPart               // 全部历史指标
>   year: ErpClaimPart              // 当年指标
>   erp_inventory: number           // ERP库存金额（WMS优先+ERP兜底）
> }
> // ErpClaimPart:
> {
>   total_inbound_amount: number    // 毛入库金额（万元）
>   reversal_amount: number         // 冲销金额（万元，正数）
>   net_inbound_amount: number      // 净入库 = inbound + reversal（万元）
>   total_outbound_amount: number   // 出库总金额（万元）
>   unclaimed_amount: number        // 未领用金额 = net - outbound（万元）
>   claim_rate_amount: number       // 领用率按金额（%）
>   claim_rate_quantity: number     // 领用率按数量（%）
> }
> ```

### 5.2 `frontend/src/api/modules/theme2.ts`

| 导出函数 | 请求路由 | TypeScript 返回类型 | 说明 |
|----------|---------|-------------------|------|
| `getStructure()` | `GET /structure` | `WmsStructure` | 库存结构（项目/采购人占比） |
| `getByProject()` | `GET /by-project` | `WmsProjectIndicator[]` | 按项目维度 |
| `getByPurchaser()` | `GET /by-purchaser` | `WmsPurchaserIndicator[]` | 按采购人维度 |
| `getByCategory()` | `GET /category/bubble` | `{ data: WmsCategoryItem[] }` | 物料类别气泡图 |
| `getBatchDigest()` | `GET /batch/digest` | `WmsBatchDigest` | 批次消化进度 |

### 5.3 `frontend/src/api/modules/theme3.ts`

| 导出函数 | 请求路由 | TypeScript 返回类型 | 说明 |
|----------|---------|-------------------|------|
| `getTimeIndicators()` | `GET /time` | `TimeIndicatorsRes` | 库龄时间指标 |
| `getAgeLayers()` | `GET /age-layers` | `AgeLayerItem[]` | 库龄分层明细 |
| `getAgeMonthly()` | `GET /age/monthly` | `AgeMonthlyRes` | 库龄月度趋势 |
| `getAgeHeatmap()` | `GET /age/heatmap` | `AgeHeatmapRes` | 库龄热力图 |

### 5.4 `frontend/src/api/modules/theme4.ts`

| 导出函数 | 请求路由 | 说明 |
|----------|---------|------|
| `getTopUnclaimedAmount()` | `GET /top/unclaimed-amount` | 未领用 TOP，按金额 |
| `getTopUnclaimedQuantity()` | `GET /top/unclaimed-quantity` | 未领用 TOP，按数量 |
| `getTopClaimedAmount()` | `GET /top/claimed-amount` | 领用 TOP，按金额 |
| `getTopClaimedQuantity()` | `GET /top/claimed-quantity` | 领用 TOP，按数量 |
| `getOptimizeSuggest()` | `GET /optimize-suggest` | 备货优化建议 |

### 5.5 其他前端 API 模块

| 模块文件 | 导出函数 | 说明 |
|----------|---------|------|
| `dashboard.ts` | `getSummary()`, `getClaimIndicators()`, `getStructureIndicators()`, `getTimeIndicators()`, `getAgeLayers()`, `getByProject()`, `getByPurchaser()`, `getTopUnclaimedAmount/Quantity()`, `getTopClaimedAmount/Quantity()`, `getDistinctValues()` | 旧版 dashboard 综合模块 |
| `kpiChecklist.ts` | `getKpiChecklist()`, `getKpiChecklistByDateRange()` | KPI 考核清单 |
| `inventoryReport.ts` | `getInventoryReport()`, `getProjectSummary()`, `getPurchaserSummary()`, `getSourceStructure()` | 库存报表 |
| `traceability.ts` | 复用 summary, claim, structure, time, by-project, by-purchaser 等 | 库存追溯模块 |
| `crossAnalysis.ts` | `getProjectMatrix()`, `getProjectTypes()`, `getTopProjects()`, `getProjectTrend()`, `getSourceDistribution()` | 交叉分析 |

---

## 6. 前端页面消费关系

### 6.1 各页面调用的 API 一览

| 页面 | Router 路径 | 调用的 API 函数 |
|------|-----------|----------------|
| **AnalysisHub**（分析总览） | `/analysisboard` | `getWmsSummary()`, `getErpClaim()`, `getClaimMonthly()`, `getClaimDaily()` |
| **Path1PurchaseUse**（采购领用） | `/path1` | `getWmsSummary()`, `getClaimMonthly()`, `getClaimDaily()`, `getTopClaimedAmount()`, `getOptimizeSuggest()` |
| **OperationsMonitor**（运营监控） | `/operationsboard` | `getWmsSummary()`, `getClaimMonthly()`, `getAnomalyDaily()`, `getErpClaim()`, `getStructureByCategory()`, `getTopClaimedAmount()` |
| **Path3AgingCleanup**（库龄清理） | `/path3` | `getWmsSummary()`, `getErpAge()` |
| **BusinessData**（业务数据） | `/businessboard` | `getWmsSummary()`, `getErpClaim()`, `getStructure()`, `getTimeIndicators()`, `getTopUnclaimedAmount()`, `getClaimWeekly()`, `getErpAgeMonthly()` |
| **KpiChecklist**（KPI考核） | `/kpi-checklist` | `getKpiChecklist()`, `getErpClaim()`, `getWmsSummary()` |
| **Theme2**（库存结构） | `/theme2` | `getWmsSummary()`, `getStructure()`, `getByProject()`, `getByPurchaser()`, `getByCategory()`, `getBatchDigest()` |
| **Theme3**（库龄分析） | `/theme3` | `getWmsSummary()`, `getTimeIndicators()`, `getAgeLayers()`, `getByProject()`, `getAgeMonthly()`, `getAgeHeatmap()` |

### 6.2 "当前库存总额"在各页面的使用情况

| 页面 | 变量/组件 | 数据源字段 | 状态 |
|------|----------|-----------|------|
| AnalysisHub | KPI 卡片 | `getWmsSummary().total_inventory_amount` | ✅ 已统一 WMS |
| KpiChecklist | K2 指标 + 总览卡片 | `getWmsSummary().total_inventory_amount` | ✅ 已统一 WMS |
| Path1PurchaseUse | 页面标题下方 | `getWmsSummary().total_inventory_amount` | ✅ 已统一 WMS |
| Path3AgingCleanup | "库存总额 (WMS)" | `getWmsSummary().total_inventory_amount` | ✅ 已统一 WMS |
| Theme1 | — | `getWmsSummary().total_inventory_amount` | ✅ 本来就是 WMS |
| Theme2 | KPI 卡片 "当前库存总额" | `getWmsSummary().total_inventory_amount` | ✅ 已统一 WMS |
| Theme3 | KPI 卡片 "库存总额" | `getWmsSummary().total_inventory_amount` | ✅ 已统一 WMS |
| OperationsMonitor | "当前库存总额" | `getWmsSummary().total_inventory_amount` | ✅ 本来就是 WMS |
| **BusinessData** | "当前库存总额" KPI | `erpClaim.erp_inventory` | ⚠️ **仍为 ERP 混合数据源** |

> **BusinessData 不一致的原因**：`erp_inventory` 来自 `v_batch_lifecycle.best_inventory_amt`，逻辑是「WMS 有库存取 WMS，WMS 无库存但 ERP 有账面余额则取 ERP」。这个兜底会把 "ERP 有账面余额但 WMS 已清理掉的历史批次" 也计入，导致比纯 WMS 口径大。

---

## 7. 字段映射速查表

### 7.1 入库相关

| 数据库层 | Python 层 | API 返回 | 前端 TypeScript | 中文说明 |
|----------|----------|---------|----------------|---------|
| `original_quantity` | `batch_inbound` / 10000 | `total_inbound_amount` | `summary.total_inbound_amount` | 入库总金额（万元） |
| `gross_inbound` (ERP) | `gross_inbound / 10000` | `total_inbound_amount` | `erpClaim.year.total_inbound_amount` | ERP 101毛收货金额（万元） |
| `reversal` (ERP) | `|reversal| / 10000` | `reversal_amount` | `erpClaim.year.reversal_amount` | ERP 102冲销金额（万元） |
| — | `(gross_inbound + reversal) / 10000` | `net_inbound_amount` | `erpClaim.year.net_inbound_amount` | ERP 净入库金额（万元） |

### 7.2 领用/出库相关

| 数据库层 | Python 层 | API 返回 | 前端 TypeScript | 中文说明 |
|----------|----------|---------|----------------|---------|
| `total_outbound_quantity` | `batch_claimed` / 10000 | `total_claimed_amount` | `summary.total_claimed_amount` | 领用总金额（万元） |
| `outbound` (ERP) | `outbound / 10000` | `total_outbound_amount` | `erpClaim.year.total_outbound_amount` | ERP 出库总金额（万元） |
| `pick_quantity` | `batch_pick` / 10000 | — | — | 领用出库金额（change_type=31） |
| `repair_quantity` | `batch_repair` / 10000 | — | — | 维修出库金额（change_type=34） |
| `scrap_quantity` | `batch_scrap` / 10000 | — | — | 报废出库金额（change_type=35） |
| — | `unclaimed_amount` | `unclaimed_amount` | `erpClaim.year.unclaimed_amount` | 未领用金额 = 净入库 − 出库（万元） |

### 7.3 库存相关

| 数据库层 | Python 层 | API 返回 | 前端 TypeScript | 中文说明 |
|----------|----------|---------|----------------|---------|
| `v_total_price` | `batch_inventory` / 10000 | `total_inventory_amount` | `summary.total_inventory_amount` | 当前库存总金额，WMS 单一源（万元） |
| `best_inventory_amt` | `Σ(best_inventory_amt) / 10000` | `erp_inventory` | `erpClaim.erp_inventory` | 最优库存金额，WMS优先+ERP兜底（万元） |
| `total_price` | `inventory_amount` (× project_ratio) | `project_ratios[].inventory_amount` | `structure.project_ratios[].inventory_amount` | 按项目拆分后的库存金额（万元） |

### 7.4 库龄相关

| 数据库层 | Python 层 | API 返回 | 前端 TypeScript | 中文说明 |
|----------|----------|---------|----------------|---------|
| `age_days` | `age_days` | `age_structure[]` 的 range 分组 | — | 库龄天数 |
| — | `Σ(inventory × age_days) / Σ(inventory)` | `avg_age_weighted_days` | `summary.avg_age_weighted_days` | 金额加权平均库龄（天） |
| — | `Σ(inventory WHERE age≥365)` | `aged_amount_1y` | `summary.aged_amount_1y` | ≥1年长库龄金额（万元） |
| — | `aged_amount / total_inventory` | `aged_ratio_1y` | `summary.aged_ratio_1y` | ≥1年长库龄占比 |

### 7.5 领用率相关

| 数据库层 | Python 层 | API 返回 | 前端 TypeScript | 中文说明 |
|----------|----------|---------|----------------|---------|
| — | `Σ(claimed) / Σ(inbound) × 100` | `claim_rate` | `summary.claim_rate` | WMS 领用率（按金额）（%） |
| — | `outbound / net_inbound × 100` | `claim_rate_amount` | `erpClaim.year.claim_rate_amount` | ERP 领用率（按金额）（%） |

---

## 8. 关键计算公式对照

### 8.1 WMS 侧（物理批次级别）

```
batch_inbound   = original_quantity × unit_price                    —— 入库金额
batch_claimed   = total_outbound_quantity × unit_price              —— 领用金额
                   = batch_pick + batch_repair + batch_scrap + batch_repaired
batch_inventory = total_price = Σ(current_quantity × unit_price)    —— 库存金额

项目级别（乘以 project_ratio）:
  project_ratio     = pi_current_quantity / SUM(pi_current_quantity) OVER (同批次)
  inbound_amount    = batch_inbound   × project_ratio
  claimed_amount    = batch_claimed   × project_ratio
  inventory_amount  = batch_inventory × project_ratio

聚合 KPI:
  claim_rate          = Σ(claimed) / Σ(inbound) × 100
  avg_age_weighted    = Σ(inventory × age_days) / Σ(inventory)
  aged_ratio_1y       = Σ(inventory WHERE age≥365) / Σ(inventory)
  identity_check       = |inbound − claimed − inventory| < 总库存的 1%
```

### 8.2 ERP 侧

```
ERP 101毛收货    = SUM(DMBTR) WHERE bwart = '101'                   —— 采购入库
ERP 102冲销      = SUM(DMBTR) WHERE bwart = '102'                   —— 入库冲销（负值）
ERP 出库         = SUM(−DMBTR) WHERE bwart IN ('201','221','222','Z61','Z62')
                   201=生产领用, 221=销售出库, 222=报废出库, Z61/Z62=其他出库

净入库            = 101毛收货 + 102冲销（102为负）                     —— net_inbound
未领用金额        = 净入库 − 出库                                     —— unclaimed_amount
领用率            = 出库 / 净入库 × 100                                —— claim_rate_amount

恒等式：出库总额 + 未领用金额 = 净入库
```

### 8.3 ERP vs WMS 库存差异

```
v_batch_lifecycle.best_inventory_amt:
  IF wms_inventory_amt > 0 → 取 WMS 库存金额
  ELSE → 取 MAX(erp_balance_amt, 0)  ← ERP 账面余额兜底

差异来源：ERP 有账面余额但 WMS 已清理的历史批次
  — WMS 侧：batch 被标记为 del_flag='1' 或 status!=1，从 v_project_inventory_wide 中排除
  — ERP 侧：erp_catalog_mb51 保留全部历史凭证，net_balance 不为 0
```

---

## 9. "当前库存总额"统一改造记录

### 9.1 问题背景

系统中存在两个"当前库存总额"的数据源：

| 数据源 | 来源 | 口径 |
|--------|------|------|
| **WMS** | `getWmsSummary().total_inventory_amount` | 纯 WMS 物理库存聚合：`Σ(v_total_price)`，仅含 `del_flag='0' AND status=1` 的批次 |
| **ERP混合** | `getErpClaim().erp_inventory` | WMS优先 + ERP账面余额兜底（`best_inventory_amt`），包含 "WMS已清理但ERP有余额" 的历史批次 |

### 9.2 改造范围

以下页面已将"当前库存总额"统一切换为 **WMS 数据源**：

| 日期 | 页面 | 改动内容 |
|------|------|---------|
| 2026-08 | AnalysisHub | `erpClaim.erp_inventory` → `getWmsSummary().total_inventory_amount`，标签改"WMS 当前库存金额" |
| 2026-08 | KpiChecklist | K2 指标 + 总览卡片 → `getWmsSummary().total_inventory_amount` |
| 2026-08 | Path3AgingCleanup | 标签"库存总额 (ERP)" → "库存总额 (WMS)"，数据源 `ea.total_inventory_amt` → `wmsSummary.total_inventory_amount` |
| 2026-08 | Theme2 | KPI 卡片新增 `getWmsSummary()` 调用，库存总额 → `wmsSummary.total_inventory_amount` |
| 2026-08 | Theme3 | KPI 卡片新增 `getWmsSummary()` 调用，库存总额 → `wmsSummary.total_inventory_amount` |

### 9.3 未改造项

| 页面 | 当前状态 | 原因 |
|------|---------|------|
| **BusinessData** | 仍使用 `erpClaim.erp_inventory` | 有待确认是否改造。其 tooltip 文字"WMS实物在库 + ERP有余额未入WMS的批次"明确说明了这个混合口径的含义 |

---

## 附录：完整数据流图

```
┌─────────────────────────────────────────────────────────────────────┐
│                     KingbaseES 数据库（人大金仓）                       │
│                                                                     │
│  WMS 原始表                         ERP 原始表                        │
│  ├── wms_inventory                  └── public.erp_catalog_mb51      │
│  ├── wms_inventory_log                 (SAP 物料凭证, werks='2635')  │
│  ├── wms_project_inventory                                          │
│  ├── wms_material                                                    │
│  └── wbs_zmmrp226/048 (ERP主数据)                                    │
│         │                                   │                        │
│         ▼                                   ▼                        │
│  维度缓存视图                          ERP 聚合视图                    │
│  ├── dim_material_cache               ├── v_batch_lifecycle          │
│  ├── dim_project_cache                │   (FULL OUTER JOIN           │
│  ├── dim_location_cache               │    ERP + WMS,                │
│  └── dim_outbound_log_cache           │    best_inventory_amt)       │
│         │                              └── v_monthly_inventory_      │
│         ▼                                  timeline                  │
│  v_project_inventory_wide ←── 核心宽表                                │
│  (WMS 全部指标的唯一数据源)                                            │
│         │                                                            │
├─────────┼────────────────────────────────────────────────────────────┤
│         ▼                                                            │
│  Python 计算层 (backend/*.py)                                         │
│  ├── utils._BATCH_AMOUNTS_SQL  ← 物理批次去重                         │
│  ├── utils._get_batch_rows()   ← 读取批次数据                          │
│  ├── summary.get_summary()     ← KPI 汇总                            │
│  ├── claim_indicators          ← 领用率                               │
│  ├── structure_indicators      ← 库存结构                             │
│  ├── time_indicators           ← 库龄分析                             │
│  ├── dimension_indicators      ← 项目/采购人维度                       │
│  ├── top_indicators            ← TOP 排行                             │
│  ├── other_indicators          ← 时序/异常/报表                        │
│  ├── erp_inventory             ← ERP 领用/库龄                        │
│  └── kpi_checklist             ← KPI 考核清单                         │
│         │                                                            │
├─────────┼────────────────────────────────────────────────────────────┤
│         ▼                                                            │
│  Flask API 层 (app.py)                                                │
│  38 个路由, 前缀 /api/wms/indicators/                                 │
│         │                                                            │
├─────────┼────────────────────────────────────────────────────────────┤
│         ▼                                                            │
│  前端 TypeScript API 模块 (frontend/src/api/modules/)                  │
│  ├── theme1.ts    (12 个接口: summary, claim, erp, anomaly)           │
│  ├── theme2.ts    (5 个接口: structure, by-project, category)         │
│  ├── theme3.ts    (5 个接口: time, age, heatmap)                     │
│  ├── theme4.ts    (5 个接口: top, optimize)                          │
│  └── kpiChecklist.ts / inventoryReport.ts / crossAnalysis.ts         │
│         │                                                            │
├─────────┼────────────────────────────────────────────────────────────┤
│         ▼                                                            │
│  前端页面 (frontend/src/views/)                                       │
│  ├── AnalysisHub/         ← summary + erpClaim + claim monthly/daily │
│  ├── Path1PurchaseUse/    ← summary + claim + topClaimed + optimize  │
│  ├── Path3AgingCleanup/   ← summary + erpAge                         │
│  ├── OperationsMonitor/   ← summary + claim + anomaly + erpClaim     │
│  ├── BusinessData/        ← summary + erpClaim + structure + time    │
│  ├── KpiChecklist/        ← kpiChecklist + erpClaim + summary        │
│  ├── Theme2/              ← summary + structure + byProject + ...    │
│  └── Theme3/              ← summary + time + ageLayers + ...         │
└─────────────────────────────────────────────────────────────────────┘
```
