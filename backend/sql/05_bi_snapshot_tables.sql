-- =====================================================================
-- BI 快照表 — 每日定时任务落表
-- =====================================================================
-- 目标数据库：10.239.192.131 KingbaseES
-- 执行方式：python bi_snapshot.py（每天凌晨执行）
-- =====================================================================

-- 表 1：核心汇总指标
CREATE TABLE IF NOT EXISTS bi_kpi_summary (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    total_inbound_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_claimed_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_inventory_quantity NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_records           INTEGER NOT NULL DEFAULT 0,
    claim_rate              NUMERIC(6,2) NOT NULL DEFAULT 0,
    aged_amount_1y          NUMERIC(16,2) NOT NULL DEFAULT 0,
    aged_ratio_1y           NUMERIC(6,2) NOT NULL DEFAULT 0,
    avg_age_weighted_days   NUMERIC(10,2) NOT NULL DEFAULT 0,
    identity_inbound_minus_claimed NUMERIC(16,2),
    identity_actual_inventory      NUMERIC(16,2),
    identity_deviation_wan         NUMERIC(16,4),
    identity_deviation_pct         NUMERIC(8,4),
    identity_holds                 BOOLEAN,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

-- 表 2：领用率指标
CREATE TABLE IF NOT EXISTS bi_claim_indicators (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    period_type     VARCHAR(10) NOT NULL,
    current_year    INTEGER NOT NULL,
    total_inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    claim_rate_amount      NUMERIC(6,2)  NOT NULL DEFAULT 0,
    total_inbound_quantity  NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_claimed_quantity  NUMERIC(16,2) NOT NULL DEFAULT 0,
    claim_rate_quantity     NUMERIC(6,2)  NOT NULL DEFAULT 0,
    unclaimed_amount       NUMERIC(16,2) NOT NULL DEFAULT 0,
    unclaimed_amount_ratio NUMERIC(6,2)  NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, period_type)
);

-- 表 3：库存结构指标
CREATE TABLE IF NOT EXISTS bi_structure_indicators (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    current_year    INTEGER NOT NULL,
    current_inventory_amount       NUMERIC(16,2) NOT NULL DEFAULT 0,
    current_year_inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    current_inventory_quantity     NUMERIC(16,2) NOT NULL DEFAULT 0,
    project_ratios_json    JSONB,
    purchaser_ratios_json  JSONB,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

-- 表 4：库龄时间指标
CREATE TABLE IF NOT EXISTS bi_age_indicators (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    aged_ratio_1y           NUMERIC(8,4)  NOT NULL DEFAULT 0,
    aged_amount_1y          NUMERIC(16,2) NOT NULL DEFAULT 0,
    avg_age_weighted_days   NUMERIC(10,2) NOT NULL DEFAULT 0,
    age_structure_json      JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

-- 表 5：项目维度分析
CREATE TABLE IF NOT EXISTS bi_dimension_project (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    project_code    VARCHAR(100) NOT NULL,
    project_name    VARCHAR(200),
    inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    inventory_amount NUMERIC(16,2) NOT NULL DEFAULT 0,
    claim_rate       NUMERIC(6,2),
    avg_age_days     NUMERIC(10,2),
    over90_ratio     NUMERIC(6,2),
    record_count     INTEGER,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, project_code)
);

-- 表 6：采购人维度分析
CREATE TABLE IF NOT EXISTS bi_dimension_purchaser (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    purchaser_name  VARCHAR(200) NOT NULL,
    inbound_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    claimed_amount   NUMERIC(16,2) NOT NULL DEFAULT 0,
    inventory_amount NUMERIC(16,2) NOT NULL DEFAULT 0,
    claim_rate       NUMERIC(6,2),
    avg_age_days     NUMERIC(10,2),
    record_count     INTEGER,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, purchaser_name)
);

-- 表 7：TOP 排行
CREATE TABLE IF NOT EXISTS bi_top_ranking (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    rank_type       VARCHAR(30) NOT NULL,
    rank_position   INTEGER NOT NULL,
    material_code   VARCHAR(100),
    material_name   VARCHAR(200),
    batch_code      VARCHAR(100),
    inventory_amount  NUMERIC(16,2),
    current_quantity  NUMERIC(16,2),
    claimed_amount    NUMERIC(16,2),
    claimed_quantity  NUMERIC(16,2),
    inbound_amount    NUMERIC(16,2),
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

-- 表 8：时序分析
CREATE TABLE IF NOT EXISTS bi_time_series (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    granularity     VARCHAR(10) NOT NULL,
    period_label    VARCHAR(30) NOT NULL,
    inbound_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    claimed_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    net_amount      NUMERIC(16,2) NOT NULL DEFAULT 0,
    claim_rate      NUMERIC(6,2) NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, granularity, period_label)
);

