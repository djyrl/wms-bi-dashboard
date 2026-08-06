-- =====================================================================
-- BI 快照表 — 每日定时任务落表
-- =====================================================================
-- 目标数据库：10.239.192.131 KingbaseES
-- 执行方式：python bi_snapshot.py（每天凌晨执行）
-- =====================================================================

-- 表 1：核心汇总指标
CREATE TABLE IF NOT EXISTS bi_kpi_summary (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期（唯一）
    total_inbound_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,             -- 入库总额（万元）
    total_claimed_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,             -- 领用总额（万元）
    total_inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,             -- 当前库存金额（万元）
    total_inventory_quantity NUMERIC(16,2) NOT NULL DEFAULT 0,            -- 库存总数量
    total_records           INTEGER NOT NULL DEFAULT 0,                   -- 批次总条数
    claim_rate              NUMERIC(6,2) NOT NULL DEFAULT 0,              -- 综合领用率（%）= claimed / inbound × 100
    aged_amount_1y          NUMERIC(16,2) NOT NULL DEFAULT 0,             -- 库龄≥1年库存金额（万元）
    aged_ratio_1y           NUMERIC(6,2) NOT NULL DEFAULT 0,              -- 长库龄占比（%）
    avg_age_weighted_days   NUMERIC(10,2) NOT NULL DEFAULT 0,             -- 金额加权平均库龄（天）
    identity_inbound_minus_claimed NUMERIC(16,2),                         -- 恒等式 inbound - claimed（万元）
    identity_actual_inventory      NUMERIC(16,2),                         -- 恒等式 实际库存（万元）
    identity_deviation_wan         NUMERIC(16,4),                         -- 恒等式 偏差（万元）
    identity_deviation_pct         NUMERIC(8,4),                          -- 恒等式 偏差率（%）
    identity_holds                 BOOLEAN,                               -- 恒等式是否成立（偏差<1%）
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date)
);

-- 表 2：领用率指标（all=全部批次, year=当年批次）
CREATE TABLE IF NOT EXISTS bi_claim_indicators (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    period_type     VARCHAR(10) NOT NULL,                                  -- 周期类型 all=全部 year=当年
    current_year    INTEGER NOT NULL,                                      -- 当前年份
    total_inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,              -- 入库总额（万元）
    total_claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,              -- 领用总额（万元）
    claim_rate_amount      NUMERIC(6,2)  NOT NULL DEFAULT 0,              -- 金额领用率（%）= claimed / inbound × 100
    total_inbound_quantity  NUMERIC(16,2) NOT NULL DEFAULT 0,             -- 入库总数量
    total_claimed_quantity  NUMERIC(16,2) NOT NULL DEFAULT 0,             -- 领用总数量
    claim_rate_quantity     NUMERIC(6,2)  NOT NULL DEFAULT 0,             -- 数量领用率（%）
    unclaimed_amount       NUMERIC(16,2) NOT NULL DEFAULT 0,              -- 未领用金额（万元）= inbound - claimed
    unclaimed_amount_ratio NUMERIC(6,2)  NOT NULL DEFAULT 0,              -- 未领用占比（%）
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, period_type)
);

-- 表 3：库存结构指标
CREATE TABLE IF NOT EXISTS bi_structure_indicators (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期（唯一）
    current_year    INTEGER NOT NULL,                                      -- 当前年份
    current_inventory_amount       NUMERIC(16,2) NOT NULL DEFAULT 0,      -- 全部库存金额（万元）
    current_year_inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,      -- 当年入库库存金额（万元）
    current_inventory_quantity     NUMERIC(16,2) NOT NULL DEFAULT 0,      -- 库存总数量
    project_ratios_json    JSONB,                                          -- 项目库存占比 TOP10 [{project_code, project_name, inventory_amount, ratio}]
    purchaser_ratios_json  JSONB,                                          -- 采购人库存占比 TOP10 [{purchaser_name, inventory_amount, ratio}]
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date)
);

-- 表 4：库龄时间指标
CREATE TABLE IF NOT EXISTS bi_age_indicators (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期（唯一）
    aged_ratio_1y           NUMERIC(8,4)  NOT NULL DEFAULT 0,            -- 长库龄占比（比例值，如0.15=15%）
    aged_amount_1y          NUMERIC(16,2) NOT NULL DEFAULT 0,            -- 长库龄金额（元）
    avg_age_weighted_days   NUMERIC(10,2) NOT NULL DEFAULT 0,            -- 加权平均库龄（天）= Σ(inventory×age) / Σ(inventory)
    age_structure_json      JSONB NOT NULL DEFAULT '[]',                  -- 库龄结构 [{range, amount, ratio, count}] ≤1年/1~3年/3~5年/≥5年
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date)
);

