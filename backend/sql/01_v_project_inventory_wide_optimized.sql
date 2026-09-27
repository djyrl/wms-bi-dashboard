-- =====================================================================
-- 视图：v_project_inventory_wide
-- 说明：以 wms_inventory（真实物理库存）作为主表，
--       先按批次聚合（避免多货位产生重复行），
--       再通过主键关联 wms_project_inventory（项目台账）、
--       dim_material_cache、dim_project_cache、
--       dim_location_cache、dim_outbound_log_cache
--
-- 表关联关系：
--   inv_agg（wms_inventory 批次聚合） ←→  wms_project_inventory    (tenant_id, material_code, batch_code, erp_inventory)
--   inv_agg                           ←→  dim_outbound_log_cache    (tenant_id, material_code, batch_code, erp_inventory)
--   inv_agg                           ←→  dim_material_cache        (material_code)
--   wms_project_inventory             ←→  dim_project_cache          (owner_project_code = project_code)
/**  
inv_agg 只消除了同批次多货位的膨胀，但 LEFT JOIN wms_project_inventory 还会导致同批次多项目的膨胀：
    inv_agg（1行/批次）
  LEFT JOIN wms_project_inventory（N行/批次）
  = 视图 N 行/批次
**/
-- =====================================================================

CREATE OR REPLACE VIEW v_project_inventory_wide AS
WITH
-- 候选：通过状态/有效货位过滤的物理库存行（全量口径，含移库行）
inv_candidate AS (
    SELECT
        winv.id,
        winv.tenant_id,
        winv.material_code,
        winv.batch_code,
        winv.erp_inventory,
        winv.warehouse_code,
        winv.original_quantity,
        winv.current_quantity,
        winv.total_price,
        winv.unit_price,
        winv.inbound_date,
        winv.putaway_date,
        winv.supplier_code,
        winv.barcode,
        winv.inventory_code
    FROM wms_inventory winv
    WHERE winv.del_flag = '0' AND winv.status = 1
    AND EXISTS (
      SELECT 1 FROM wms_inventory_location iloc
      INNER JOIN wms_location loc ON iloc.location_id = loc.id AND loc.del_flag = '0'
      WHERE iloc.inventory_id = winv.id AND iloc.del_flag = '0'
        AND iloc.status = 1 AND iloc.current_quantity > 0
        AND loc.warehouse_code = 'A00'
    )
),
-- 物理库存按批次聚合（避免同批次多货位导致行膨胀）
-- 全量口径：含移库行（RELOCATION_ORDER）。移库是「源行扣减 + 迁移行承载」的拆库存行，
--           两行不会同时处于活跃状态（status=1 且 current_quantity>0），不存在重复计算；
--           排除移库行会漏算其承载的真实库存（2026-09 曾导致 135 个物资查不到）
inv_agg AS (
    SELECT
        tenant_id,
        material_code,
        batch_code,
        erp_inventory,
        SUM(original_quantity)              AS original_quantity,
        SUM(current_quantity)               AS current_quantity,
        -- CAST 保持列类型为 numeric(22,10)（与行级列一致），避免 CREATE OR REPLACE VIEW 报类型不匹配
        CAST(SUM(total_price) AS numeric(22,10))                    AS v_total_price,
        CAST(CASE
            WHEN SUM(current_quantity) > 0
            THEN SUM(current_quantity * unit_price) / SUM(current_quantity)
            ELSE AVG(unit_price)
        END AS numeric(22,10))                                      AS v_unit_price,
        MIN(inbound_date)                   AS inbound_date,
        MAX(putaway_date)                   AS putaway_date,
        MAX(supplier_code)                  AS supplier_code,
        MAX(barcode)                        AS barcode,
        MAX(inventory_code)                 AS inventory_code,
        MAX(warehouse_code)                 AS warehouse_code
    FROM inv_candidate c
    GROUP BY tenant_id, material_code, batch_code,warehouse_code,erp_inventory
)
SELECT
    -- ==================== 物理库存主键（批次级） ====================
    inv.tenant_id,
    inv.material_code                  AS material_code,  -- 物料编码
    inv.batch_code                    AS batch_code,      -- 批次编码
    inv.erp_inventory                 AS erp_inventory,   -- ERP库存标识
    inv.barcode                                                                                 AS barcode,         -- 条码
    inv.inventory_code                                                                          AS inventory_code,  -- 库存编码
    inv.supplier_code                                                                           AS supplier_code,   -- 供应商编码

    -- ==================== 物理库存数量 & 金额（批次聚合后） ====================
    inv.original_quantity   AS original_quantity,   -- 原始数量
    inv.current_quantity    AS inv_current_quantity, -- 当前库存数量（批次级）
    inv.v_total_price       AS total_price,
    inv.v_unit_price        AS unit_price,

    -- ==================== 物料维度（dim_material_cache PK: material_code）====================
    dm.material_name                                                                            AS material_name,       -- 物料名称
    dm.material_unit                                                                            AS material_unit,       -- 物料单位
    dm.material_group_code                                                                      AS material_group_code, -- 物料组编码
    dm.material_description                                                                     AS material_description, -- 物料描述

    -- ==================== 项目台账（wms_project_inventory PK: id，通过四字段关联）====================
    pi.id                                                                                       AS project_inventory_id,    -- 项目台账ID
    pi.owner_project_code                                                                       AS owner_project_code,      -- 项目编码
    pi.owner_project_type                                                                       AS owner_project_type,      -- 项目类型
    pi.current_quantity                                                                         AS current_quantity,        -- 项目库存数量（兼容旧名）
    pi.current_quantity                                                                         AS pi_current_quantity,     -- 项目库存数量（供 project_ratio 窗口函数）
    pi.locked_quantity                                                                          AS pi_locked_quantity,      -- 项目锁定数量
    pi.available_quantity                                                                       AS pi_available_quantity,   -- 项目可用数量

    -- ==================== 项目维度（dim_project_cache PK: project_code = owner_project_code）====================
    dp.project_name                                                                             AS project_name,        -- 项目名称
    dp.plan_category                                                                            AS plan_category,       -- 计划类别
    dp.purchaser_name                                                                           AS purchaser_name,      -- 采购员
    dp.department_name                                                                          AS department_name,     -- 部门名称
    dp.project_submitter                                                                        AS project_submitter,   -- 提交人
    dp.project_contact                                                                          AS project_contact,     -- 联系人

    -- ==================== 时间维度 ====================
    inv.inbound_date                                                                            AS inbound_date,    -- 入库日期
    inv.putaway_date                                                                            AS putaway_date,    -- 货架上架日期
    pi.create_date                                                                              AS create_date,     -- 台账创建日期
    -- 库龄天数（以入库日期为准，无则用台账创建日期）
    EXTRACT(DAY FROM (CURRENT_DATE - COALESCE(inv.inbound_date, pi.create_date)::timestamp))::int AS age_days,

    -- ==================== 出库维度（dim_outbound_log_cache PK: tenant_id + material_code + batch_code + erp_inventory）====================
    COALESCE(ol.total_outbound_quantity, 0)                                                     AS total_outbound_quantity, -- 总出库数量
    COALESCE(ol.pick_quantity, 0)                                                               AS pick_quantity,           -- 领料出库数量（真领用）
    COALESCE(ol.reversal_quantity, 0)                                                           AS reversal_quantity,       -- 收货冲销数量
    COALESCE(ol.return_quantity, 0)                                                             AS return_quantity,         -- 采购退货数量
    COALESCE(ol.repair_quantity, 0)                                                             AS repair_quantity,         -- 维修数量
    COALESCE(ol.scrap_quantity, 0)                                                              AS scrap_quantity,          -- 报废数量
    COALESCE(ol.repaired_quantity, 0)                                                           AS repaired_quantity,       -- 返修数量
    ol.last_outbound_time                                                                       AS last_outbound_time       -- 最后出库时间（operation_time）

