-- ============================================================
-- 采购批次库存报表视图 v6
-- 主表：wms_project_inventory
-- 库存过滤：官方口径（status=1, current_quantity>0, 有效货位仓库Z00）
-- 金额/数量按项目台账占比分摊，SUM(inventory_amount) = 官方 SUM(total_price)
-- 无项目归属 → WMS001「非项目物资」
--
-- v6 修正：
--   1. inbound_amount 改用原始入库加权单价(基于 original_quantity)，
--      避免因报废/调整导致 original_qty ≠ current_qty 时金额失真
--   2. claimed_amount → outbound_amount(全部出库) + pick_amount(仅领料)
--   3. 三数关系：inbound_amount ≈ outbound_amount + inventory_amount
-- ============================================================
CREATE OR REPLACE VIEW v_rpt_inventory_report AS
WITH filtered_inventory AS (
    -- 官方口径的物理库存明细：默认ERP仓库 + status=1 + current_quantity>0 + 有效货位
    SELECT
        inv."tenant_id",
        inv."material_code",
        inv."batch_code",
        inv."erp_inventory",
        inv."id" AS inventory_id,
        inv."current_quantity",
        inv."original_quantity",
        inv."total_price",
        inv."unit_price",
        inv."inbound_date",
        inv."putaway_date",
        inv."supplier_code"
    FROM "wms_inventory" inv
    WHERE inv."del_flag" = '0'
      AND inv."status" = 1
      AND inv."current_quantity" > 0
      AND EXISTS (
          SELECT 1
          FROM "wms_inventory_location" iloc
          INNER JOIN "wms_location" loc
              ON iloc."location_id" = loc."id"
              AND loc."del_flag" = '0'
          WHERE iloc."inventory_id" = inv."id"
            AND iloc."del_flag" = '0'
            AND iloc."status" = 1
            AND iloc."current_quantity" > 0
      )
),
official_inventory AS (
    -- 按 (tenant_id, material_code, batch_code, erp_inventory) 聚合物理库存
    SELECT
        "tenant_id",
        "material_code",
        "batch_code",
        "erp_inventory",
        SUM("current_quantity") AS total_current_quantity,
        SUM("original_quantity") AS total_original_quantity,
        SUM("total_price") AS total_price,
        -- 当前加权单价（基于 current_quantity，用于 inventory_amount）
        CASE
            WHEN SUM("current_quantity") > 0
            THEN SUM("total_price") / SUM("current_quantity")
            ELSE MAX("unit_price")
        END AS weighted_unit_price,
        -- 原始入库加权单价（基于 original_quantity，用于 inbound_amount）
        SUM("original_quantity" * "unit_price") AS total_original_price,
        CASE
            WHEN SUM("original_quantity") > 0
            THEN SUM("original_quantity" * "unit_price") / SUM("original_quantity")
            ELSE MAX("unit_price")
        END AS weighted_unit_price_orig,
        MIN("inbound_date") AS inbound_date,
        MAX("putaway_date") AS putaway_date,
        MAX("supplier_code") AS supplier_code
    FROM filtered_inventory
    GROUP BY "tenant_id", "material_code", "batch_code", "erp_inventory"
),
outbound_log_agg AS (
    -- 出库日志按同一维度聚合
    SELECT
        inv."tenant_id",
        inv."material_code",
        inv."batch_code",
        inv."erp_inventory",
        SUM(log.change_quantity) AS total_outbound_quantity,
        -- 仅领料（change_type=31），不含报废/维修
        SUM(CASE WHEN log.change_type = 31 THEN log.change_quantity ELSE 0 END) AS pick_quantity,
        SUM(CASE WHEN log.change_type = 34 THEN log.change_quantity ELSE 0 END) AS repair_quantity,
        SUM(CASE WHEN log.change_type = 35 THEN log.change_quantity ELSE 0 END) AS scrap_quantity,
        SUM(CASE WHEN log.change_type = 36 THEN log.change_quantity ELSE 0 END) AS repaired_quantity
    FROM filtered_inventory inv
    INNER JOIN wms_inventory_log log
        ON log.inventory_id = inv.inventory_id
    WHERE log.change_type IN (31, 34, 35, 36)
      AND log.del_flag = '0'
    GROUP BY inv."tenant_id", inv."material_code", inv."batch_code", inv."erp_inventory"
),
project_inventory_with_ratio AS (
    -- 项目台账及数量占比
    SELECT
        pi."id",
        pi."tenant_id",
        pi."material_code",
        pi."batch_code",
        pi."erp_inventory",
        pi."owner_project_code",
        pi."owner_project_type",
        pi."current_quantity",
        pi."create_date",
        SUM(pi."current_quantity") OVER (
            PARTITION BY pi."tenant_id", pi."material_code", pi."batch_code", pi."erp_inventory"
        ) AS total_project_quantity,
        CASE
            WHEN SUM(pi."current_quantity") OVER (
                PARTITION BY pi."tenant_id", pi."material_code", pi."batch_code", pi."erp_inventory"
            ) > 0
            THEN pi."current_quantity" / SUM(pi."current_quantity") OVER (
                PARTITION BY pi."tenant_id", pi."material_code", pi."batch_code", pi."erp_inventory"
            )
            ELSE 0
        END AS project_ratio
    FROM "wms_project_inventory" pi
    WHERE pi."del_flag" = '0'
)
SELECT
    pi."id",
    pi."batch_code" AS purchase_batch,
    COALESCE(NULLIF(erp_mat.maktx, ' '), NULLIF(wms_mat.name, ' '), pi."material_code") AS material_name,
    pi."material_code",
    CASE
        WHEN pi."owner_project_code" IS NULL OR pi."owner_project_code" = ' ' THEN 'WMS001'
        ELSE pi."owner_project_code"
    END AS project_code,
    CASE
        WHEN pi."owner_project_code" IS NULL OR pi."owner_project_code" = ' ' THEN '非项目物资'
        ELSE erp_proj.zpost1
    END AS project_name,
    erp_proj.z_user AS purchaser_name,
    erp_proj.plancat_txt AS project_type,
    inv.inbound_date::date AS inbound_date,
    inv.putaway_date::date AS putaway_date,
    pi."batch_code",
    inv.total_original_quantity AS original_quantity,
    pi."current_quantity",
    ROUND((COALESCE(outbound_log.total_outbound_quantity, 0) * pi.project_ratio)::numeric, 4) AS used_quantity,
    -- 领料数量（仅 change_type=31，不含报废/维修）
    ROUND((COALESCE(outbound_log.pick_quantity, 0) * pi.project_ratio)::numeric, 4) AS pick_quantity,
    ROUND((COALESCE(outbound_log.repair_quantity, 0) * pi.project_ratio)::numeric, 4) AS repair_quantity,
    ROUND((COALESCE(outbound_log.scrap_quantity, 0) * pi.project_ratio)::numeric, 4) AS scrap_quantity,
    ROUND((COALESCE(outbound_log.repaired_quantity, 0) * pi.project_ratio)::numeric, 4) AS repaired_quantity,
    inv.weighted_unit_price AS unit_price,
    erp_mat.msehl AS unit,
    inv.supplier_code,
    -- 【v6 修正】入库金额：用原始入库加权单价(基于 original_quantity)，保持与 inventory 一致性
    ROUND((inv.total_original_price * pi.project_ratio)::numeric, 2) AS inbound_amount,
    -- 【v6 修正】领用金额（仅领料 change_type=31）: 用原始入库加权单价
    ROUND((COALESCE(outbound_log.pick_quantity, 0) * inv.weighted_unit_price_orig * pi.project_ratio)::numeric, 2) AS claimed_amount,
    -- 全部出库金额（含领料+维修+报废+修复）: 用原始入库加权单价
    ROUND((COALESCE(outbound_log.total_outbound_quantity, 0) * inv.weighted_unit_price_orig * pi.project_ratio)::numeric, 2) AS outbound_amount,
    -- 当前库存金额（不变）: total_price = SUM(current_qty × unit_price)
    ROUND((inv.total_price * pi.project_ratio)::numeric, 2) AS inventory_amount,
    -- 领用率（基于入库金额）
    CASE
        WHEN inv.total_original_price > 0
        THEN LEAST(ROUND(
            COALESCE(outbound_log.total_outbound_quantity, 0)
            * inv.weighted_unit_price_orig / inv.total_original_price * 100, 2), 100.00)
        ELSE 0
    END AS claim_rate,
    CASE
        WHEN inv.inbound_date IS NOT NULL
        THEN EXTRACT(DAY FROM (CURRENT_DATE - inv.inbound_date::timestamp))::int
        ELSE EXTRACT(DAY FROM (CURRENT_DATE - pi."create_date"::timestamp))::int
    END AS age_days