-- 表 5：项目维度分析（每项目一行）
CREATE TABLE IF NOT EXISTS bi_dimension_project (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    project_code    VARCHAR(100) NOT NULL,                                 -- 项目编码
    project_name    VARCHAR(200),                                          -- 项目名称
    inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 入库金额（元，project_ratio 分配后）
    claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 领用金额（元，project_ratio 分配后）
    inventory_amount NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 未消耗库存金额（元）= 批次库存 × project_ratio
    claim_rate       NUMERIC(6,2),                                        -- 领用率（%）= claimed / inbound × 100（上限100%）
    avg_age_days     NUMERIC(10,2),                                       -- 金额加权平均库龄（天）
    over90_ratio     NUMERIC(6,2),                                        -- 库龄≥90天占比（%）
    record_count     INTEGER,                                             -- 记录数
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, project_code)
);

-- 表 6：采购人维度分析（按 project_contact 聚合）
CREATE TABLE IF NOT EXISTS bi_dimension_purchaser (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    purchaser_name  VARCHAR(200) NOT NULL,                                 -- 采购人/联系人名称
    inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 入库金额（元）
    claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 领用金额（元）
    inventory_amount NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 未消耗库存金额（元）
    claim_rate       NUMERIC(6,2),                                        -- 领用率（%）
    avg_age_days     NUMERIC(10,2),                                       -- 加权平均库龄（天）
    record_count     INTEGER,                                             -- 记录数
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, purchaser_name)
);

-- 表 7：TOP 排行（未领用金额/数量, 领用金额/数量）
CREATE TABLE IF NOT EXISTS bi_top_ranking (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    rank_type       VARCHAR(30) NOT NULL,                                  -- 排行类型 unclaimed_amount=未领用金额 unclaimed_quantity=未领用数量 claimed_amount=领用金额 claimed_quantity=领用数量
    rank_position   INTEGER NOT NULL,                                      -- 排名
    material_code   VARCHAR(100),                                          -- 物料编码
    material_name   VARCHAR(200),                                          -- 物料名称
    batch_code      VARCHAR(100),                                          -- 批次号
    inventory_amount  NUMERIC(16,2),                                       -- 库存金额（元）
    current_quantity  NUMERIC(16,2),                                       -- 当前库存数量
    claimed_amount    NUMERIC(16,2),                                       -- 领用金额（元）
    claimed_quantity  NUMERIC(16,2),                                       -- 领用数量
    inbound_amount    NUMERIC(16,2),                                       -- 入库金额（元）
    unit_price       NUMERIC(16,4),                                        -- 单价
    unit             VARCHAR(20),                                          -- 单位
    age_days         INTEGER,                                              -- 库龄（天）
    inbound_date     DATE,                                                 -- 入库日期
    project_code     VARCHAR(100),                                         -- 项目编码
    project_name     VARCHAR(200),                                         -- 项目名称
    purchaser_name   VARCHAR(200),                                         -- 采购人
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, rank_type, rank_position)
);

-- 表 8：时序分析（月/日/周粒度）
CREATE TABLE IF NOT EXISTS bi_time_series (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    granularity     VARCHAR(10) NOT NULL,                                  -- 粒度 monthly=月度 daily=日度 weekly=周度
    period_label    VARCHAR(30) NOT NULL,                                  -- 时间标签 如2026-01/2026-01-15/2026-W03
    inbound_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 入库金额（元）
    claimed_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 领用金额（元）
    net_amount      NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 净额（元）= inbound - claimed
    claim_rate      NUMERIC(6,2) NOT NULL DEFAULT 0,                      -- 领用率（%）
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, granularity, period_label)
);

-- 表 9：批次消化进度（TOP 6 批次）
CREATE TABLE IF NOT EXISTS bi_batch_digest (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    batch_code      VARCHAR(100) NOT NULL,                                 -- 批次号
    inbound_wan     NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 入库金额（万元）
    remain_pct      NUMERIC(6,2)  NOT NULL DEFAULT 0,                     -- 剩余占比（%）= remain / inbound × 100
    avg_age_days    INTEGER,                                               -- 平均库龄（天）
    digest_data_json JSONB NOT NULL DEFAULT '[]',                          -- 逐月消化数据 [100, 95, 88, ...] 百分比序列
    color_hex       VARCHAR(7),                                            -- 颜色标识
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, batch_code)
);

-- 表 10：异常检测（近12周）
CREATE TABLE IF NOT EXISTS bi_anomaly_detection (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    week_label      VARCHAR(30) NOT NULL,                                  -- 周标签 如3/1-3/7
    inbound_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 入库金额（万元）
    claimed_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 领用金额（万元）
    anomaly_type    INTEGER NOT NULL DEFAULT 0,                           -- 异常类型 0=正常 1=异常
    anomaly_label   VARCHAR(500),                                          -- 异常描述 如'新项目(XX项目);环比↑35%'
    huanbi_pct      NUMERIC(6,2),                                          -- 周度环比变化（%）
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, week_label)
);