FROM inv_agg inv

-- 项目台账：通过 (tenant_id, material_code, batch_code, erp_inventory) 关联
LEFT JOIN wms_project_inventory pi
    ON  pi.tenant_id      = inv.tenant_id
    AND pi.material_code  = inv.material_code
    AND pi.batch_code     = inv.batch_code
    AND pi.warehouse_code  = inv.warehouse_code
    AND pi.erp_inventory  = inv.erp_inventory
    AND pi.del_flag       = '0'

-- 物料维度：通过 material_code 关联
LEFT JOIN dim_material_cache dm
    ON dm.material_code = inv.material_code

-- 项目维度：通过 project_code = owner_project_code 关联
LEFT JOIN dim_project_cache dp
    ON dp.project_code = pi.owner_project_code

-- 出库日志：通过 (tenant_id, material_code, batch_code, erp_inventory) 关联
LEFT JOIN dim_outbound_log_cache ol
    ON  ol.tenant_id      = inv.tenant_id
    AND ol.material_code  = inv.material_code
    AND ol.batch_code     = inv.batch_code
    AND ol.erp_inventory  = inv.erp_inventory;


COMMENT ON VIEW v_project_inventory_wide IS '核心宽表 — wms_inventory 批次聚合后通过主键关联 dim_material_cache + wms_project_inventory + dim_project_cache + dim_outbound_log_cache';
