"""
采购库存 BI — 维度指标计算模块
===============================
按项目和采购人维度的库存分析指标。

数据来源：v_project_inventory_wide。
金额统一来源：utils._BATCH_AMOUNTS_SQL（批次去重）+ _PROJECT_RATIO_SQL（项目分配）。

计算流程：
  1. batch_amounts CTE → 物理批次去重，计算批次级金额
  2. wide_with_ratio → JOIN 回视图获取项目/采购人信息，× project_ratio 分配
  3. GROUP BY 维度 → 聚合

提供：
  - get_by_project():       所有项目的领用率、未消耗库存、平均库龄
  - get_by_purchaser():     所有采购人（联系人）的同类指标
  - get_project_summary():  项目维度汇总（支持排序）
  - get_purchaser_summary(): 采购人维度汇总（支持排序）
"""

from typing import Any, Dict, List

from utils import (
    query, _f, _rows_to_float,
    _BATCH_AMOUNTS_SQL, _PROJECT_RATIO_SQL, _date_filter_sql,
)


# ── 允许的排序字段映射（防止 SQL 注入）──
ALLOWED_SORT_COLUMNS = {
    "claim_rate": "claim_rate",
    "age_days": "age_days",
    "avg_age_days": "avg_age_days",
    "inventory_amount": "inventory_amount",
    "inbound_amount": "inbound_amount",
    "inbound_date": "inbound_date",
}


def get_by_project(owner_project_type: str = None, start_date=None, end_date=None) -> List[Dict]:
    """
    按项目维度分析：每个项目的领用率、未消耗库存金额、平均库龄。

    SQL 聚合模式：
      batch_amounts → JOIN 视图 → project_ratio 分配 → GROUP BY project_code

    Args:
        owner_project_type: 可选，按项目类型过滤（如 'Q' 表示特定类项目）。
                            为 None 时不过滤，返回所有项目。
        start_date:         可选，入库日期下限（'YYYY-MM-DD'）
        end_date:           可选，入库日期上限（'YYYY-MM-DD'）

    返回每个项目的：
      - project_code:          项目编码
      - project_name:          项目名称
      - inbound_amount:        入库金额（项目分配后，元）
      - claimed_amount:        领用金额（项目分配后，元）
      - unclaimed_amount:      未消耗库存金额（项目分配后，元）= 库存金额
      - claim_rate:            领用率（%）= claimed / inbound × 100，上限 100%
      - avg_age_days:          金额加权平均库龄（天）
      - over90_ratio:          库龄 ≥ 90 天的库存占比（%）
      - record_count:          记录数

    Returns:
        List[Dict]: 所有项目（或指定类型）的分析数据，按库存金额降序
    """
    date_clause = _date_filter_sql(start_date, end_date)
    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        -- 批次金额 JOIN 视图，分配项目比例
        wide_with_ratio AS (
            SELECT
                w.owner_project_code AS project_code,
                w.project_name,
                w.owner_project_type,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
                ba.batch_age_days,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE 1=1{date_clause}
        )
        SELECT
            project_code,
            MAX(project_name) AS project_name,
            -- 项目级汇总：批次金额 × project_ratio 求和
            SUM(batch_inbound * project_ratio)   AS inbound_amt,
            SUM(batch_claimed * project_ratio)   AS claimed_amt,
            SUM(batch_inventory * project_ratio) AS inventory_amt,
            -- 加权库龄：Σ(项目库存金额 × 库龄)
            SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted,
            -- 库龄 ≥ 90 天的库存金额
            SUM(CASE WHEN batch_age_days >= 90
                THEN batch_inventory * project_ratio ELSE 0 END) AS over90_amt,
            COUNT(*) AS record_count
        FROM wide_with_ratio
        WHERE %s IS NULL OR wide_with_ratio.owner_project_type = %s
        GROUP BY project_code
        ORDER BY inventory_amt DESC
    """
    rows = query(sql, (owner_project_type, owner_project_type))
    rows = _rows_to_float(rows, "inbound_amt", "claimed_amt", "inventory_amt",
                         "age_weighted", "over90_amt")

    # ── 格式化输出 ──
    result = []
    for r in rows:
        code = r["project_code"] or ""
        inb, clm, inv, age_w, over90 = (
            r["inbound_amt"], r["claimed_amt"], r["inventory_amt"],
            r["age_weighted"], r["over90_amt"],
        )
        result.append({
            "project_code": code,
            "project_name": r["project_name"] or "",
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            # 未消耗库存 = 库存金额（恒等式：inbound - claimed ≈ inventory）
            "unclaimed_amount": round(inv, 2),
            # 领用率 = claimed / inbound，上限 100%
            "claim_rate": min(round(clm / inb * 100, 2), 100.00) if inb else 0,
            # 加权平均库龄
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
            # 库龄 ≥ 90 天占比
            "over90_ratio": round(over90 / inv * 100, 1) if inv else 0,
            "record_count": int(r["record_count"] or 0),
        })

    return result


def get_by_purchaser(start_date=None, end_date=None) -> List[Dict]:
    """
    按采购人（联系人）维度分析。

    与 get_by_project 逻辑相同，但按 project_contact 聚合。
    注意：project_contact 是项目联系人字段，与 project_submitter（提报人）不同。

    Args:
        start_date: 可选，入库日期下限（'YYYY-MM-DD'）
        end_date:   可选，入库日期上限（'YYYY-MM-DD'）

    返回每个采购人的：
      - purchaser_id:          采购人ID（= contact_name）
      - purchaser_name:        采购人名称
      - inbound_amount:        入库金额（元）
      - claimed_amount:        领用金额（元）
      - unclaimed_amount:      未消耗库存金额（元）
      - claim_rate:            领用率（%）
      - avg_age_days:          加权平均库龄（天）
      - record_count:          记录数

    Returns:
        List[Dict]: 所有采购人的分析数据，按库存金额降序
    """
    date_clause = _date_filter_sql(start_date, end_date)
    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.project_contact AS contact_name,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
                ba.batch_age_days,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE 1=1{date_clause}
        )
        SELECT
            contact_name AS purchaser_name,
            SUM(batch_inbound * project_ratio)   AS inbound_amt,
            SUM(batch_claimed * project_ratio)   AS claimed_amt,
            SUM(batch_inventory * project_ratio) AS inventory_amt,
            SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted,
            COUNT(*) AS record_count
        FROM wide_with_ratio
        WHERE contact_name IS NOT NULL AND char_length(contact_name) > 0
        GROUP BY contact_name
        ORDER BY inventory_amt DESC
    """
    rows = query(sql)
    rows = _rows_to_float(rows, "inbound_amt", "claimed_amt", "inventory_amt",
                         "age_weighted")

    result = []
    for r in rows:
        inb, clm, inv, age_w = (
            r["inbound_amt"], r["claimed_amt"], r["inventory_amt"], r["age_weighted"]
        )
        name = r["purchaser_name"]
        result.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "unclaimed_amount": round(inv, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else 0,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
            "record_count": int(r["record_count"] or 0),
        })

    return result