-- 表 11：KPI 考核清单（K1-K9 + T1-T2）
CREATE TABLE IF NOT EXISTS bi_kpi_checklist (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期（唯一）
    total_inbound_wan       NUMERIC(16,2),                                 -- 入库总额（万元）
    total_claimed_wan       NUMERIC(16,2),                                 -- 领用总额（万元）
    current_inventory_wan   NUMERIC(16,2),                                 -- 当前库存（万元）
    overall_claim_rate      NUMERIC(6,2),                                  -- 综合领用率（%）
    aged_ratio_1y           NUMERIC(6,2),                                  -- 长库龄占比（%）
    ok_count      INTEGER,                                                 -- 达标数
    warning_count INTEGER,                                                 -- 预警数
    alert_count   INTEGER,                                                 -- 未达标数
    identity_deviation_pct NUMERIC(8,4),                                   -- 恒等式偏差率（%）
    identity_holds         BOOLEAN,                                        -- 恒等式是否成立
    core_kpis_json        JSONB,                                           -- 核心考核KPI K1-K3
    constraint_kpis_json  JSONB,                                           -- 约束类KPI K4-K5
    structure_kpis_json   JSONB,                                           -- 结构分析KPI K6-K9
    top_kpis_json         JSONB,                                           -- TOP类KPI T1-T2
    data_start_date  DATE,                                                 -- 数据起始日期
    data_end_date    DATE,                                                 -- 数据截止日期
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date)
);

-- 表 12：安全库存偏离度（按物料编码，TOP 10+其他）
CREATE TABLE IF NOT EXISTS bi_safety_stock (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    rank_position   INTEGER NOT NULL,                                      -- 排名（1-10, 99=其他）
    material_code   VARCHAR(100) NOT NULL,                                 -- 物料编码
    category_name   VARCHAR(200),                                          -- 物料名称
    current_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 库存金额（元）
    safe_max        NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 安全上限（元）= TOP10均值 × 1.5
    safe_min        NUMERIC(16,2) NOT NULL DEFAULT 0,                     -- 安全下限（元）= TOP10均值 × 0.5
    record_count    INTEGER,                                               -- 批次数
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, material_code)
);

-- 表 13：采购批次库存报表（批次级明细）
CREATE TABLE IF NOT EXISTS bi_inventory_report (
    id                  SERIAL PRIMARY KEY,                                -- 自增主键
    snapshot_date       DATE NOT NULL DEFAULT CURRENT_DATE,                -- 快照日期
    purchase_batch      VARCHAR(100),                                      -- 采购批次号
    material_name       VARCHAR(200),                                      -- 物料名称
    material_code       VARCHAR(100),                                      -- 物料编码
    project_code        VARCHAR(100),                                      -- 项目编码
    project_name        VARCHAR(200),                                      -- 项目名称
    purchaser_name      VARCHAR(200),                                      -- 提报人（采购归属）
    submitter_name      VARCHAR(200),                                      -- 申请人
    contact_name        VARCHAR(200),                                      -- 联系人
    project_type        VARCHAR(100),                                      -- 项目计划类别
    inbound_date        DATE,                                              -- 入库日期
    putaway_date        DATE,                                              -- 上架日期
    batch_code          VARCHAR(100),                                      -- 批次号
    original_quantity   NUMERIC(16,4),                                     -- 原始入库数量
    current_quantity    NUMERIC(16,4),                                     -- 当前库存数量
    used_quantity       NUMERIC(16,4),                                     -- 已领用数量（total_outbound × project_ratio）
    pick_quantity       NUMERIC(16,4),                                     -- 拣货出库数量（× project_ratio）
    repair_quantity     NUMERIC(16,4),                                     -- 维修出库数量（× project_ratio）
    scrap_quantity      NUMERIC(16,4),                                     -- 报废出库数量（× project_ratio）
    repaired_quantity   NUMERIC(16,4),                                     -- 返修出库数量（× project_ratio）
    unit_price          NUMERIC(16,4),                                     -- 当前加权均价
    unit                VARCHAR(20),                                       -- 物料单位
    supplier_code       VARCHAR(100),                                      -- 供应商编码
    inbound_amount      NUMERIC(16,2),                                     -- 项目级入库金额（元）= 批次入库 × project_ratio
    claimed_amount      NUMERIC(16,2),                                     -- 项目级领用金额（元）= 批次领用 × project_ratio
    inventory_amount    NUMERIC(16,2),                                     -- 项目级库存金额（元）= 批次库存 × project_ratio
    claim_rate          NUMERIC(6,2),                                      -- 领用率（%）批次级，上限100%
    age_days            INTEGER,                                           -- 库龄（天）
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()                          -- 创建时间
);

-- 附加表：物资类别气泡图（按 material_group_code 聚合）
CREATE TABLE IF NOT EXISTS bi_category_bubble (
    id              SERIAL PRIMARY KEY,                                    -- 自增主键
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,                    -- 快照日期
    category_code   VARCHAR(100) NOT NULL,                                 -- 物资类别编码
    category_name   VARCHAR(200),                                          -- 物资类别名称
    inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 库存金额（元）
    inbound_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 入库金额（元）
    claimed_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,                   -- 领用金额（元）
    claim_rate        NUMERIC(6,2)  NOT NULL DEFAULT 0,                   -- 领用率（%）
    sku_count         INTEGER,                                             -- SKU数
    record_count      INTEGER,                                             -- 批次数
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),                         -- 创建时间
    UNIQUE(snapshot_date, category_code)
);

CREATE INDEX IF NOT EXISTS idx_ir_snapshot ON bi_inventory_report(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_ir_material ON bi_inventory_report(snapshot_date, material_code);