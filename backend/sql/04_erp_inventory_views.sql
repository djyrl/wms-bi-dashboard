-- =====================================================================
-- ERP + WMS 联合库存视图
-- =====================================================================
-- 说明：将 erp_catalog_mb51（ERP 全部历史凭证）与
--       v_project_inventory_wide（WMS 当前实物库存）在批次级联联合，
--       补齐 WMS 2026 年 6 月之前的数据缺口。
--
-- 数据来源：
--   erp_catalog_mb51        — ERP 物料凭证（2021-05 ~ 今，plants=2635）
--   v_project_inventory_wide — WMS 物理库存快照（2026-06 ~ 今）
--
-- 匹配键：material_code + batch_code（ERP charg 列 ↔ WMS batch_code 列）
--
-- 关键约定：
--   - ERP DMBTR 天然带正负号，直接 SUM 即净变化
--   - KingbaseES Oracle 兼容模式：空字符串 '' 视为 NULL，不可用 != '' 判断
--   - WMS 使用 DISTINCT ON (tenant_id,material_code,batch_code,erp_inventory) 去重
-- =====================================================================

-- ---------------------------------------------------------------
-- 1. 批次生命周期视图（一个批次一行）
-- ---------------------------------------------------------------
-- 每个批次的完整画像：
--   ERP 侧：入库/出库/净余额，首次入库日期，最后移动日期
--   WMS 侧：当前库存金额/数量，单价，库龄
--   状态：在库 / ERP有余额_WMS无 / 已消耗完 / 负余额(异常)
-- ---------------------------------------------------------------
CREATE OR REPLACE VIEW v_batch_lifecycle AS
WITH erp_batch AS (
    SELECT
        row_json->>'MATNR'                       AS material_code,
        charg                                     AS batch_code,
        -- 入库（101收货 + 102冲销，102已是负数）
        SUM(CASE WHEN bwart IN ('101','102')
            THEN (row_json->>'DMBTR')::numeric
            ELSE 0 END)                           AS erp_inbound_amt,
        SUM(CASE WHEN bwart IN ('101','102')
            THEN (row_json->>'MENGE')::numeric
            ELSE 0 END)                           AS erp_inbound_qty,
        -- 出库（201成本中心 / 221项目 / 222 / Z61项目 / Z62）
        SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
            THEN (row_json->>'DMBTR')::numeric
            ELSE 0 END)                           AS erp_outbound_amt,
        SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
            THEN (row_json->>'MENGE')::numeric
            ELSE 0 END)                           AS erp_outbound_qty,
        -- 净余额（金额 & 数量）
        SUM((row_json->>'DMBTR')::numeric)        AS erp_balance_amt,
        SUM((row_json->>'MENGE')::numeric)        AS erp_balance_qty,
        -- 时间
        MIN(row_json->>'BLDAT')                   AS first_inbound_date,
        MAX(row_json->>'BLDAT')                   AS last_move_date,
        -- 行数 & 移动类型种类
        COUNT(*)                                  AS move_cnt,
        COUNT(DISTINCT bwart)                     AS move_type_cnt
    FROM public.erp_catalog_mb51
    WHERE werks = '2635'
      AND row_json->>'MATNR' IS NOT NULL
      AND charg IS NOT NULL
    GROUP BY row_json->>'MATNR', charg
),
wms_batch_raw AS (
    SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
        material_code,
        batch_code,
        total_price                              AS wms_inventory_amt,
        current_quantity                         AS wms_current_qty,
        original_quantity                        AS wms_orig_qty,
        total_outbound_quantity                  AS wms_outbound_qty,
        unit_price                               AS wms_unit_price,
        age_days                                 AS wms_age_days,
        inbound_date::date                       AS wms_inbound_date,
        material_name,
        material_group_code
    FROM v_project_inventory_wide
),
wms_batch AS (
    SELECT
        material_code,
        batch_code,
        SUM(wms_inventory_amt)    AS wms_inventory_amt,
        SUM(wms_current_qty)      AS wms_current_qty,
        SUM(wms_orig_qty)         AS wms_orig_qty,
        SUM(wms_outbound_qty)     AS wms_outbound_qty,
        MAX(wms_unit_price)       AS wms_unit_price,
        MAX(wms_age_days)         AS wms_age_days,
        MAX(wms_inbound_date)     AS wms_inbound_date,
        MAX(material_name)        AS material_name,
        MAX(material_group_code)  AS material_group_code
    FROM wms_batch_raw
    GROUP BY material_code, batch_code
)
SELECT
    COALESCE(e.material_code, w.material_code)      AS material_code,
    COALESCE(e.batch_code, w.batch_code)             AS batch_code,

    -- ERP 账面
    COALESCE(e.erp_inbound_amt, 0)                   AS erp_inbound_amt,
    COALESCE(e.erp_inbound_qty, 0)                   AS erp_inbound_qty,
    COALESCE(e.erp_outbound_amt, 0)                  AS erp_outbound_amt,
    COALESCE(e.erp_outbound_qty, 0)                  AS erp_outbound_qty,
    COALESCE(e.erp_balance_amt, 0)                   AS erp_balance_amt,
    COALESCE(e.erp_balance_qty, 0)                   AS erp_balance_qty,
    e.first_inbound_date,
    e.last_move_date,
    e.move_cnt,
    e.move_type_cnt,

    -- WMS 实物
    COALESCE(w.wms_inventory_amt, 0)                 AS wms_inventory_amt,
    COALESCE(w.wms_current_qty, 0)                   AS wms_current_qty,
    COALESCE(w.wms_orig_qty, 0)                      AS wms_orig_qty,
    COALESCE(w.wms_outbound_qty, 0)                  AS wms_outbound_qty,
    w.wms_unit_price,
    w.wms_age_days,
    w.wms_inbound_date,
    w.material_name,
    w.material_group_code,

    -- 最佳库存估计：WMS 优先，其次用 ERP 账面（但不能为负）
    CASE
        WHEN COALESCE(w.wms_inventory_amt, 0) > 0
            THEN w.wms_inventory_amt
        ELSE GREATEST(COALESCE(e.erp_balance_amt, 0), 0)
    END                                              AS best_inventory_amt,
    CASE
        WHEN COALESCE(w.wms_current_qty, 0) > 0
            THEN w.wms_current_qty
        ELSE GREATEST(COALESCE(e.erp_balance_qty, 0), 0)
    END                                              AS best_inventory_qty,

    -- 状态分类
    CASE
        WHEN COALESCE(w.wms_inventory_amt, 0) > 0 THEN '在库'
        WHEN COALESCE(e.erp_balance_amt, 0) > 100 THEN 'ERP有余额_WMS无'
        WHEN COALESCE(e.erp_balance_amt, 0) BETWEEN -100 AND 100 THEN '已消耗完'
        ELSE '负余额_异常'
    END                                              AS batch_status,

    -- ERP/WMS 金额差异
    CASE
        WHEN COALESCE(w.wms_inventory_amt, 0) > 0 AND COALESCE(e.erp_balance_amt, 0) > 0
        THEN w.wms_inventory_amt - e.erp_balance_amt
        ELSE NULL
    END                                              AS erp_wms_gap_amt

