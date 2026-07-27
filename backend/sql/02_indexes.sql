-- =====================================================================
-- 推荐索引（部署前请先确认表结构和现有索引）
-- 说明：针对视图查询瓶颈添加的复合索引，大幅提升 JOIN 和过滤性能
-- =====================================================================

-- ---------------------------------------------------------------
-- 1. wms_inventory 表索引
-- ---------------------------------------------------------------
-- filtered_inventory CTE 的 WHERE 条件过滤
CREATE INDEX IF NOT EXISTS idx_wms_inv_filter
    ON wms_inventory (del_flag, status, current_quantity)
    WHERE del_flag = '0' AND status = 1 AND current_quantity > 0;

-- official_inventory CTE 的 GROUP BY 维度
CREATE INDEX IF NOT EXISTS idx_wms_inv_material_batch_erp
    ON wms_inventory (tenant_id, material_code, batch_code, erp_inventory)
    WHERE del_flag = '0' AND status = 1 AND current_quantity > 0;

-- ---------------------------------------------------------------
-- 2. wms_inventory_location 表索引
-- ---------------------------------------------------------------
-- filtered_inventory 的 EXISTS 子查询
CREATE INDEX IF NOT EXISTS idx_wms_invloc_inv_filter
    ON wms_inventory_location (inventory_id, del_flag, status, current_quantity)
    WHERE del_flag = '0' AND status = 1 AND current_quantity > 0;

-- v_dim_location 的 GROUP BY
CREATE INDEX IF NOT EXISTS idx_wms_invloc_location
    ON wms_inventory_location (inventory_id, location_id)
    WHERE del_flag = '0' AND status = 1;

-- ---------------------------------------------------------------
-- 3. wms_location 表索引
-- ---------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_wms_loc_pk_delflag
    ON wms_location (id, del_flag);

-- ---------------------------------------------------------------
-- 4. wms_inventory_log 表索引（出库日志 — 最大瓶颈）
-- ---------------------------------------------------------------
-- v_dim_outbound_log 的过滤条件
CREATE INDEX IF NOT EXISTS idx_wms_invlog_type_filter
    ON wms_inventory_log (inventory_id, change_type, change_quantity)
    WHERE del_flag = '0' AND change_type IN (31, 34, 35, 36);

-- 按 inventory_id 快速关联
CREATE INDEX IF NOT EXISTS idx_wms_invlog_inv_id
    ON wms_inventory_log (inventory_id)
    WHERE del_flag = '0';

-- ---------------------------------------------------------------
-- 5. wms_project_inventory 表索引
-- ---------------------------------------------------------------
-- project_inventory_with_ratio CTE 的窗口函数 PARTITION BY
CREATE INDEX IF NOT EXISTS idx_wms_projinv_partition
    ON wms_project_inventory (tenant_id, material_code, batch_code, erp_inventory, current_quantity)
    WHERE del_flag = '0';

-- ---------------------------------------------------------------
-- 6. ERP 解析表索引
-- ---------------------------------------------------------------
-- v_dim_material 的 DISTINCT ON
CREATE INDEX IF NOT EXISTS idx_zmmrp048_matnr
    ON wbs_zmmrp048_parsed (matnr, update_date DESC)
    WHERE char_length(COALESCE(maktx, '')) > 0;

-- v_dim_project 的 DISTINCT ON
CREATE INDEX IF NOT EXISTS idx_zmmrp048_posid
    ON wbs_zmmrp048_parsed (posid, update_date DESC)
    WHERE char_length(COALESCE(zpost1, '')) > 0;

-- v_dim_project 的 ZMMRP226 聚合
CREATE INDEX IF NOT EXISTS idx_zmmrp226_wbs
    ON wbs_zmmrp226_parsed (z_dxxmh, tenant_id)
    WHERE z_dxxmh IS NOT NULL;

-- ---------------------------------------------------------------
-- 7. wms_material 表索引
-- ---------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_wms_material_code
    ON wms_material (code)
    WHERE del_flag = '0';