-- 表 9：批次消化进度
CREATE TABLE IF NOT EXISTS bi_batch_digest (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    batch_code      VARCHAR(100) NOT NULL,
    inbound_wan     NUMERIC(16,2) NOT NULL DEFAULT 0,
    remain_pct      NUMERIC(6,2)  NOT NULL DEFAULT 0,
    avg_age_days    INTEGER,
    digest_data_json JSONB NOT NULL DEFAULT '[]',
    color_hex       VARCHAR(7),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, batch_code)
);

-- 表 10：异常检测
CREATE TABLE IF NOT EXISTS bi_anomaly_detection (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    week_label      VARCHAR(30) NOT NULL,
    inbound_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    claimed_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    anomaly_type    INTEGER NOT NULL DEFAULT 0,
    anomaly_label   VARCHAR(500),
    huanbi_pct      NUMERIC(6,2),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, week_label)
);

-- 表 11：KPI 考核清单
CREATE TABLE IF NOT EXISTS bi_kpi_checklist (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    total_inbound_wan       NUMERIC(16,2),
    total_claimed_wan       NUMERIC(16,2),
    current_inventory_wan   NUMERIC(16,2),
    overall_claim_rate      NUMERIC(6,2),
    aged_ratio_1y           NUMERIC(6,2),
    ok_count      INTEGER,
    warning_count INTEGER,
    alert_count   INTEGER,
    identity_deviation_pct NUMERIC(8,4),
    identity_holds         BOOLEAN,
    core_kpis_json        JSONB,
    constraint_kpis_json  JSONB,
    structure_kpis_json   JSONB,
    top_kpis_json         JSONB,
    data_start_date  DATE,
    data_end_date    DATE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date)
);

-- 表 12：安全库存偏离度
CREATE TABLE IF NOT EXISTS bi_safety_stock (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    rank_position   INTEGER NOT NULL,
    material_code   VARCHAR(100) NOT NULL,
    category_name   VARCHAR(200),
    current_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    safe_max        NUMERIC(16,2) NOT NULL DEFAULT 0,
    safe_min        NUMERIC(16,2) NOT NULL DEFAULT 0,
    record_count    INTEGER,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, material_code)
);

-- 表 13：采购批次库存报表
CREATE TABLE IF NOT EXISTS bi_inventory_report (
    id                  SERIAL PRIMARY KEY,
    snapshot_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    purchase_batch      VARCHAR(100),
    material_name       VARCHAR(200),
    material_code       VARCHAR(100),
    project_code        VARCHAR(100),
    project_name        VARCHAR(200),
    purchaser_name      VARCHAR(200),
    submitter_name      VARCHAR(200),
    contact_name        VARCHAR(200),
    project_type        VARCHAR(100),
    inbound_date        DATE,
    putaway_date        DATE,
    batch_code          VARCHAR(100),
    original_quantity   NUMERIC(16,4),
    current_quantity    NUMERIC(16,4),
    used_quantity       NUMERIC(16,4),
    pick_quantity       NUMERIC(16,4),
    repair_quantity     NUMERIC(16,4),
    scrap_quantity      NUMERIC(16,4),
    repaired_quantity   NUMERIC(16,4),
    unit_price          NUMERIC(16,4),
    unit                VARCHAR(20),
    supplier_code       VARCHAR(100),
    inbound_amount      NUMERIC(16,2),
    claimed_amount      NUMERIC(16,2),
    inventory_amount    NUMERIC(16,2),
    claim_rate          NUMERIC(6,2),
    age_days            INTEGER,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ir_snapshot ON bi_inventory_report(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_ir_material ON bi_inventory_report(snapshot_date, material_code);

-- 附加表：物资类别气泡图
CREATE TABLE IF NOT EXISTS bi_category_bubble (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    category_code   VARCHAR(100) NOT NULL,
    category_name   VARCHAR(200),
    inventory_amount  NUMERIC(16,2) NOT NULL DEFAULT 0,
    inbound_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,
    claimed_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,
    claim_rate        NUMERIC(6,2)  NOT NULL DEFAULT 0,
    sku_count         INTEGER,
    record_count      INTEGER,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_date, category_code)
);