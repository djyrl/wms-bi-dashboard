-- =====================================================================
-- 物化维度表（替代实时维度视图，大幅提升查询性能）
-- 说明：将维度视图的计算结果持久化到物理表，定时刷新
--       宽表查询时 JOIN 物理表而非视图，避免视图套视图的性能开销
--
-- 刷新策略建议：
--   - 维度数据变化不频繁（ERP 数据每天同步一次），建议每小时或每天刷新
--   - 可通过 pg_cron 或应用程序定时任务调用刷新函数
-- =====================================================================

-- ---------------------------------------------------------------
-- 1. 物料维度物化表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_material_cache (
    material_code        VARCHAR PRIMARY KEY,
    material_name        VARCHAR,
    material_unit        VARCHAR,
    material_group_code  VARCHAR,
    material_description TEXT,
    material_storage_code VARCHAR,
    data_source          VARCHAR(10),
    refreshed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_mat_name ON dim_material_cache (material_name);

-- ---------------------------------------------------------------
-- 2. 项目维度物化表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_project_cache (
    project_code          VARCHAR PRIMARY KEY,
    project_name          VARCHAR,
    plan_category         VARCHAR,
    purchaser_name        VARCHAR,
    department_name       VARCHAR,
    project_submitter     VARCHAR,
    project_contact       VARCHAR,
    internal_project_code VARCHAR,
    tenant_id             BIGINT,
    refreshed_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_proj_name ON dim_project_cache (project_name);

-- ---------------------------------------------------------------
-- 3. 货位维度物化表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_location_cache (
    inventory_id       BIGINT PRIMARY KEY,
    location_codes     TEXT,
    location_barcodes  TEXT,
    location_names     TEXT,
    location_count     INT,
    warehouse_code     VARCHAR,
    warehouse_name     VARCHAR,
    refreshed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------
-- 4. 出库日志维度物化表
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_outbound_log_cache (
    id                      BIGSERIAL PRIMARY KEY,
    tenant_id               BIGINT NOT NULL,
    material_code           VARCHAR NOT NULL,
    batch_code              VARCHAR,
    erp_inventory           VARCHAR NOT NULL,
    total_outbound_quantity NUMERIC,
    pick_quantity           NUMERIC,          -- 领料出库数量（REQUISITION_ORDER，真领用）
    reversal_quantity       NUMERIC,          -- 收货冲销数量（GOODS_RECEIPT_REVERSAL_OUTBOUND_ORDER）
    return_quantity         NUMERIC,          -- 采购退货数量（PURCHASE_RETURN_ORDER）
    repair_quantity         NUMERIC,
    scrap_quantity          NUMERIC,
    repaired_quantity       NUMERIC,
    last_outbound_time      TIMESTAMP,       -- 最后出库时间（wms_inventory_log.operation_time）
    refreshed_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 已存在表时补充新增列（冲销/退货拆分，兼容旧库升级）
ALTER TABLE dim_outbound_log_cache ADD COLUMN IF NOT EXISTS reversal_quantity NUMERIC;
ALTER TABLE dim_outbound_log_cache ADD COLUMN IF NOT EXISTS return_quantity NUMERIC;

-- batch_code 非空时强制四列唯一（允许 NULL 行共存）
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_outbound_uniq
    ON dim_outbound_log_cache (tenant_id, material_code, batch_code, erp_inventory)
    WHERE batch_code IS NOT NULL;

-- 日常查询索引
CREATE INDEX IF NOT EXISTS idx_dim_outbound_4cols
    ON dim_outbound_log_cache (tenant_id, material_code, batch_code, erp_inventory);

-- =====================================================================
-- 刷新函数：直接查询源表（不经过维度视图），一次性刷新所有缓存表
-- =====================================================================
CREATE OR REPLACE FUNCTION fn_refresh_dim_caches() RETURNS void AS $$
BEGIN
    -- -----------------------------------------------------------
    -- 1. 刷新物料维度：wms_material + wbs_zmmrp048_parsed
    -- -----------------------------------------------------------
    TRUNCATE TABLE dim_material_cache;
    INSERT INTO dim_material_cache (
        material_code, material_name, material_unit,
        material_group_code, material_description, material_storage_code,
        data_source
    )
    WITH erp_material AS (
        SELECT DISTINCT ON (matnr)
            matnr, maktx, msehl
        FROM wbs_zmmrp048_parsed
        WHERE char_length(COALESCE(maktx, '')) > 0
        ORDER BY matnr, update_date DESC
    )
    SELECT
        COALESCE(e.matnr, w.code),
        COALESCE(NULLIF(e.maktx, ' '), w.name),
        COALESCE(e.msehl, w.unit),
        w.material_group_code,
        w.description,
        w.storage_code,
        CASE
            WHEN e.matnr IS NOT NULL THEN 'ERP'
            WHEN w.code  IS NOT NULL THEN 'WMS'
            ELSE 'UNKNOWN'
        END
    FROM wms_material w
    FULL OUTER JOIN erp_material e ON e.matnr = w.code
    WHERE w.del_flag = '0' OR e.matnr IS NOT NULL;

    -- -----------------------------------------------------------
    -- 2. 刷新项目维度：wbs_zmmrp226_parsed + wbs_zmmrp048_parsed
    -- -----------------------------------------------------------
    TRUNCATE TABLE dim_project_cache;
    INSERT INTO dim_project_cache (
        project_code, project_name, plan_category,
        purchaser_name, department_name, project_submitter,
        project_contact, internal_project_code, tenant_id
    )
    WITH
    zmmrp226_agg AS (
        SELECT
            z_dxxmh            AS wbs_code,
            tenant_id,
            MAX(post1)         AS wbs_description,
            MAX(z_jhlb_nm)     AS plan_category,
            MAX(reqptmt_name)  AS department_name,
            MAX(z_name)        AS submitter,
            MAX(contact)       AS project_contact,
            MAX(zzxmbh)        AS project_code
        FROM (
            SELECT DISTINCT z_dxxmh, tenant_id, post1,
                   z_jhlb_nm, reqptmt_name, z_name, contact, zzxmbh, pbdnr
            FROM wbs_zmmrp226_parsed
            WHERE z_dxxmh IS NOT NULL
        ) sub
        GROUP BY z_dxxmh, tenant_id
    ),
    zmmrp048_agg AS (
        SELECT DISTINCT ON (posid)
            posid, zpost1, z_user, plancat_txt
        FROM wbs_zmmrp048_parsed
        WHERE char_length(COALESCE(zpost1, '')) > 0
        ORDER BY posid, update_date DESC
    )
    SELECT
        COALESCE(r.wbs_code, p.posid),
        COALESCE(r.wbs_description, p.zpost1),
        COALESCE(r.plan_category, p.plancat_txt),
        p.z_user,
        r.department_name,
        r.submitter,
        r.project_contact,
        r.project_code,
        r.tenant_id
    FROM zmmrp226_agg r
    FULL OUTER JOIN zmmrp048_agg p ON p.posid = r.wbs_code;

    -- -----------------------------------------------------------
    -- 3. 刷新货位维度：wms_inventory_location + wms_location + wms_warehouse
    -- -----------------------------------------------------------
    TRUNCATE TABLE dim_location_cache;
    INSERT INTO dim_location_cache (
        inventory_id, location_codes, location_barcodes,
        location_names, location_count, warehouse_code, warehouse_name
    )
    SELECT
        il.inventory_id,
        LISTAGG(loc.code, ', ')   WITHIN GROUP (ORDER BY loc.code),
        LISTAGG(loc.barcode, ', ') WITHIN GROUP (ORDER BY loc.code),
        LISTAGG(loc.name, ', ')   WITHIN GROUP (ORDER BY loc.code),
        COUNT(*),
        MIN(loc.warehouse_code),
        MAX(wh.name)
    FROM wms_inventory_location il
    INNER JOIN wms_location loc
        ON loc.id = il.location_id AND loc.del_flag = '0'
    LEFT JOIN wms_warehouse wh
        ON wh.code = loc.warehouse_code AND wh.del_flag = '0'
    WHERE il.status = 1 AND il.del_flag = '0'
    GROUP BY il.inventory_id;

    -- -----------------------------------------------------------
    -- 4. 刷新出库日志维度：wms_inventory + wms_inventory_log
    -- -----------------------------------------------------------
    TRUNCATE TABLE dim_outbound_log_cache;
    INSERT INTO dim_outbound_log_cache (
        tenant_id, material_code, batch_code, erp_inventory,
        total_outbound_quantity, pick_quantity, reversal_quantity, return_quantity,
        repair_quantity, scrap_quantity, repaired_quantity, last_outbound_time
    )
    SELECT
        inv.tenant_id,
        inv.material_code,
        inv.batch_code,
        inv.erp_inventory,
        -- 总出库（全部 31/34/35/36）
        SUM(log.change_quantity),
        -- 领料出库（REQUISITION_ORDER，真领用）
        SUM(CASE WHEN log.change_type = 31 AND log.business_type = 'REQUISITION_ORDER'
                 THEN log.change_quantity ELSE 0 END),
        -- 收货冲销（GOODS_RECEIPT_REVERSAL_OUTBOUND_ORDER，应冲减入库而非计入领用）
        SUM(CASE WHEN log.change_type = 31 AND log.business_type = 'GOODS_RECEIPT_REVERSAL_OUTBOUND_ORDER'
                 THEN log.change_quantity ELSE 0 END),
        -- 采购退货（PURCHASE_RETURN_ORDER，应冲减入库而非计入领用）
        SUM(CASE WHEN log.change_type = 31 AND log.business_type = 'PURCHASE_RETURN_ORDER'
                 THEN log.change_quantity ELSE 0 END),
        -- 维修 / 报废 / 返修
        SUM(CASE WHEN log.change_type = 34 THEN log.change_quantity ELSE 0 END),
        SUM(CASE WHEN log.change_type = 35 THEN log.change_quantity ELSE 0 END),
        SUM(CASE WHEN log.change_type = 36 THEN log.change_quantity ELSE 0 END),
        MAX(log.update_date)
    FROM wms_inventory inv
    INNER JOIN wms_inventory_log log ON log.inventory_id = inv.id
    WHERE log.change_type IN (31, 34, 35, 36)
      AND log.del_flag = '0'
      AND inv.del_flag = '0'
      AND inv.batch_code IS NOT NULL
    GROUP BY inv.tenant_id, inv.material_code, inv.batch_code, inv.erp_inventory;

    RAISE NOTICE '所有维度缓存表刷新完成: %', CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_refresh_dim_caches() IS '刷新所有维度缓存表 — 直接查询源表，不经维度视图';
