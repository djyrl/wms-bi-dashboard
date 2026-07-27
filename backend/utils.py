"""
采购库存 BI — 公共工具模块
========================
数据库连接、查询辅助、数据转换。

金额计算统一采用「方式二：物理批次去重」：
  1. 先 DISTINCT ON (tenant_id, material_code, batch_code, inventory_code) 去重
  2. 在去重后的批次上计算 inboud_amt / claimed_amt / inventory_amt
  3. 如需项目级金额，再 JOIN 回项目行，按 project_ratio 分配

project_ratio 仅用于项目金额分配，不用于计算批次总额。
"""

import psycopg2
import psycopg2.extras
from typing import Any, Dict, List, Optional

from db_config import DB_CONFIG


def _f(v) -> float:
    if v is None:
        return 0.0
    return float(v)


def _rows_to_float(rows: List[Dict], *fields: str) -> List[Dict]:
    for r in rows:
        for f in fields:
            if f in r:
                r[f] = _f(r[f])
    return rows


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        if conn:
            conn.close()


def query_one(sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    rows = query(sql, params)
    return rows[0] if rows else None


# ================================================================
#  批次级金额计算（方式二：物理批次去重）
#  所有金额汇总接口统一用这个 CTE 作为金额来源
# ================================================================

_BATCH_AMOUNTS_SQL = """
    batch_amounts AS (
        SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
            tenant_id,
            material_code,
            batch_code,
            erp_inventory                       AS inv_code,
            original_quantity * unit_price       AS batch_inbound,
            total_outbound_quantity * unit_price AS batch_claimed,
            total_price                         AS batch_inventory,
            original_quantity                   AS batch_orig_qty,
            total_outbound_quantity             AS batch_outbound_qty,
            unit_price                          AS batch_unit_price,
            age_days                            AS batch_age_days,
            inbound_date,
            plan_category,
            material_group_code
        FROM v_project_inventory_wide
    )
"""

# ================================================================
#  project_ratio — 仅用于项目级金额分配，不用于计算总额
# ================================================================

_PROJECT_RATIO_SQL = """
    CASE
        WHEN w.pi_current_quantity IS NULL THEN 1.0
        WHEN SUM(w.pi_current_quantity) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        ) = 0
        THEN 1.0::numeric / COUNT(*) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        )
        ELSE w.pi_current_quantity::numeric / SUM(w.pi_current_quantity) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        )
    END
"""


def _get_inventory_rows() -> List[Dict]:
    """
    从 v_project_inventory_wide 获取库存明细（按项目展开）。

    金额计算流程：
      1. batch_amounts CTE — 物理批次去重，计算批次级金额
      2. 关联回项目行，用 project_ratio 分配批次金额到各项目
      3. Σ(项目金额) = 批次金额（project_ratio 按批次求和 = 1.0）

    返回列兼容所有旧调用方。
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.*,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
                ba.batch_orig_qty,
                ba.batch_outbound_qty,
                ba.batch_unit_price,
                ba.batch_age_days,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
        )
        SELECT
            r.project_inventory_id                  AS id,
            r.batch_code                            AS purchase_batch,
            r.material_name,
            r.material_code,
            r.owner_project_code                    AS project_code,
            r.project_name,
            r.project_submitter                     AS purchaser_name,  -- 提报人（采购归属）
            r.purchaser_name                        AS applicant_name,   -- 申请人
            r.project_contact                       AS contact_name,     -- 联系人
            r.plan_category                         AS project_type,
            r.inbound_date::date                    AS inbound_date,
            r.putaway_date::date                    AS putaway_date,
            r.batch_code,
            r.original_quantity,
            r.pi_current_quantity                   AS current_quantity,
            ROUND((r.batch_outbound_qty
                   * r.project_ratio)::numeric, 4)  AS used_quantity,
            ROUND((r.batch_outbound_qty
                   * r.project_ratio)::numeric, 4)  AS pick_quantity,
            ROUND((r.batch_outbound_qty
                   * r.project_ratio)::numeric, 4)  AS repair_quantity,
            ROUND((r.batch_outbound_qty
                   * r.project_ratio)::numeric, 4)  AS scrap_quantity,
            ROUND((r.batch_outbound_qty
                   * r.project_ratio)::numeric, 4)  AS repaired_quantity,
            r.batch_unit_price                      AS unit_price,
            r.material_unit                         AS unit,
            r.supplier_code,
            -- 项目级金额 = 批次金额 × 项目占比
            ROUND((r.batch_inbound
                   * r.project_ratio)::numeric, 2)  AS inbound_amount,
            ROUND((r.batch_claimed
                   * r.project_ratio)::numeric, 2)  AS claimed_amount,
            ROUND((r.batch_inventory
                   * r.project_ratio)::numeric, 2)  AS inventory_amount,
            -- 领用率（批次级，非项目级）
            CASE WHEN r.batch_orig_qty > 0
                 THEN LEAST(ROUND(r.batch_outbound_qty::numeric
                          / r.batch_orig_qty * 100, 2), 100.00)
                 ELSE 0
            END                                     AS claim_rate,
            CASE WHEN r.batch_orig_qty > 0
                 THEN LEAST(ROUND(r.batch_outbound_qty::numeric
                          / r.batch_orig_qty * 100, 2), 100.00)
                 ELSE 0
            END                                     AS claim_rate_on_inbound,
            r.batch_age_days                        AS age_days
        FROM wide_with_ratio r
    """)
    return _rows_to_float(rows,
        "original_quantity", "current_quantity", "used_quantity",
        "pick_quantity", "repair_quantity", "scrap_quantity", "repaired_quantity",
        "unit_price", "inbound_amount", "claimed_amount",
        "inventory_amount", "claim_rate", "age_days")


