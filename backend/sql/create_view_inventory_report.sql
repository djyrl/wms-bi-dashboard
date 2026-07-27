-- =====================================================================
-- 报表视图：库存报表 (v_rpt_inventory_report)
-- 说明：v_inventory_report 的兼容替代品，基于 v_project_inventory_wide 薄包装
--       列名和语义与旧视图完全一致，Python 程序零改动
-- =====================================================================
CREATE OR REPLACE VIEW v_rpt_inventory_report AS
SELECT
    -- 主键
    w.project_inventory_id                  AS id,
    -- 采购批次
    w.batch_code                            AS purchase_batch,
    -- 物料名称（ERP 优先已在 v_dim_material 处理）
    w.material_name,
    -- 物料编码
    w.material_code,
    -- 项目编码（WMS001 兜底已在宽表处理）
    w.owner_project_code                    AS project_code,
    -- 项目名称（非项目物资兜底）
    CASE
        WHEN w.owner_project_code = 'WMS001' THEN '非项目物资'
        ELSE w.project_name
    END                                     AS project_name,
    -- 采购人
    w.purchaser_name,
    -- 项目类型
    w.plan_category                         AS project_type,
    -- 时间
    w.inbound_date::date                    AS inbound_date,
    w.putaway_date::date                    AS putaway_date,
    -- 批次
    w.batch_code,
    -- 数量
    w.original_quantity,
    w.current_quantity,
    -- 出库数量（按项目占比分摊）
    ROUND((w.total_outbound_quantity
           * w.project_ratio)::numeric, 4)  AS used_quantity,
    ROUND((w.pick_quantity
           * w.project_ratio)::numeric, 4)  AS pick_quantity,
    ROUND((w.repair_quantity
           * w.project_ratio)::numeric, 4)  AS repair_quantity,
    ROUND((w.scrap_quantity
           * w.project_ratio)::numeric, 4)  AS scrap_quantity,
    ROUND((w.repaired_quantity
           * w.project_ratio)::numeric, 4)  AS repaired_quantity,
    -- 单价
    w.unit_price,
    -- 单位
    w.material_unit                         AS unit,
    -- 供应商
    w.supplier_code,
    -- 金额
    w.inbound_amount,
    w.claimed_amount,
    w.inventory_amount,
    w.claim_rate_on_inventory AS claim_rate, -- 库存口径
    w.claim_rate_on_inbound, -- 入库口径
    -- 库龄
    w.age_days

FROM v_project_inventory_wide w;

COMMENT ON VIEW v_rpt_inventory_report IS '采购批次库存报表 — v_inventory_report 兼容视图，列名/语义不变，Python 程序零改动';


-- ============================================================
-- 补录 wms_project_inventory：33条物理库存缺少项目台账记录
-- 目标：使视图 v_rpt_inventory_report 的 inventory_amount 从 3918.30万 对齐到 4130.35万
-- 执行前请备份: SELECT * INTO wms_project_inventory_bak_20260714 FROM wms_project_inventory;
-- ============================================================

INSERT INTO wms_project_inventory (
    id, tenant_id, material_code, batch_code,
    owner_project_type, owner_project_code,
    erp_inventory, current_quantity, locked_quantity, available_quantity,
    warehouse_code, del_flag, create_date, remarks
)
SELECT
    -- 用 md5 生成确定性唯一 ID（基于 tenant+material+batch+erp 组合）
    ('x' || SUBSTR(MD5(inv.tenant_id || '|' || inv.material_code || '|' || COALESCE(inv.batch_code,'') || '|' || inv.erp_inventory), 1, 15))::BIT(60)::BIGINT AS id,
    inv.tenant_id,
    inv.material_code,
    inv.batch_code,
    NULL AS owner_project_type,
    NULL AS owner_project_code,
    inv.erp_inventory,
    SUM(inv.current_quantity)  AS current_quantity,
    0 AS locked_quantity,
    SUM(inv.current_quantity)  AS available_quantity,
    MAX(inv.warehouse_code)    AS warehouse_code,
    '0' AS del_flag,
    NOW() AS create_date,
    '补录：物理库存存在但项目台账缺失的记录，对齐 v_rpt_inventory_report 金额'
FROM wms_inventory inv
WHERE inv.del_flag = '0' AND inv.status = 1 AND inv.current_quantity > 0
GROUP BY inv.tenant_id, inv.material_code, inv.batch_code, inv.erp_inventory
HAVING NOT EXISTS (
    SELECT 1 FROM wms_project_inventory pi
    WHERE pi.del_flag = '0' AND pi.current_quantity > 0
      AND pi.tenant_id = inv.tenant_id
      AND pi.material_code = inv.material_code
      AND COALESCE(pi.batch_code, '') = COALESCE(inv.batch_code, '')
      AND pi.erp_inventory = inv.erp_inventory
);


有 87 个物理库存分组（material_code + batch_code）在 wms_project_inventory 表中完全没有对应记录。
这些库存可能是：
1、历史数据在拆离项目维度（V3.2.8）时，部分批次未创建项目台账
2、某些入库操作触发了物理库存更新但没有同步创建 project_inventory 行
你之前说的 "3918.30万万元" 其实是 3918.30 万元（inventory_amount 字段单位是元），并不是万亿级别，只是比物理库存总额少了 212 万。