FROM project_inventory_with_ratio pi
LEFT JOIN official_inventory inv
    ON inv."tenant_id" = pi."tenant_id"
    AND inv."material_code" = pi."material_code"
    AND COALESCE(inv."batch_code", ' ') = COALESCE(pi."batch_code", ' ')
    AND inv."erp_inventory" = pi."erp_inventory"
LEFT JOIN outbound_log_agg outbound_log
    ON outbound_log."tenant_id" = pi."tenant_id"
    AND outbound_log."material_code" = pi."material_code"
    AND COALESCE(outbound_log."batch_code", ' ') = COALESCE(pi."batch_code", ' ')
    AND outbound_log."erp_inventory" = pi."erp_inventory"
-- 项目级字段（名称、类型、采购人）：只按 posid 取
LEFT JOIN (
    SELECT DISTINCT ON (posid)
        posid, zpost1, z_user, plancat_txt
    FROM wbs_zmmrp048_parsed
    WHERE char_length(COALESCE(zpost1, '')) > 0
    ORDER BY posid, update_date DESC
) erp_proj ON erp_proj.posid = pi."owner_project_code"

-- 物料级字段（名称、单位）：只按 matnr 取
LEFT JOIN (
    SELECT DISTINCT ON (matnr)
        matnr, maktx, msehl
    FROM wbs_zmmrp048_parsed
    WHERE char_length(maktx) > 0
    ORDER BY matnr, update_date DESC
) erp_mat ON erp_mat.matnr = pi."material_code"
-- wms_material 备选物料名称（ERP 目录中没有时使用）
LEFT JOIN wms_material wms_mat ON wms_mat.code = pi."material_code" AND wms_mat.del_flag = '0';

COMMENT ON VIEW v_rpt_inventory_report IS '采购批次库存报表 v6 — 入库/出库金额均用original原始单价，领用=仅pick(31)，出库=全部类型。入库 ≈ 出库 + 当前库存';
