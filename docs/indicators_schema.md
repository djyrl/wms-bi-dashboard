# 采购库存 BI 仪表盘 — 指标体系与建表文档

> 本文档整理自 `backend/mcp_server.py` 中暴露的 22 个 MCP 工具及其对应的计算模块。
> 数据源：人大金仓 KingbaseES（兼容 PostgreSQL），核心视图 `v_project_inventory_wide`。

---

## 目录

1. [数据基础](#1-数据基础)
2. [表 1：核心汇总指标 `bi_kpi_summary`](#2-表-1核心汇总指标-bi_kpi_summary)
3. [表 2：领用率指标 `bi_claim_indicators`](#3-表-2领用率指标-bi_claim_indicators)
4. [表 3：库存结构指标 `bi_structure_indicators`](#4-表-3库存结构指标-bi_structure_indicators)
5. [表 4：库龄时间指标 `bi_age_indicators`](#5-表-4库龄时间指标-bi_age_indicators)
6. [表 5：项目维度分析 `bi_dimension_project`](#6-表-5项目维度分析-bi_dimension_project)
7. [表 6：采购人维度分析 `bi_dimension_purchaser`](#7-表-6采购人维度分析-bi_dimension_purchaser)
8. [表 7：TOP 排行 `bi_top_ranking`](#8-表-7top-排行-bi_top_ranking)
9. [表 8：时序分析 `bi_time_series`](#9-表-8时序分析-bi_time_series)
10. [表 9：批次消化进度 `bi_batch_digest`](#10-表-9批次消化进度-bi_batch_digest)
11. [表 10：异常检测 `bi_anomaly_detection`](#11-表-10异常检测-bi_anomaly_detection)
12. [表 11：KPI 考核清单 `bi_kpi_checklist`](#12-表-11kpi-考核清单-bi_kpi_checklist)
13. [表 12：安全库存偏离度 `bi_safety_stock`](#13-表-12安全库存偏离度-bi_safety_stock)
14. [表 13：采购批次库存报表 `bi_inventory_report`](#14-表-13采购批次库存报表-bi_inventory_report)
15. [附录 A：核心计算公式汇总](#附录-a核心计算公式汇总)

---

## 1. 数据基础

### 1.1 核心视图

```
v_project_inventory_wide
  ├── inv_agg CTE（1 行/批次，按货位聚合）
  │     ├── v_total_price  = SUM(current_quantity × unit_price)
  │     ├── v_unit_price   = SUM(current_quantity × unit_price) / SUM(current_quantity)
  │     └── age_days       = CURRENT_DATE - COALESCE(inbound_date, create_date)
  └── LEFT JOIN wms_project_inventory（N 行/批次，一个批次可关联多个项目）
        → 视图最终有 N 行/批次（膨胀 N 倍）
```

### 1.2 三个核心金额定义

| 金额 | 字段 | 公式 | 含义 |
|------|------|------|------|
| 入库金额 | `inbound_amount` | `original_quantity × v_unit_price` | 以当前加权均价重估的原始入库价值 |
| 领用金额 | `claimed_amount` | `total_outbound_quantity × v_unit_price` | 以当前加权均价重估的累计出库价值 |
| 库存金额 | `inventory_amount` | `v_total_price = SUM(current_quantity × unit_price)` | 当前库存真实价值（视图直接给出） |

### 1.3 会计恒等式

```
inbound_amount ≈ claimed_amount + inventory_amount
```

推导：
```
inbound  = original_quantity × v_unit_price
         ≈ (current_quantity + total_outbound_quantity) × v_unit_price
         = current_quantity × v_unit_price + total_outbound_quantity × v_unit_price
         = inventory + claimed
```

前提：`original_quantity ≈ current_quantity + total_outbound_quantity`（三者共享同一数据源头 `wms_inventory`）。
实际偏差应在 1% 以内。

### 1.4 去重策略

**⚠️ 严禁直接在 `v_project_inventory_wide` 上 `SUM(total_price)`**，视图行数 = 批次 × 项目，必须先去重再聚合。

所有聚合计算使用统一的 `_BATCH_AMOUNTS_SQL` CTE：

```sql
DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
    original_quantity * unit_price       AS batch_inbound,
    total_outbound_quantity * unit_price AS batch_claimed,
    total_price                         AS batch_inventory,
    ...
FROM v_project_inventory_wide
```

### 1.5 项目金额分配

当需要按项目维度拆分时，使用 `project_ratio` 因子：

```sql
project_ratio = CASE
    WHEN 该批次无项目台账行 → 1.0
    WHEN 所有项目 pi_current_quantity = 0 → 平均分配
    ELSE pi_current_quantity / SUM(pi_current_quantity) OVER (批次窗口)
END
```

性质：同一批次所有 `project_ratio` 之和 = 1.0，因此项目级汇总 = 批次级汇总。

### 1.6 出库类型

| change_type | 字段 | 含义 |
|-------------|------|------|
| 31 | `pick_quantity` | 拣货出库 |
| 34 | `repair_quantity` | 维修出库 |
| 35 | `scrap_quantity` | 报废出库 |
| 36 | `repaired_quantity` | 返修出库 |

恒等式：`total_outbound = pick + repair + scrap + repaired`

---

## 2. 表 1：核心汇总指标 `bi_kpi_summary`

### 2.1 建表语句

```sql
CREATE TABLE bi_kpi_summary (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,  -- 快照日期

    -- 核心金额（万元）
    total_inbound_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 入库总额
    total_claimed_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 领用总额
    total_inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 当前库存金额

    -- 数量 & 批次
    total_inventory_quantity NUMERIC(16,2) NOT NULL DEFAULT 0, -- 库存总数量
    total_records            INTEGER NOT NULL DEFAULT 0,       -- 批次总条数

    -- 派生指标
    claim_rate              NUMERIC(6,2) NOT NULL DEFAULT 0,   -- 综合领用率(%)
    aged_amount_1y          NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 库龄≥1年库存金额(万元)
    aged_ratio_1y           NUMERIC(6,2) NOT NULL DEFAULT 0,   -- 长库龄占比(%)
    avg_age_weighted_days   NUMERIC(10,2) NOT NULL DEFAULT 0,  -- 金额加权平均库龄(天)

    -- 恒等式校验
    identity_inbound_minus_claimed NUMERIC(16,2),  -- inbound - claimed (万元)
    identity_actual_inventory      NUMERIC(16,2),  -- 实际库存 (万元)
    identity_deviation_wan         NUMERIC(16,4),  -- 偏差(万元)
    identity_deviation_pct         NUMERIC(8,4),   -- 偏差(%)
    identity_holds                 BOOLEAN,         -- 恒等式是否成立(偏差<1%)

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

COMMENT ON TABLE bi_kpi_summary IS 'KPI总览核心汇总指标';
COMMENT ON COLUMN bi_kpi_summary.total_inbound_amount IS '入库总额(万元)，所有批次 original_quantity × v_unit_price 求和';
COMMENT ON COLUMN bi_kpi_summary.claim_rate IS '综合领用率(%) = claimed / inbound × 100';
COMMENT ON COLUMN bi_kpi_summary.avg_age_weighted_days IS '金额加权平均库龄(天) = Σ(inventory_amount × age_days) / Σ(inventory_amount)';
```

### 2.2 指标详细计算方式

#### 2.2.1 数据获取

```sql
-- 一次查询所有批次数据，在 Python 内存中聚合
SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
    original_quantity * unit_price       AS batch_inbound,
    total_outbound_quantity * unit_price AS batch_claimed,
    total_price                         AS batch_inventory,
    original_quantity                   AS batch_orig_qty,
    age_days
FROM v_project_inventory_wide;
```

#### 2.2.2 计算步骤

| 步骤 | 指标 | 公式 | 说明 |
|------|------|------|------|
| 1 | 入库总额 | `Σ batch_inbound` | 遍历所有批次行求和（元） |
| 2 | 领用总额 | `Σ batch_claimed` | 同上 |
| 3 | 库存总额 | `Σ batch_inventory` | 同上 |
| 4 | 库存总数量 | `Σ batch_orig_qty` | 原始数量总和 |
| 5 | 加权平均库龄 | `Σ(inventory × age_days) / Σ(inventory)` | 以库存金额为权重，反映「钱在仓库放了多久」 |
| 6 | 长库龄占比 | `Σ(inventory WHERE age_days ≥ 365) / Σ(inventory) × 100` | 库龄≥1年的库存金额占比 |
| 7 | 综合领用率 | `claimed / inbound × 100` | 入库物资中有多少被领用 |
| 8 | 恒等式校验 | `inbound - claimed ≈ inventory` | 偏差 < 1% 视为成立 |

#### 2.2.3 返回示例

```json
{
  "total_inbound_amount": 12500.00,
  "total_claimed_amount": 8750.00,
  "total_inventory_amount": 3750.00,
  "total_inventory_quantity": 150000.00,
  "total_records": 3200,
  "claim_rate": 70.00,
  "aged_amount_1y": 1125.00,
  "aged_ratio_1y": 30.00,
  "avg_age_weighted_days": 385.50,
  "identity_check": { "holds": true, "deviation_pct": 0.05 }
}
```

---

## 3. 表 2：领用率指标 `bi_claim_indicators`

### 3.1 建表语句

```sql
CREATE TABLE bi_claim_indicators (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    period_type     VARCHAR(10) NOT NULL,  -- 'all' = 全部批次, 'year' = 当年
    current_year    INTEGER NOT NULL,       -- 当前年份

    -- 金额领用率
    total_inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 入库总额(万元)
    total_claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 领用总额(万元)
    claim_rate_amount      NUMERIC(6,2)  NOT NULL DEFAULT 0,  -- 金额领用率(%)

    -- 数量领用率
    total_inbound_quantity  NUMERIC(16,2) NOT NULL DEFAULT 0, -- 入库总数量
    total_claimed_quantity  NUMERIC(16,2) NOT NULL DEFAULT 0, -- 领用总数量
    claim_rate_quantity     NUMERIC(6,2)  NOT NULL DEFAULT 0, -- 数量领用率(%)

    -- 未领用
    unclaimed_amount       NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 未领用金额(万元)
    unclaimed_amount_ratio NUMERIC(6,2)  NOT NULL DEFAULT 0,  -- 未领用占比(%)

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, period_type)
);

COMMENT ON TABLE bi_claim_indicators IS '采购领用率指标（按全部/当年拆分）';
COMMENT ON COLUMN bi_claim_indicators.period_type IS 'all=全部历史批次, year=当年入库批次';
COMMENT ON COLUMN bi_claim_indicators.claim_rate_amount IS '金额领用率(%) = claimed / inbound × 100';
COMMENT ON COLUMN bi_claim_indicators.unclaimed_amount IS '未领用金额(万元) = inbound - claimed，恒等式下≈当前库存';
```

### 3.2 指标详细计算方式

#### 3.2.1 当年定义

`inbound_date` 所在自然年 = 当前年。例如 2026 年入库的批次。

#### 3.2.2 SQL 计算

```sql
WITH batch_amounts AS (
    SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
        original_quantity * unit_price       AS batch_inbound,
        total_outbound_quantity * unit_price AS batch_claimed,
        total_price                         AS batch_inventory,
        original_quantity                   AS batch_orig_qty,
        total_outbound_quantity             AS batch_outbound_qty,
        inbound_date
    FROM v_project_inventory_wide
)
SELECT
    -- 「全部」汇总
    SUM(batch_inbound)                                     AS inbound_all,
    SUM(batch_claimed)                                     AS claimed_all,
    SUM(batch_inventory)                                   AS inventory_all,
    SUM(batch_orig_qty)                                    AS orig_qty_all,
    SUM(batch_outbound_qty)                                AS outbound_qty_all,
    -- 「当年」汇总（按 inbound_date 年份筛选）
    SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
             THEN batch_inbound ELSE 0 END)                AS inbound_year,
    SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
             THEN batch_claimed ELSE 0 END)                AS claimed_year,
    ...
FROM batch_amounts;
```

#### 3.2.3 派生指标公式

| 指标 | 公式 | 说明 |
|------|------|------|
| 金额领用率 | `claimed / inbound × 100%` | 已领用金额占入库金额的比例 |
| 数量领用率 | `outbound_qty / original_qty × 100%` | 已领用数量占入库数量的比例 |
| 未领用金额 | `inbound - claimed`（万元） | 恒等式下 ≈ 当前库存金额 |
| 未领用占比 | `(inbound - claimed) / inbound × 100%` | 未领用比例 |

---

## 4. 表 3：库存结构指标 `bi_structure_indicators`

### 4.1 建表语句

```sql
CREATE TABLE bi_structure_indicators (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    current_year    INTEGER NOT NULL,

    -- 汇总金额（万元）
    current_inventory_amount       NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 全部库存金额
    current_year_inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 当年入库库存金额
    current_inventory_quantity     NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 库存总数量

    -- 项目/采购人占比（JSON，存储 TOP 10）
    project_ratios_json    JSONB,  -- [{project_code, project_name, inventory_amount, ratio}, ...]
    purchaser_ratios_json  JSONB,  -- [{purchaser_name, inventory_amount, ratio}, ...]

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

COMMENT ON TABLE bi_structure_indicators IS '库存结构指标（全部/当年库存、项目/采购人占比）';
```

### 4.2 指标详细计算方式

#### 4.2.1 计算流程

```
Step 1: batch_amounts CTE（批次去重）
Step 2: wide_with_ratio（JOIN 回视图，× project_ratio 分配）
Step 3: 按项目 / 采购人 GROUP BY 聚合
Step 4: 计算占比 = 维度库存金额 / 总库存金额
```

#### 4.2.2 项目库存占比

```sql
SELECT
    owner_project_code,
    MAX(project_name) AS project_name,
    SUM(batch_inventory * project_ratio) AS inventory_amount
FROM wide_with_ratio
GROUP BY owner_project_code
ORDER BY inventory_amount DESC;
```

占比 = `项目库存金额 / 总库存金额`

#### 4.2.3 采购人库存占比

```sql
SELECT
    purchaser_name,
    SUM(batch_inventory * project_ratio) AS inventory_amount
FROM wide_with_ratio
WHERE purchaser_name IS NOT NULL
GROUP BY purchaser_name
ORDER BY inventory_amount DESC;
```

占比 = `采购人库存金额 / 总库存金额`

---

## 5. 表 4：库龄时间指标 `bi_age_indicators`

### 5.1 建表语句

```sql
CREATE TABLE bi_age_indicators (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,

    -- 核心指标
    aged_ratio_1y           NUMERIC(8,4)  NOT NULL DEFAULT 0,  -- 长库龄占比(比例，如0.15)
    aged_amount_1y          NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 长库龄金额(元)
    avg_age_weighted_days   NUMERIC(10,2) NOT NULL DEFAULT 0,  -- 加权平均库龄(天)

    -- 库龄结构分段（JSON）
    age_structure_json      JSONB NOT NULL DEFAULT '[]',  -- [{range, amount, ratio, count}, ...]

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

COMMENT ON TABLE bi_age_indicators IS '库龄时间指标（长库龄占比、库龄结构、加权平均库龄）';
```

### 5.2 指标详细计算方式

#### 5.2.1 库龄分段定义

| 段 | 范围 |
|----|------|
| ≤1年 | 0 ≤ age_days < 365 |
| 1~3年 | 365 ≤ age_days < 1095 |
| 3~5年 | 1095 ≤ age_days < 1825 |
| ≥5年 | 1825 ≤ age_days |

#### 5.2.2 计算公式

| 指标 | 公式 | 说明 |
|------|------|------|
| 加权平均库龄 | `Σ(inventory_amount × age_days) / Σ(inventory_amount)` | 以库存金额为权重 |
| 长库龄占比 | `Σ(inventory WHERE age_days ≥ 365) / Σ(inventory)` | 所有≥1年段的占比之和 |
| 各段金额 | `Σ(inventory WHERE min_age ≤ age_days < max_age)` | 该库龄段内所有批次的库存金额 |
| 各段占比 | `各段金额 / 总库存金额` | |
| 各段批次数 | `COUNT(rows WHERE min_age ≤ age_days < max_age)` | 该段内的批次数量 |

#### 5.2.3 库龄分层明细（`get_age_layers`）

按 `min_amount`（最小库存金额）、`min_age`（最小库龄）、`max_age`（最大库龄）筛选，返回项目级明细行：

```
get_inventory_rows() → 筛选: inventory_amount ≥ min_amount AND age ≥ min_age AND age ≤ max_age
→ 按 inventory_amount 降序排列
```

#### 5.2.4 平均库龄月度趋势（`get_age_monthly`）

对最近 12 个月的每个月末，回溯「当月已入库」的批次：

| 指标 | 公式 | 说明 |
|------|------|------|
| 当月加权平均库龄 | `Σ(inbound_amount × 月末库龄) / Σ(inbound_amount)` | 以入库金额为权重，反映该月入库物资的库龄水平 |
| 超 90 天占比 | `Σ(inbound_amount WHERE 月末库龄 ≥ 90) / Σ(inbound_amount)` | |

#### 5.2.5 滞留库存热力图（`get_age_heatmap`）

按物料类别 × 库龄段交叉统计库存金额：

```
库龄段（6段）：0-30天, 30-60天, 60-90天, 90-180天, 180-365天, >365天
物料类别：TOP 10（按总库存金额降序）
矩阵：行=库龄段，列=类别，值=库存金额(万元)
```

---

## 6. 表 5：项目维度分析 `bi_dimension_project`

### 6.1 建表语句

```sql
CREATE TABLE bi_dimension_project (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    project_code    VARCHAR(100) NOT NULL,
    project_name    VARCHAR(200),

    -- 核心金额（元）
    inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 入库金额（项目分配后）
    claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 领用金额（项目分配后）
    inventory_amount NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 未消耗库存金额（项目分配后）

    -- 派生指标
    claim_rate       NUMERIC(6,2),   -- 领用率(%) = claimed / inbound × 100，上限100%
    avg_age_days     NUMERIC(10,2),  -- 金额加权平均库龄(天)
    over90_ratio     NUMERIC(6,2),   -- 库龄≥90天占比(%)
    record_count     INTEGER,        -- 记录数

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, project_code)
);

COMMENT ON TABLE bi_dimension_project IS '项目维度分析（每项目的领用率、库存、库龄）';
COMMENT ON COLUMN bi_dimension_project.inventory_amount IS '未消耗库存金额(元) = 批次库存 × project_ratio 分配后';
COMMENT ON COLUMN bi_dimension_project.claim_rate IS '领用率(%) = claimed / inbound × 100';
```

### 6.2 指标详细计算方式

#### 6.2.1 SQL 计算流程

```sql
WITH batch_amounts AS (...),  -- 批次去重
wide_with_ratio AS (
    SELECT
        w.owner_project_code AS project_code,
        w.project_name,
        ba.batch_inbound,
        ba.batch_claimed,
        ba.batch_inventory,
        ba.batch_age_days,
        project_ratio        -- 按 pi_current_quantity 占比
    FROM v_project_inventory_wide w
    JOIN batch_amounts ba ON ...
)
SELECT
    project_code,
    MAX(project_name) AS project_name,
    SUM(batch_inbound * project_ratio)   AS inbound_amt,
    SUM(batch_claimed * project_ratio)   AS claimed_amt,
    SUM(batch_inventory * project_ratio) AS inventory_amt,
    SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted,
    SUM(CASE WHEN batch_age_days >= 90
        THEN batch_inventory * project_ratio ELSE 0 END) AS over90_amt,
    COUNT(*) AS record_count
FROM wide_with_ratio
GROUP BY project_code
ORDER BY inventory_amt DESC;
```

#### 6.2.2 派生指标公式

| 指标 | 公式 |
|------|------|
| 领用率 | `claimed / inbound × 100`（上限 100%） |
| 加权平均库龄 | `Σ(inventory × age_days) / Σ(inventory)` |
| 超90天占比 | `Σ(inventory WHERE age ≥ 90) / Σ(inventory) × 100` |

---

## 7. 表 6：采购人维度分析 `bi_dimension_purchaser`

### 7.1 建表语句

```sql
CREATE TABLE bi_dimension_purchaser (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    purchaser_name  VARCHAR(200) NOT NULL,  -- 采购人/联系人名称

    -- 核心金额（元）
    inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    inventory_amount NUMERIC(16,2) NOT NULL DEFAULT 0,

    -- 派生指标
    claim_rate       NUMERIC(6,2),
    avg_age_days     NUMERIC(10,2),
    record_count     INTEGER,

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, purchaser_name)
);

COMMENT ON TABLE bi_dimension_purchaser IS '采购人维度分析（按 project_contact 聚合）';
```

### 7.2 指标详细计算方式

与项目维度分析逻辑相同，但按 `project_contact`（项目联系人）聚合：

```sql
SELECT
    project_contact AS purchaser_name,
    SUM(batch_inbound * project_ratio)   AS inbound_amt,
    SUM(batch_claimed * project_ratio)   AS claimed_amt,
    SUM(batch_inventory * project_ratio) AS inventory_amt,
    SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted,
    COUNT(*) AS record_count
FROM wide_with_ratio
WHERE project_contact IS NOT NULL
GROUP BY project_contact
ORDER BY inventory_amt DESC;
```

---

## 8. 表 7：TOP 排行 `bi_top_ranking`

### 8.1 建表语句

```sql
CREATE TABLE bi_top_ranking (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    rank_type       VARCHAR(30) NOT NULL,  -- 排行类型
    rank_position   INTEGER NOT NULL,      -- 排名

    -- 物料信息
    material_code   VARCHAR(100),
    material_name   VARCHAR(200),
    batch_code      VARCHAR(100),

    -- 金额/数量
    inventory_amount  NUMERIC(16,2),       -- 库存金额(元)
    current_quantity  NUMERIC(16,2),       -- 当前库存数量
    claimed_amount    NUMERIC(16,2),       -- 领用金额(元)
    claimed_quantity  NUMERIC(16,2),       -- 领用数量
    inbound_amount    NUMERIC(16,2),       -- 入库金额(元)

    -- 维度信息
    unit_price       NUMERIC(16,4),
    unit             VARCHAR(20),
    age_days         INTEGER,
    inbound_date     DATE,
    project_code     VARCHAR(100),
    project_name     VARCHAR(200),
    purchaser_name   VARCHAR(200),

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, rank_type, rank_position)
);

COMMENT ON TABLE bi_top_ranking IS 'TOP排行（未领用/已领用，按金额/数量）';
COMMENT ON COLUMN bi_top_ranking.rank_type IS 'unclaimed_amount=未领用金额TOP, unclaimed_quantity=未领用数量TOP, claimed_amount=领用金额TOP, claimed_quantity=领用数量TOP';
```

### 8.2 指标详细计算方式

#### 8.2.1 未领用库存 TOP（金额）

```
数据源：_get_inventory_rows()（项目级明细）
排序：按 inventory_amount 降序
取 TOP N（默认 10）
```

#### 8.2.2 未领用库存 TOP（数量）

```
数据源：_get_inventory_rows()
排序：按 current_quantity 降序
取 TOP N（默认 10）
```

#### 8.2.3 领用 TOP（金额）

```
数据源：_get_inventory_rows()
聚合：按 material_code 汇总 claimed_amount
排序：按 claimed_amount 降序
取 TOP N（默认 10）
```

#### 8.2.4 领用 TOP（数量）

```
数据源：_get_inventory_rows()
聚合：按 material_code 汇总 used_quantity
排序：按 used_quantity 降序
取 TOP N（默认 10）
```

#### 8.2.5 智能备货优化建议（`get_optimize_suggest`）

| 步骤 | 计算 | 公式 |
|------|------|------|
| 1 | 按物料汇总 | 对每个 material_code，求和 current(库存金额)、claimed(已领用金额)、age_weighted(金额×库龄) |
| 2 | 加权平均库龄 | `avg_age = Σ(age_weighted) / Σ(inventory_total)` |
| 3 | 日均消耗 | `daily_use = (claimed / avg_age) / 10000`（万元/天） |
| 4 | 建议上限 | `max_stock = daily_use × safety_days`（默认 60 天） |
| 5 | 筛选超标 | 只保留 `current_wan > max_stock` 的物料 |
| 6 | 排序 | 按超出量 `current - maxStock` 降序 |

---

## 9. 表 8：时序分析 `bi_time_series`

### 9.1 建表语句

```sql
CREATE TABLE bi_time_series (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    granularity     VARCHAR(10) NOT NULL,  -- 'monthly' / 'daily' / 'weekly'
    period_label    VARCHAR(30) NOT NULL,  -- 时间标签，如 '2026-01', '2026-01-15', '2026-W03'

    -- 核心金额（元）
    inbound_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 入库金额
    claimed_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 领用金额
    net_amount      NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 净额 = inbound - claimed

    -- 派生指标
    claim_rate      NUMERIC(6,2) NOT NULL DEFAULT 0,   -- 领用率(%)

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, granularity, period_label)
);

COMMENT ON TABLE bi_time_series IS '时序分析（月/日/周粒度的入库、领用、领用率趋势）';
COMMENT ON COLUMN bi_time_series.granularity IS 'monthly=月度, daily=日度, weekly=周度';
```

### 9.2 指标详细计算方式

#### 9.2.1 月度趋势（`get_claim_monthly`）

```python
# 数据源：_get_inventory_rows()
# 按 putaway_date 或 inbound_date 聚合到月份
month_key = date.strftime("%Y-%m")
monthly[month_key].inbound += row["inbound_amount"]
monthly[month_key].claimed += row["claimed_amount"]

# 领用率
claim_rate = claimed / inbound × 100

# 取最近 12 个月
```

#### 9.2.2 日度趋势（`get_claim_daily`）

```python
# 时间范围：上个月第一天 → 今天
# 按 inbound_date 聚合到天
day_key = date.strftime("%Y-%m-%d")
# 领用率 = claimed / inbound × 100
```

#### 9.2.3 周度趋势（`get_claim_weekly`）

```python
# 时间范围：最近 12 周
# 按 ISO 周聚合
week_key = f"{iso_year}-W{iso_week:02d}"
# 领用率 = claimed / inbound × 100
```

---

## 10. 表 9：批次消化进度 `bi_batch_digest`

### 10.1 建表语句

```sql
CREATE TABLE bi_batch_digest (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    batch_code      VARCHAR(100) NOT NULL,

    -- 核心数据
    inbound_wan     NUMERIC(16,2) NOT NULL DEFAULT 0,   -- 入库金额(万元)
    remain_pct      NUMERIC(6,2)  NOT NULL DEFAULT 0,   -- 剩余占比(%)
    avg_age_days    INTEGER,                             -- 平均库龄(天)

    -- 逐月消化数据（JSON）
    digest_data_json JSONB NOT NULL DEFAULT '[]',        -- [100, 95, 88, ...] 百分比序列

    -- 颜色标识
    color_hex       VARCHAR(7),

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, batch_code)
);

COMMENT ON TABLE bi_batch_digest IS '批次消化进度（TOP 6批次，按入库金额降序）';
```

### 10.2 指标详细计算方式

```python
# 取 TOP 6 批次（按入库金额降序）
SELECT batch_code, SUM(inbound_amt), SUM(remain_amt), AVG(age_days)
FROM distinct_inventory
GROUP BY batch_code
ORDER BY inbound_amt DESC LIMIT 6;

# 对每个批次，模拟逐月消化：
total_remain_pct = remain / inbound × 100
months = max(age_days / 30, 1)
monthly_consume_rate = (100 - total_remain_pct) / months

# 生成 7 个数据点：[入库月, +1月, +2月, ..., +6月]
data[m] = max(0, 100 - monthly_consume_rate × m)
```

---

## 11. 表 10：异常检测 `bi_anomaly_detection`

### 11.1 建表语句

```sql
CREATE TABLE bi_anomaly_detection (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    week_label      VARCHAR(30) NOT NULL,  -- 周标签，如 '3/1-3/7'

    -- 金额（万元）
    inbound_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    claimed_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,

    -- 异常判定
    anomaly_type    INTEGER NOT NULL DEFAULT 0,  -- 0=正常, 1=异常
    anomaly_label   VARCHAR(500),                -- 异常描述，如 '新项目(XX项目);环比↑35%'
    huanbi_pct      NUMERIC(6,2),                -- 周度环比变化(%)

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, week_label)
);

COMMENT ON TABLE bi_anomaly_detection IS '异常检测（近12周，新项目+周度环比超±30%）';
```

### 11.2 指标详细计算方式

#### 11.2.1 检测维度

| 维度 | 检测逻辑 | 判定条件 |
|------|----------|----------|
| 新项目 | 近 N 天（默认 30）内有新项目创建 | 项目 `create_date` 在 `today - N天` 之后 |
| 周度环比 | 本周领用 vs 上周领用 | 波动超 ±30% |

#### 11.2.2 计算流程

```python
# Step 1: 新项目检测
SELECT owner_project_code, MIN(create_date)::date AS first_date
FROM v_project_inventory_wide
WHERE owner_project_code IS NOT NULL
GROUP BY owner_project_code;

# 筛选 first_date >= today - days 的项目，标记对应 ISO 周

# Step 2: 按 ISO 周聚合（近 16 周，为环比留余量）
week_key = f"{iso_year}-W{iso_week:02d}"
week_map[week_key].inbound += row["inbound_amount"]
week_map[week_key].claimed += row["claimed_amount"]

# Step 3: 逐周判定
huanbi = (本周claimed - 上周claimed) / 上周claimed × 100
if abs(huanbi) > 30: 异常

# 返回最近 12 周
```

---

## 12. 表 11：KPI 考核清单 `bi_kpi_checklist`

### 12.1 建表语句

```sql
CREATE TABLE bi_kpi_checklist (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,

    -- 汇总信息
    total_inbound_wan       NUMERIC(16,2),  -- 入库总额(万元)
    total_claimed_wan       NUMERIC(16,2),  -- 领用总额(万元)
    current_inventory_wan   NUMERIC(16,2),  -- 当前库存(万元)
    overall_claim_rate      NUMERIC(6,2),   -- 综合领用率(%)
    aged_ratio_1y           NUMERIC(6,2),   -- 长库龄占比(%)

    -- 考核状态统计
    ok_count      INTEGER,   -- 达标数
    warning_count INTEGER,   -- 预警数
    alert_count   INTEGER,   -- 未达标数

    -- 恒等式校验
    identity_deviation_pct NUMERIC(8,4),
    identity_holds         BOOLEAN,

    -- 各指标详情（JSONB）
    core_kpis_json        JSONB,  -- K1-K3
    constraint_kpis_json  JSONB,  -- K4-K5
    structure_kpis_json   JSONB,  -- K6-K9
    top_kpis_json         JSONB,  -- T1-T2

    data_start_date  DATE,
    data_end_date    DATE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

COMMENT ON TABLE bi_kpi_checklist IS 'KPI考核清单（K1-K9 + T1-T2）';
```

### 12.2 指标结构

#### 第一类：核心考核指标 K1-K3

| 编号 | 名称 | 公式 | 目标 | 方向 |
|------|------|------|------|------|
| K1 | 采购领用率（金额） | `claimed / inbound × 100%` | ≥80% | 越高越好 |
| K2 | 当前库存金额 | `SUM(current_quantity × unit_price)` | 控制上限 | 越低越好 |
| K3 | 长库龄库存金额占比 | `库存≥1年金额 / 总库存 × 100%` | 逐年下降 | 越低越好 |

#### 第二类：约束类指标 K4-K5

| 编号 | 名称 | 公式 | 目标 |
|------|------|------|------|
| K4 | 未领用采购金额 | `inbound - claimed`（万元） | 控制新增库存 |
| K5 | 项目未消耗库存 | `Σ(owner_project_type='Q' 的 inventory_amount)`（万元） | 项目采购约束 |

#### 第三类：结构分析指标 K6-K9

| 编号 | 名称 | 内容 |
|------|------|------|
| K6 | 库存结构分析 | 项目库存占比 TOP 10 + 采购人库存占比 TOP 10 |
| K7 | 时间分析 | 平均库龄、未动用天数、库龄结构 |
| K8 | 项目分析 | 所有项目的领用率、库存、库龄 |
| K9 | 采购人分析 | 所有采购人的领用率、库存、库龄 |

#### 第四类：TOP 指标 T1-T2（不纳入考核）

| 编号 | 名称 | 内容 |
|------|------|------|
| T1 | 未领用库存 TOP 10（金额） | 按物料编码聚合，金额降序 |
| T2 | 领用 TOP 10 | 分两组：按金额 + 按数量 |

#### 12.2.3 状态判定规则

```python
def _status(rate, target, direction):
    if direction == "up":
        if rate >= target: return "ok"        # 达成
        elif rate >= target * 0.85: return "warning"  # 达成85%以上
        else: return "alert"                  # 未达成
    else:  # direction == "down"
        if rate <= target: return "ok"
        elif rate <= target * 1.15: return "warning"
        else: return "alert"
```

#### 12.2.4 未动用天数（K7 子指标）

定义：`claimed_amount = 0` 且 `current_quantity > 0` 的库存为「未动用」。

```
未动用天数 = Σ(未动用库存金额 × 库龄) / Σ(未动用库存金额)
```

---

## 13. 表 12：安全库存偏离度 `bi_safety_stock`

### 13.1 建表语句

```sql
CREATE TABLE bi_safety_stock (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    rank_position   INTEGER NOT NULL,     -- 排名（1-10, 99=其他）

    material_code   VARCHAR(100) NOT NULL,
    category_name   VARCHAR(200),         -- 物料名称（来自 dim_material_cache）

    -- 库存金额（元）
    current_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,

    -- 安全库存上下限（元）
    safe_max        NUMERIC(16,2) NOT NULL DEFAULT 0,
    safe_min        NUMERIC(16,2) NOT NULL DEFAULT 0,

    record_count    INTEGER,              -- 批次数

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, material_code)
);

COMMENT ON TABLE bi_safety_stock IS '安全库存偏离度（按物料编码，TOP 10+其他）';
COMMENT ON COLUMN bi_safety_stock.safe_max IS '安全上限 = mean_amt × 1.5（TOP 10物料平均库存的1.5倍）';
COMMENT ON COLUMN bi_safety_stock.safe_min IS '安全下限 = mean_amt × 0.5（TOP 10物料平均库存的0.5倍）';
```

### 13.2 指标详细计算方式

```python
# 按物料编码聚合库存金额
rows = query("""
    SELECT material_code, SUM(batch_inventory) AS amt, COUNT(*) AS cnt
    FROM batch_amounts
    GROUP BY material_code
    ORDER BY amt DESC
""")

# 取 TOP 10
top_rows = rows[:10]
amounts = [r["amt"] for r in top_rows]
mean_amt = sum(amounts) / len(amounts)

# 计算安全上下限
safe_max = mean_amt * 1.5  # 超过此值表示积压
safe_min = mean_amt * 0.5  # 低于此值表示不足

# 剩余归为「其他」
rest = sum(r["amt"] for r in rows[10:])
```

---

## 14. 表 13：采购批次库存报表 `bi_inventory_report`

### 14.1 建表语句

```sql
CREATE TABLE bi_inventory_report (
    id                  SERIAL PRIMARY KEY,
    snapshot_date       DATE NOT NULL DEFAULT CURRENT_DATE,

    -- 基本信息
    purchase_batch      VARCHAR(100),  -- 采购批次号
    material_name       VARCHAR(200),
    material_code       VARCHAR(100),
    project_code        VARCHAR(100),
    project_name        VARCHAR(200),
    purchaser_name      VARCHAR(200),
    submitter_name      VARCHAR(200),
    contact_name        VARCHAR(200),
    project_type        VARCHAR(100),

    -- 日期
    inbound_date        DATE,
    putaway_date        DATE,
    batch_code          VARCHAR(100),

    -- 数量
    original_quantity   NUMERIC(16,4),
    current_quantity    NUMERIC(16,4),
    used_quantity       NUMERIC(16,4),  -- 已领用数量
    pick_quantity       NUMERIC(16,4),  -- 拣货数量
    repair_quantity     NUMERIC(16,4),  -- 维修数量
    scrap_quantity      NUMERIC(16,4),  -- 报废数量
    repaired_quantity   NUMERIC(16,4),  -- 返修数量

    -- 单价
    unit_price          NUMERIC(16,4),
    unit                VARCHAR(20),
    supplier_code       VARCHAR(100),

    -- 金额（元）
    inbound_amount      NUMERIC(16,2),
    claimed_amount      NUMERIC(16,2),
    inventory_amount    NUMERIC(16,2),

    -- 派生指标
    claim_rate          NUMERIC(6,2),   -- 领用率(%)
    age_days            INTEGER,        -- 库龄(天)

    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inventory_report_snapshot ON bi_inventory_report(snapshot_date);
CREATE INDEX idx_inventory_report_material ON bi_inventory_report(snapshot_date, material_code);
CREATE INDEX idx_inventory_report_project ON bi_inventory_report(snapshot_date, project_code);

COMMENT ON TABLE bi_inventory_report IS '采购批次库存报表（批次级明细，支持排序分页）';
```

### 14.2 指标详细计算方式

```sql
-- 使用 _BATCH_AMOUNTS_SQL + _PROJECT_RATIO_SQL 模式
-- 项目级金额 = 批次金额 × project_ratio

inbound_amount   = ROUND(batch_inbound * project_ratio, 2)
claimed_amount   = ROUND(batch_claimed * project_ratio, 2)
inventory_amount = ROUND(batch_inventory * project_ratio, 2)

-- 领用率（批次级，同一批次各项目行返回相同值）
claim_rate = LEAST(ROUND(total_outbound / original * 100, 2), 100.00)

-- 分项出库数量 = 各类型出库量 × project_ratio
used_quantity = ROUND(total_outbound_quantity * project_ratio, 4)
pick_quantity = ROUND(pick_quantity * project_ratio, 4)
repair_quantity = ROUND(repair_quantity * project_ratio, 4)
scrap_quantity = ROUND(scrap_quantity * project_ratio, 4)
repaired_quantity = ROUND(repaired_quantity * project_ratio, 4)
```

支持排序字段：`claim_rate` / `age_days` / `inventory_amount`，支持 `asc` / `desc`，支持分页（`limit` + `offset`）。

---

## 15. 附加表：物资类别气泡图 `bi_category_bubble`

### 15.1 建表语句

```sql
CREATE TABLE bi_category_bubble (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    category_code   VARCHAR(100) NOT NULL,
    category_name   VARCHAR(200),

    inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 库存金额(元)
    inbound_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 入库金额(元)
    claimed_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,  -- 领用金额(元)
    claim_rate        NUMERIC(6,2)  NOT NULL DEFAULT 0,  -- 领用率(%)
    sku_count         INTEGER,                            -- SKU数
    record_count      INTEGER,                            -- 批次数

    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, category_code)
);

COMMENT ON TABLE bi_category_bubble IS '物资类别气泡图数据（按 material_group_code 聚合）';
```

### 15.2 计算方式

```sql
SELECT material_group_code,
    SUM(total_price) AS inventory_amount,
    SUM(inbound_amt) AS inbound_amount,
    SUM(claimed_amt) AS claimed_amount,
    COUNT(DISTINCT material_code) AS sku_count,
    COUNT(DISTINCT batch_code) AS record_count
FROM distinct_inventory  -- 按物理批次去重
WHERE material_group_code IS NOT NULL
GROUP BY material_group_code
ORDER BY inventory_amount DESC;

-- 取 TOP 10，其余归为「其他」
-- claim_rate = claimed / inbound × 100
```

---

## 附录 A：核心计算公式汇总

### A.1 金额计算

| 指标 | 公式 | 单位 |
|------|------|------|
| 入库金额 | `original_quantity × v_unit_price` | 元 |
| 领用金额 | `total_outbound_quantity × v_unit_price` | 元 |
| 库存金额 | `v_total_price = SUM(current_quantity × unit_price)` | 元 |
| 未领用金额 | `inbound - claimed` | 元 |
| 项目分配金额 | `批次金额 × project_ratio` | 元 |

### A.2 比率计算

| 指标 | 公式 | 说明 |
|------|------|------|
| 金额领用率 | `claimed / inbound × 100%` | 已领用比例 |
| 数量领用率 | `outbound_qty / original_qty × 100%` | 已领用数量比例 |
| 未领用占比 | `(inbound - claimed) / inbound × 100%` | 未领用比例 |
| 长库龄占比 | `Σ(inventory WHERE age ≥ 365) / Σ(inventory) × 100%` | ≥1年库存占比 |
| 项目/采购人占比 | `维度库存金额 / 总库存金额 × 100%` | |
| 超90天占比 | `Σ(inventory WHERE age ≥ 90) / Σ(inventory) × 100%` | |

### A.3 库龄计算

| 指标 | 公式 | 说明 |
|------|------|------|
| 库龄天数 | `CURRENT_DATE - COALESCE(inbound_date, create_date)` | 在视图中预计算 |
| 金额加权平均库龄 | `Σ(inventory_amount × age_days) / Σ(inventory_amount)` | 反映资金的沉淀时间 |
| 入库加权平均库龄 | `Σ(inbound_amount × age_days) / Σ(inbound_amount)` | 用于月度趋势回溯 |
| 未动用天数 | `Σ(未动用inventory × age) / Σ(未动用inventory)` | claimed=0 且 qty>0 |

### A.4 恒等式

```
inbound ≈ claimed + inventory

偏差率 = |inbound - claimed - inventory| / inventory × 100%
偏差 < 1% 视为成立
```

### A.5 去重规则

所有聚合计算必须先通过以下 CTE 去重：

```sql
DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
```

项目级计算需先获得批次金额，再通过 `project_ratio` 分配，确保 `Σ(项目金额) = Σ(批次金额)`。

### A.6 指标与 MCP 工具对照表

| MCP 工具名 | 对应模块 | 写入表 |
|------------|----------|--------|
| `get_kpi_summary` | `summary.py` | `bi_kpi_summary` |
| `get_claim_indicators` | `claim_indicators.py` | `bi_claim_indicators` |
| `get_structure_indicators` | `structure_indicators.py` | `bi_structure_indicators` |
| `get_time_indicators` | `time_indicators.py` | `bi_age_indicators` |
| `get_age_layers` | `time_indicators.py` | (查询用，不落表) |
| `get_age_monthly` | `time_indicators.py` | `bi_time_series` |
| `get_age_heatmap` | `time_indicators.py` | (查询用，不落表) |
| `get_by_project` | `dimension_indicators.py` | `bi_dimension_project` |
| `get_by_purchaser` | `dimension_indicators.py` | `bi_dimension_purchaser` |
| `get_project_summary` | `dimension_indicators.py` | `bi_dimension_project` |
| `get_purchaser_summary` | `dimension_indicators.py` | `bi_dimension_purchaser` |
| `get_top_unclaimed_amount` | `top_indicators.py` | `bi_top_ranking` |
| `get_top_unclaimed_quantity` | `top_indicators.py` | `bi_top_ranking` |
| `get_top_claimed_amount` | `top_indicators.py` | `bi_top_ranking` |
| `get_top_claimed_quantity` | `top_indicators.py` | `bi_top_ranking` |
| `get_optimize_suggest` | `top_indicators.py` | (查询用，不落表) |
| `get_claim_monthly` | `other_indicators.py` | `bi_time_series` |
| `get_claim_daily` | `other_indicators.py` | `bi_time_series` |
| `get_claim_weekly` | `other_indicators.py` | `bi_time_series` |
| `get_category_bubble` | `other_indicators.py` | `bi_category_bubble` |
| `get_anomaly_daily` | `other_indicators.py` | `bi_anomaly_detection` |
| `get_batch_digest` | `other_indicators.py` | `bi_batch_digest` |
| `get_inventory_report` | `other_indicators.py` | `bi_inventory_report` |
| `get_kpi_checklist` | `kpi_checklist.py` | `bi_kpi_checklist` |
| `get_structure_by_category` | `structure_indicators.py` | `bi_safety_stock` |
| `get_source_structure` | `structure_indicators.py` | (查询用，不落表) |