def get_project_summary(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
) -> Dict:
    """
    项目库存追溯汇总表（支持排序）。

    与 get_by_project 返回相同维度的数据，但支持按指定字段排序。

    Args:
        sort_by:    排序字段 — inventory_amount / claim_rate / avg_age_days，默认 inventory_amount
        sort_order: 排序方向 — asc / desc，默认 desc

    Returns:
        {total: 项目总数, rows: [{project_name, project_code, inbound_amount,
                                  claimed_amount, inventory_amount, claim_rate, avg_age_days}, ...]}
    """
    # 安全获取排序字段（白名单）
    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, "inventory_amount")
    order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.owner_project_code AS project_code,
                w.project_name,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
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
            project_code,
            MAX(project_name) AS project_name,
            SUM(batch_inbound * project_ratio)   AS inbound_amount,
            SUM(batch_claimed * project_ratio)   AS claimed_amount,
            SUM(batch_inventory * project_ratio) AS inventory_amount,
            SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted
        FROM wide_with_ratio
        GROUP BY project_code
        ORDER BY {sort_col} {order_dir}
    """
    rows = query(sql)
    rows = _rows_to_float(rows, "inbound_amount", "claimed_amount",
                         "inventory_amount", "age_weighted")

    result = []
    for r in rows:
        code = r["project_code"] or ""
        inb, clm, inv, age_w = (
            r["inbound_amount"], r["claimed_amount"],
            r["inventory_amount"], r["age_weighted"]
        )
        result.append({
            "project_name": r["project_name"] or "",
            "project_code": code,
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "inventory_amount": round(inv, 2),
            # 领用率：无入库时返回 None（区别于 0%）
            "claim_rate": round(clm / inb * 100, 2) if inb else None,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
        })

    return {"total": len(result), "rows": result}


def get_purchaser_summary(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
) -> Dict:
    """
    采购人（联系人）库存追溯汇总表（支持排序）。

    与 get_by_purchaser 返回相同维度的数据，但支持排序。

    Args:
        sort_by:    排序字段 — inventory_amount / claim_rate / avg_age_days
        sort_order: 排序方向 — asc / desc

    Returns:
        {total: 采购人总数, rows: [{purchaser_name, inbound_amount,
                                    claimed_amount, inventory_amount, claim_rate, avg_age_days}, ...]}
    """
    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, "inventory_amount")
    order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.project_contact AS contact_name,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
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
            contact_name,
            SUM(batch_inbound * project_ratio)   AS inbound_amount,
            SUM(batch_claimed * project_ratio)   AS claimed_amount,
            SUM(batch_inventory * project_ratio) AS inventory_amount,
            SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted
        FROM wide_with_ratio
        WHERE contact_name IS NOT NULL AND char_length(contact_name) > 0
        GROUP BY contact_name
        ORDER BY {sort_col} {order_dir}
    """
    rows = query(sql)
    rows = _rows_to_float(rows, "inbound_amount", "claimed_amount",
                         "inventory_amount", "age_weighted")

    result = []
    for r in rows:
        inb, clm, inv, age_w = (
            r["inbound_amount"], r["claimed_amount"],
            r["inventory_amount"], r["age_weighted"]
        )
        name = r["contact_name"] or "(未归属联系人)"
        result.append({
            "purchaser_name": name,
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "inventory_amount": round(inv, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else None,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
        })

    return {"total": len(result), "rows": result}