def _get_batch_rows() -> List[Dict]:
    """获取批次级明细（物理去重），用于需要逐批次迭代的场景（如 age_structure）。"""
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            batch_inbound   AS inbound_amount,
            batch_claimed   AS claimed_amount,
            batch_inventory AS inventory_amount,
            batch_orig_qty  AS original_quantity,
            batch_outbound_qty AS used_quantity,
            batch_unit_price AS unit_price,
            batch_age_days  AS age_days,
            inbound_date,
            material_group_code
        FROM batch_amounts
    """)
    return _rows_to_float(rows,
        "inbound_amount", "claimed_amount", "inventory_amount",
        "original_quantity", "used_quantity", "unit_price", "age_days")


def _get_wide_batch_aggregates(year: Optional[int] = None) -> Dict[str, float]:
    """
    按物理批次去重聚合。
    若指定 year，只统计 inbound_date 在该自然年的批次。
    """
    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            COALESCE(SUM(batch_inbound), 0)   AS total_inbound_amount,
            COALESCE(SUM(batch_claimed), 0)   AS total_claimed_amount,
            COALESCE(SUM(batch_inventory), 0) AS total_inventory_amount,
            COALESCE(SUM(batch_orig_qty), 0)  AS original_quantity,
            COALESCE(SUM(batch_outbound_qty), 0) AS total_outbound_quantity
        FROM batch_amounts
        WHERE %s IS NULL OR EXTRACT(YEAR FROM inbound_date) = %s
    """
    rows = query(sql, (year, year))
    if not rows:
        return {
            "total_inbound_amount": 0.0,
            "total_claimed_amount": 0.0,
            "total_inventory_amount": 0.0,
            "original_quantity": 0.0,
            "total_outbound_quantity": 0.0,
        }
    return _rows_to_float(rows, *rows[0].keys())[0]


def _get_wide_structure_aggregates() -> Dict[str, List[Dict]]:
    """
    按项目和采购人聚合库存金额（项目分摊后）。
    金额来源：批次去重 × project_ratio。
    """
    project_rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.owner_project_code,
                w.project_name,
                w.purchaser_name,
                ba.batch_inventory,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
        )
        SELECT
            owner_project_code,
            MAX(project_name) AS project_name,
            SUM(batch_inventory * project_ratio) AS inventory_amount
        FROM wide_with_ratio
        GROUP BY owner_project_code
        ORDER BY inventory_amount DESC NULLS LAST
    """)
    project_rows = _rows_to_float(project_rows, "inventory_amount")

    purchaser_rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.project_submitter,
                ba.batch_inventory,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE w.project_submitter IS NOT NULL
              AND char_length(w.project_submitter) > 0
        )
        SELECT
            project_submitter AS purchaser_name,
            SUM(batch_inventory * project_ratio) AS inventory_amount
        FROM wide_with_ratio
        GROUP BY project_submitter
        ORDER BY inventory_amount DESC
    """)
    purchaser_rows = _rows_to_float(purchaser_rows, "inventory_amount")

    return {"project_rows": project_rows, "purchaser_rows": purchaser_rows}