FROM erp_batch e
FULL OUTER JOIN wms_batch w
    ON e.material_code = w.material_code
   AND e.batch_code = w.batch_code;


-- ---------------------------------------------------------------
-- 2. 月度库存时序视图（全局累计和）
-- ---------------------------------------------------------------
-- 原理：
--   所有 ERP 移动按月汇总 → 窗口函数计算全局累计和 → 每月末的库存总额。
--   这是最简单且正确的方案，避免了「稀疏批次」问题（某批次某月无移动时，
--   不会出现在该月的汇总中）。
--
-- 注意：
--   - 给出的是 ERP 账面累计余额，不含 WMS 校准
--   - 累计和从 2021-05 开始，假设期初库存为 0
--   - 适用于全局库存趋势分析
-- ---------------------------------------------------------------
CREATE OR REPLACE VIEW v_monthly_inventory_timeline AS
WITH monthly_total AS (
    SELECT
        DATE_TRUNC('month', (row_json->>'BLDAT')::date)::date AS doc_month, -- 取移动日期
        SUM(CASE WHEN bwart IN ('101','102')
            THEN (row_json->>'DMBTR')::numeric ELSE 0 END)   AS month_inbound, -- 入
        SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
            THEN -(row_json->>'DMBTR')::numeric ELSE 0 END)  AS month_outbound, -- 出
        SUM((row_json->>'DMBTR')::numeric)                    AS net_amt_change, -- 净金额
        SUM((row_json->>'MENGE')::numeric)                    AS net_qty_change, -- 净数量
        COUNT(*)                                              AS move_cnt, -- 移动次数
        COUNT(DISTINCT row_json->>'MATNR' || '|' || charg)   AS active_batches -- 批次数
    FROM public.erp_catalog_mb51
    WHERE werks = '2635'
      AND row_json->>'MATNR' IS NOT NULL
      AND charg IS NOT NULL
    GROUP BY 1
)
SELECT
    doc_month,
    active_batches,
    month_inbound,
    month_outbound,
    net_amt_change,
    SUM(net_amt_change) OVER (ORDER BY doc_month ROWS UNBOUNDED PRECEDING) AS total_inventory_amt,
    SUM(net_qty_change) OVER (ORDER BY doc_month ROWS UNBOUNDED PRECEDING) AS total_inventory_qty,
    move_cnt
FROM monthly_total
ORDER BY doc_month;


-- ---------------------------------------------------------------
-- 3. 物料月度库存视图（按物料汇总的全局累计）
-- ---------------------------------------------------------------
CREATE OR REPLACE VIEW v_material_monthly_inventory AS
WITH material_monthly AS (
    SELECT
        row_json->>'MATNR'                                   AS material_code,
        DATE_TRUNC('month', (row_json->>'BLDAT')::date)::date AS doc_month, -- 取移动日期
        SUM((row_json->>'DMBTR')::numeric)                    AS net_amt_change, -- 净金额
        COUNT(DISTINCT charg)                                 AS active_batches -- 批次数
    FROM public.erp_catalog_mb51
    WHERE werks = '2635'
      AND row_json->>'MATNR' IS NOT NULL
      AND charg IS NOT NULL
    GROUP BY 1, 2
)
SELECT
    material_code,
    doc_month,
    net_amt_change,
    SUM(net_amt_change) OVER (
        PARTITION BY material_code ORDER BY doc_month ROWS UNBOUNDED PRECEDING
    ) AS cumulative_balance,
    active_batches
FROM material_monthly
ORDER BY material_code, doc_month;


COMMENT ON VIEW v_batch_lifecycle IS
'ERP+WMS批次生命周期视图：每个物料+批次一行，含ERP账面、WMS实物、状态分类、最佳库存估计';

COMMENT ON VIEW v_monthly_inventory_timeline IS
'月度库存时序：从2021年5月至今，每月末的库存金额(ERP累计余额)';

COMMENT ON VIEW v_material_monthly_inventory IS
'物料月度库存：按物料+月份汇总的库存金额';
