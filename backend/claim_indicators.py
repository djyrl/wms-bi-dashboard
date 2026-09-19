"""
采购库存 BI — 领用率指标模块
===========================
计算采购领用率指标，按「当年」和「全部」两个维度拆分。

数据来源：v_project_inventory_wide（唯一数据源）。
金额计算：基于 utils.py 中的 _BATCH_AMOUNTS_SQL 统一去重 CTE。

关键概念：
  「当年」：inbound_date 所在自然年 = 当前年。例如 2026 年入库的批次。
  「全部」：所有历史批次，不按年份筛选。

指标：
  领用率（金额）  = claimed / inbound × 100%
  领用率（数量）  = outbound_qty / original_qty × 100%
  未领用金额       = inbound - claimed（万元）
  未领用占比       = (inbound - claimed) / inbound × 100%

会计恒等式：
  ✅ inbound ≈ claimed + inventory
  未领用金额 ≈ 当前库存金额（在恒等式成立时）
"""

from datetime import date
from typing import Dict

from utils import query, _f, _rows_to_float


def _query_claim_aggregates(current_year: int) -> Dict[str, Dict[str, float]]:
    """
    一次 SQL 查询返回「全部」和「当年」两个维度的批次聚合指标。
    使用 utils._BATCH_AMOUNTS_SQL 相同的去重逻辑，确保口径一致。

    Args:
        current_year: 当前年份（如 2026），用于筛选「当年」数据

    Returns:
        {
            "all":  {total_inbound_amount, total_claimed_amount, total_inventory_amount,
                     original_quantity, total_outbound_quantity},
            "year": {同上，但只算 inbound_date 所在年 = current_year 的批次}
        }
    """
    sql = f"""
        WITH batch_amounts AS (
            -- 物理批次去重（与 utils._BATCH_AMOUNTS_SQL 口径一致）
            SELECT DISTINCT ON (tenant_id, material_code, batch_code)
                -- 三个核心金额
                original_quantity * unit_price       AS batch_inbound,
                total_outbound_quantity * unit_price AS batch_claimed,
                total_price                         AS batch_inventory,
                -- 数量字段
                original_quantity                   AS batch_orig_qty,
                total_outbound_quantity             AS batch_outbound_qty,
                -- 入库日期（用于年份筛选）
                inbound_date
            FROM v_project_inventory_wide
        )
        SELECT
            -- 「全部」汇总
            COALESCE(SUM(batch_inbound), 0)      AS inbound_all,
            COALESCE(SUM(batch_claimed), 0)      AS claimed_all,
            COALESCE(SUM(batch_inventory), 0)    AS inventory_all,
            COALESCE(SUM(batch_orig_qty), 0)     AS orig_qty_all,
            COALESCE(SUM(batch_outbound_qty), 0) AS outbound_qty_all,
            -- 「当年」汇总（按 inbound_date 年份筛选）
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_inbound ELSE 0 END), 0) AS inbound_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_claimed ELSE 0 END), 0) AS claimed_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_inventory ELSE 0 END), 0) AS inventory_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_orig_qty ELSE 0 END), 0) AS orig_qty_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_outbound_qty ELSE 0 END), 0) AS outbound_qty_year
        FROM batch_amounts
    """
    rows = query(sql)
    row = _rows_to_float(rows, *rows[0].keys())[0]

    # 拆分回两个维度
    return {
        "all": {
            "total_inbound_amount": row["inbound_all"],
            "total_claimed_amount": row["claimed_all"],
            "total_inventory_amount": row["inventory_all"],
            "original_quantity": row["orig_qty_all"],
            "total_outbound_quantity": row["outbound_qty_all"],
        },
        "year": {
            "total_inbound_amount": row["inbound_year"],
            "total_claimed_amount": row["claimed_year"],
            "total_inventory_amount": row["inventory_year"],
            "original_quantity": row["orig_qty_year"],
            "total_outbound_quantity": row["outbound_qty_year"],
        },
    }


def _build_claim_range(agg: Dict[str, float]) -> Dict:
    """
    基于聚合金额，计算领用率指标。

    从原始汇总金额计算出：
      - claim_rate_amount:     金额领用率（%）= claimed / inbound × 100
      - claim_rate_quantity:   数量领用率（%）= outbound_qty / original_qty × 100
      - unclaimed_amount:      未领用金额（万元）= (inbound - claimed) / 10000
                                ≈ 当前库存金额（恒等式成立时）
      - unclaimed_amount_ratio: 未领用占比（%）= (inbound - claimed) / inbound × 100
      - total_inbound_amount:  入库总额（万元）
      - total_claimed_amount:  领用总额（万元）
      - total_inbound_quantity:  入库总数量
      - total_claimed_quantity: 领用总数量

    Args:
        agg: _query_claim_aggregates 返回的 "all" 或 "year" 字典

    Returns:
        Dict: 领用率指标详情
    """
    # 提取原始金额
    total_inbound_amt = agg.get("total_inbound_amount", 0.0)    # 入库总额（元）
    total_claimed_amt = agg.get("total_claimed_amount", 0.0)    # 领用总额（元）
    total_inbound_qty = agg.get("original_quantity", 0.0)       # 入库总数量
    total_claimed_qty = agg.get("total_outbound_quantity", 0.0)  # 领用总数量

    # 未领用金额 = 入库 - 领用
    # 在恒等式 inbound ≈ claimed + inventory 下，≈ 当前库存金额
    unclaimed_amt = total_inbound_amt - total_claimed_amt

    return {
        # 领用率（金额 & 数量）
        "claim_rate_amount": round(total_claimed_amt / total_inbound_amt * 100, 2)
        if total_inbound_amt else 0.0,
        "claim_rate_quantity": round(total_claimed_qty / total_inbound_qty * 100, 2)
        if total_inbound_qty else 0.0,
        # 未领用
        "unclaimed_amount": round(unclaimed_amt / 10000, 2),
        "unclaimed_amount_ratio": round(unclaimed_amt / total_inbound_amt * 100, 2)
        if total_inbound_amt else 0.0,
        # 汇总金额（万元）
        "total_inbound_amount": round(total_inbound_amt / 10000, 2),
        "total_claimed_amount": round(total_claimed_amt / 10000, 2),
        # 汇总数量
        "total_inbound_quantity": round(total_inbound_qty, 2),
        "total_claimed_quantity": round(total_claimed_qty, 2),
    }


def get_claim_indicators() -> Dict:
    """
    获取采购领用率指标（主入口）。

    返回「全部」和「当年」两个维度的领用率分析。

    当年定义：inbound_date 所在自然年 = 当前年（如 2026）。

    Returns:
        {
            "current_year": 2026,
            "year_start": "2026-01-01",
            "year_end": "2026-12-31",
            "all":  {...},   # 全部批次的领用率指标
            "year": {...},   # 当年入库批次的领用率指标
        }
    """
    current_year = date.today().year
    # 一次查询获取全部和当年两个维度的聚合数据
    aggs = _query_claim_aggregates(current_year)

    return {
        "current_year": current_year,
        "year_start": f"{current_year}-01-01",
        "year_end": f"{current_year}-12-31",
        # 全部批次
        "all": _build_claim_range(aggs["all"]),
        # 当年入库批次
        "year": _build_claim_range(aggs["year"]),
    }
