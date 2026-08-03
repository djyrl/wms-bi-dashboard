"""
采购库存 BI — ERP+WMS 联合库存模块
==================================
将 erp_catalog_mb51（ERP 全部历史凭证）与 v_project_inventory_wide（WMS 当前库存）
在批次级联合，补齐 WMS 2026 年 6 月之前的数据缺口。

数据来源：
  erp_catalog_mb51         — ERP 物料凭证，plant=2635，2021-05 至今
  v_project_inventory_wide  — WMS 物理库存，2026-06 至今

核心视图（SQL 定义在 sql/04_erp_inventory_views.sql）：
  v_batch_lifecycle             — 批次生命周期（一行一个批次）
  v_monthly_inventory_timeline  — 月度库存时序（一行一个月份）
  v_material_monthly_inventory  — 物料月度库存（一行一个物料×月份）

关键公式：
  ERP 累计余额 = Σ(所有移动类型的 DMBTR) = 该批次的账面库存
  WMS 当前库存 = total_price (已去重)
  差异 < 0.3%，两者高度一致
"""

from datetime import date
from typing import Dict, List, Optional

from utils import query, _f, _rows_to_float


# ================================================================
#  批次生命周期
# ================================================================

def get_batch_lifecycle(
    status: Optional[str] = None,
    material_code: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> Dict:
    """
    获取批次生命周期列表。

    每个物料+批次一行，包含 ERP 账面数据、WMS 实物数据、状态分类。

    Args:
        status:        可选，按状态筛选：'在库' / 'ERP有余额_WMS无' / '已消耗完' / '负余额_异常'
        material_code: 可选，按物料编码筛选
        limit:         返回条数，默认 500
        offset:        偏移量，默认 0

    Returns:
        {
            "total": 总批次数,
            "limit": limit,
            "offset": offset,
            "rows": [{批次生命周期详情}, ...],
            "summary": {  # 汇总
                "total_batches": ..., "in_stock_batches": ...,
                "total_best_inventory_amt": ...,  # 万元
                "total_wms_inventory_amt": ...,   # 万元
                "total_erp_balance_amt": ...,     # 万元
            }
        }
    """
    where_clauses = ["1=1"]
    if status:
        where_clauses.append(f"batch_status = '{status}'")
    if material_code:
        where_clauses.append(f"material_code = '{material_code}'")
    where_sql = " AND ".join(where_clauses)

    # ── 总数 ──
    count_rows = query(f"""
        SELECT COUNT(*) AS cnt
        FROM v_batch_lifecycle
        WHERE {where_sql}
    """)
    total = count_rows[0]["cnt"] if count_rows else 0

    # ── 明细 ──
    rows = query(f"""
        SELECT
            material_code, batch_code,
            erp_inbound_amt, erp_outbound_amt, erp_balance_amt, erp_balance_qty,
            first_inbound_date, last_move_date, move_cnt, move_type_cnt,
            wms_inventory_amt, wms_current_qty, wms_orig_qty, wms_outbound_qty,
            wms_unit_price, wms_age_days, wms_inbound_date,
            material_name, material_group_code,
            best_inventory_amt, best_inventory_qty,
            batch_status, erp_wms_gap_amt
        FROM v_batch_lifecycle
        WHERE {where_sql}
        ORDER BY best_inventory_amt DESC NULLS LAST
        LIMIT {limit} OFFSET {offset}
    """)
    rows = _rows_to_float(rows,
        "erp_inbound_amt", "erp_outbound_amt", "erp_balance_amt", "erp_balance_qty",
        "wms_inventory_amt", "wms_current_qty", "wms_orig_qty", "wms_outbound_qty",
        "wms_unit_price", "wms_age_days",
        "best_inventory_amt", "best_inventory_qty", "erp_wms_gap_amt")

    # ── 汇总 ──
    summary_rows = query(f"""
        SELECT
            COUNT(*) AS total_batches,
            COUNT(*) FILTER (WHERE batch_status = '在库') AS in_stock_batches,
            COUNT(*) FILTER (WHERE batch_status = 'ERP有余额_WMS无') AS erp_only_batches,
            COUNT(*) FILTER (WHERE batch_status = '已消耗完') AS consumed_batches,
            SUM(best_inventory_amt) AS total_best_inventory_amt,
            SUM(wms_inventory_amt) AS total_wms_inventory_amt,
            SUM(erp_balance_amt) AS total_erp_balance_amt
        FROM v_batch_lifecycle
        WHERE {where_sql}
    """)
    s = _rows_to_float(summary_rows,
        "total_best_inventory_amt", "total_wms_inventory_amt", "total_erp_balance_amt")[0] if summary_rows else {}

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "rows": rows,
        "summary": {
            "total_batches": s.get("total_batches", 0),
            "in_stock_batches": s.get("in_stock_batches", 0),
            "erp_only_batches": s.get("erp_only_batches", 0),
            "consumed_batches": s.get("consumed_batches", 0),
            "total_best_inventory_amt": round(s.get("total_best_inventory_amt", 0) / 10000, 2),
            "total_wms_inventory_amt": round(s.get("total_wms_inventory_amt", 0) / 10000, 2),
            "total_erp_balance_amt": round(s.get("total_erp_balance_amt", 0) / 10000, 2),
        },
    }


# ================================================================
#  月度库存时序
# ================================================================

def get_monthly_inventory(
    year: Optional[int] = None,
    material_code: Optional[str] = None,
) -> Dict:
    """
    获取月度库存时序。

    从 2021 年 5 月至今，每月末的库存总额（ERP 累计余额聚合）。
    对于 2026 年 6 月之后的月份，可与 WMS 快照交叉验证。

    Args:
        year:          可选，筛选特定年份。不传则返回全部历史。
        material_code: 可选，筛选特定物料。不传则汇总全部物料。

    Returns:
        {
            "rows": [
                {
                    "doc_month": "2025-12-01",
                    "active_batches": 1234,
                    "total_inventory_amt": 3820.50,   # 万元
                    "total_inventory_qty": 290000,
                    "month_inbound": 150.00,           # 万元
                    "month_outbound": 80.00,           # 万元
                }, ...
            ]
        }
    """
    if material_code:
        # 按物料查询，使用 v_material_monthly_inventory
        where = f"material_code = '{material_code}'"
        if year:
            where += f" AND EXTRACT(YEAR FROM doc_month) = {year}"
        sql = f"""
            SELECT
                doc_month,
                cumulative_balance,
                active_batches
            FROM v_material_monthly_inventory
            WHERE {where}
            ORDER BY doc_month
        """
        rows = query(sql)
        rows = _rows_to_float(rows, "cumulative_balance")
        return {
            "material_code": material_code,
            "rows": [
                {
                    "doc_month": str(r["doc_month"])[:10],
                    "inventory_amt": round(r["cumulative_balance"] / 10000, 2),
                    "active_batches": r["active_batches"],
                }
                for r in rows
            ],
        }
    else:
        # 全部物料，使用 v_monthly_inventory_timeline
        where = "1=1"
        if year:
            where = f"EXTRACT(YEAR FROM doc_month) = {year}"
        sql = f"""
            SELECT
                doc_month,
                active_batches,
                total_inventory_amt,
                total_inventory_qty,
                month_inbound,
                month_outbound,
                net_amt_change,
                move_cnt
            FROM v_monthly_inventory_timeline
            WHERE {where}
            ORDER BY doc_month
        """
        rows = query(sql)
        rows = _rows_to_float(rows,
            "total_inventory_amt", "total_inventory_qty",
            "month_inbound", "month_outbound", "net_amt_change")
        return {
            "rows": [
                {
                    "doc_month": str(r["doc_month"])[:10],
                    "active_batches": r["active_batches"],
                    "total_inventory_amt": round(r["total_inventory_amt"] / 10000, 2),
                    "total_inventory_qty": round(r["total_inventory_qty"], 2),
                    "month_inbound": round(r["month_inbound"] / 10000, 2),
                    "month_outbound": round(r["month_outbound"] / 10000, 2),
                }
                for r in rows
            ],
        }


# ================================================================
#  ERP vs WMS 交叉验证
# ================================================================

def get_erp_wms_reconciliation() -> Dict:
    """
    ERP 账面 vs WMS 实物的交叉验证汇总。

    回答：ERP 和 WMS 在批次级别的匹配度如何？

    Returns:
        {
            "total_batches_erp": 15680,       # ERP 中的总批次数
            "total_batches_wms": 414,         # WMS 中的总批次数
            "matched_batches": 1734,          # 两者匹配的物料+批次组合数
            "matched_erp_balance": 3633.24,   # 匹配批次的 ERP 账面余额(万元)
            "matched_wms_inventory": 3641.66, # 匹配批次的 WMS 实物库存(万元)
            "gap_amount": 8.41,               # 差异金额(万元)
            "gap_pct": 0.23,                  # 差异率(%)
            "erp_only_positive_batches": 444, # 仅ERP有正余额的批次数
            "consumed_batches": 11366,        # 已消耗完的批次数
        }
    """
    rows = query("""
        SELECT
            COUNT(*) AS total_batches,
            COUNT(*) FILTER (WHERE wms_inventory_amt > 0) AS in_stock,
            COUNT(*) FILTER (WHERE batch_status = 'ERP有余额_WMS无') AS erp_only,
            COUNT(*) FILTER (WHERE batch_status = '已消耗完') AS consumed,
            SUM(erp_balance_amt) AS erp_total,
            SUM(wms_inventory_amt) AS wms_total,
            SUM(best_inventory_amt) AS best_total,
            SUM(CASE WHEN wms_inventory_amt > 0 AND erp_balance_amt > 0
                THEN wms_inventory_amt - erp_balance_amt ELSE 0 END) AS total_gap
        FROM v_batch_lifecycle
    """)
    if not rows:
        return {}

    r = _rows_to_float(rows, "erp_total", "wms_total", "best_total", "total_gap")[0]
    matched_wms = r["wms_total"]
    matched_erp = r["erp_total"]  # 这里 erp_total 是所有批次的，不只是匹配的

    # 精确算匹配批次的差异
    match_rows = query("""
        SELECT
            SUM(erp_balance_amt) AS matched_erp,
            SUM(wms_inventory_amt) AS matched_wms
        FROM v_batch_lifecycle
        WHERE wms_inventory_amt > 0 AND erp_balance_amt > 0
    """)
    if match_rows:
        mr = _rows_to_float(match_rows, "matched_erp", "matched_wms")[0]
        matched_erp = mr["matched_erp"]
        matched_wms = mr["matched_wms"]

    gap = matched_wms - matched_erp
    gap_pct = round(gap / matched_wms * 100, 2) if matched_wms else 0

    return {
        "total_batches_erp": r.get("total_batches", 0),
        "in_stock_batches": r.get("in_stock", 0),
        "matched_erp_balance": round(matched_erp / 10000, 2),
        "matched_wms_inventory": round(matched_wms / 10000, 2),
        "gap_amount": round(gap / 10000, 2),
        "gap_pct": gap_pct,
        "erp_only_positive_batches": r.get("erp_only", 0),
        "consumed_batches": r.get("consumed", 0),
        "total_best_inventory_amt": round(r.get("best_total", 0) / 10000, 2),
    }


# ================================================================
#  单个物料库存走势
# ================================================================

def get_material_timeline(material_code: str) -> Dict:
    """
    获取单个物料的库存走势（逐月）。

    Args:
        material_code: 物料编码

    Returns:
        {
            "material_code": "10039617",
            "material_name": "镀锌等边角钢...",
            "current_wms_inventory": 12.50,   # 万元，当前WMS库存
            "erp_cumulative_balance": 12.30,   # 万元，ERP累计余额
            "monthly": [{doc_month, inventory_amt, active_batches}, ...]
        }
    """
    # ── 月度走势 ──
    monthly = query(f"""
        SELECT doc_month, cumulative_balance, active_batches
        FROM v_material_monthly_inventory
        WHERE material_code = '{material_code}'
        ORDER BY doc_month
    """)
    monthly = _rows_to_float(monthly, "cumulative_balance")

    # ── 当前库存 & 物料名 ──
    wms_now = query(f"""
        SELECT
            MAX(w.material_name) AS material_name,
            COALESCE(SUM(w.wms_inventory_amt), 0) AS wms_inv,
            COALESCE(SUM(w.best_inventory_amt), 0) AS best_inv
        FROM v_batch_lifecycle w
        WHERE w.material_code = '{material_code}'
    """)
    wms_now = _rows_to_float(wms_now, "wms_inv", "best_inv")[0] if wms_now else {}

    # WMS 没有物料名时从 ERP 取
    material_name = wms_now.get("material_name") or ""
    if not material_name:
        erp_name = query(f"""
            SELECT row_json->>'MAKTX' AS maktx
            FROM public.erp_catalog_mb51
            WHERE werks = '2635'
              AND row_json->>'MATNR' = '{material_code}'
              AND row_json->>'MAKTX' IS NOT NULL
            LIMIT 1
        """)
        if erp_name:
            material_name = erp_name[0]["maktx"] or ""

    return {
        "material_code": material_code,
        "material_name": material_name,
        "current_wms_inventory": round(wms_now.get("wms_inv", 0) / 10000, 2),
        "erp_cumulative_balance": round(wms_now.get("best_inv", 0) / 10000, 2),
        "monthly": [
            {
                "doc_month": str(r["doc_month"])[:10],
                "inventory_amt": round(r["cumulative_balance"] / 10000, 2),
                "active_batches": r["active_batches"],
            }
            for r in monthly
        ],
    }


# ================================================================
#  库存概览（当前快照）
# ================================================================

def get_inventory_overview() -> Dict:
    """
    库存概览（当前快照）。

    返回：
      - 按状态分组的批次数量和金额
      - 库存总额（最佳估计）

    Returns:
        {
            "total_batches": 15680,
            "total_inventory_amt": 3820.50,       # 万元
            "in_stock": { "batches": 1734, "amt": 3641.66 },
            "erp_only_positive": { "batches": 444, "amt": 89.00 },
            "consumed": { "batches": 11366, "amt": 0 },
            "abnormal": { "batches": 2136, "amt": -10.00 },
        }
    """
    rows = query("""
        SELECT
            batch_status,
            COUNT(*) AS cnt,
            SUM(best_inventory_amt) AS total_amt
        FROM v_batch_lifecycle
        GROUP BY batch_status
        ORDER BY total_amt DESC
    """)
    rows = _rows_to_float(rows, "total_amt")

    result = {"total_batches": 0, "total_inventory_amt": 0}
    total_batches = 0
    total_amt = 0
    for r in rows:
        status_key = r["batch_status"]
        amt_wan = round(r["total_amt"] / 10000, 2)
        result[status_key] = {"batches": r["cnt"], "amt_wan": amt_wan}
        total_batches += r["cnt"]
        total_amt += r["total_amt"]

    result["total_batches"] = total_batches
    result["total_inventory_amt"] = round(total_amt / 10000, 2)
    return result


# ================================================================
#  ERP 领用率指标
# ================================================================
#  从 erp_catalog_mb51 计算领用率，与 WMS 版 (claim_indicators.py) 并列。
#
#  ERP 版 vs WMS 版的关键区别：
#    ERP: 统计所有历史凭证，包括已消耗完的批次 → 领用率更高、更真实
#    WMS: 只统计当前有库存的批次 → 领用率偏低（大量已消耗的没算）
#
#  移动类型映射：
#    入库 = 101 + 102（102已是负数）
#    出库 = 201(成本中心) + 221(项目) + 222 + Z61(项目) + Z62
#    领用率 = 出库 / 入库 × 100%
# ================================================================

def _query_erp_claim_aggregates(current_year: int) -> dict:
    """
    一次查询返回「全部历史」和「当年」两个维度的出入库汇总。

    Args:
        current_year: 当前年份（如 2026）

    Returns:
        {"all": {inbound, outbound, ...}, "year": {inbound, outbound, ...}}
    """
    sql = f"""
        SELECT
            -- 全部历史
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0)     AS inbound_all,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0)    AS outbound_all,
            -- 当年
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0)     AS inbound_year,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0)    AS outbound_year,
            -- 数量
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                THEN (row_json->>'MENGE')::numeric ELSE 0 END), 0)     AS inbound_qty_all,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
                THEN -(row_json->>'MENGE')::numeric ELSE 0 END), 0)    AS outbound_qty_all,
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN (row_json->>'MENGE')::numeric ELSE 0 END), 0)     AS inbound_qty_year,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN -(row_json->>'MENGE')::numeric ELSE 0 END), 0)    AS outbound_qty_year
        FROM public.erp_catalog_mb51
        WHERE werks = '2635'
          AND row_json->>'MATNR' IS NOT NULL
          AND charg IS NOT NULL
    """
    rows = query(sql)
    return _rows_to_float(rows, *rows[0].keys())[0] if rows else {}


def _build_erp_claim_metrics(inbound: float, outbound: float,
                              inbound_qty: float, outbound_qty: float) -> dict:
    """基于出入库金额计算领用率指标。"""
    unclaimed = inbound - outbound
    return {
        "total_inbound_amount": round(inbound / 10000, 2),
        "total_outbound_amount": round(outbound / 10000, 2),
        "total_inbound_quantity": round(inbound_qty, 2),
        "total_outbound_quantity": round(outbound_qty, 2),
        "claim_rate_amount": round(outbound / inbound * 100, 2) if inbound > 0 else 0.0,
        "claim_rate_quantity": round(outbound_qty / inbound_qty * 100, 2) if inbound_qty > 0 else 0.0,
        "unclaimed_amount": round(unclaimed / 10000, 2),
        "unclaimed_amount_ratio": round(unclaimed / inbound * 100, 2) if inbound > 0 else 0.0,
    }


def get_erp_claim_indicators() -> Dict:
    """
    ERP 版领用率指标（主入口）。

    返回「全部历史」和「当年」两个维度的领用率分析。

    Returns:
        {
            "current_year": 2026,
            "year_start": "2026-01-01", "year_end": "2026-12-31",
            "all":  {...},   # 全部历史的领用率
            "year": {...},   # 当年的领用率
            "note": "数据来源: erp_catalog_mb51, 移动类型 101+102入库 / 201+221+Z61+...出库"
        }
    """
    current_year = date.today().year
    agg = _query_erp_claim_aggregates(current_year)

    return {
        "current_year": current_year,
        "year_start": f"{current_year}-01-01",
        "year_end": f"{current_year}-12-31",
        "all": _build_erp_claim_metrics(
            agg.get("inbound_all", 0), agg.get("outbound_all", 0),
            agg.get("inbound_qty_all", 0), agg.get("outbound_qty_all", 0),
        ),
        "year": _build_erp_claim_metrics(
            agg.get("inbound_year", 0), agg.get("outbound_year", 0),
            agg.get("inbound_qty_year", 0), agg.get("outbound_qty_year", 0),
        ),
        "note": "ERP数据(erp_catalog_mb51)，移动类型101+102=入库, 201+221+222+Z61+Z62=出库",
    }


def get_erp_claim_monthly(year: Optional[int] = None) -> Dict:
    """
    ERP 版月度领用率趋势。

    按月统计入库金额、出库金额、领用率。

    Args:
        year: 可选，筛选年份。不传则全部历史。

    Returns:
        {"rows": [{doc_month, inbound, outbound, claim_rate}, ...]}
    """
    year_filter = f"AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{year}'" if year else ""
    sql = f"""
        SELECT
            SUBSTRING(row_json->>'BLDAT', 1, 7) AS doc_month,
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0)     AS inbound,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','222','Z61','Z62')
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0)    AS outbound,
            COUNT(*) AS move_cnt
        FROM public.erp_catalog_mb51
        WHERE werks = '2635'
          AND row_json->>'MATNR' IS NOT NULL
          AND charg IS NOT NULL
          {year_filter}
        GROUP BY 1
        ORDER BY 1
    """
    rows = query(sql)
    rows = _rows_to_float(rows, "inbound", "outbound")

    return {
        "rows": [
            {
                "doc_month": r["doc_month"],
                "inbound": round(r["inbound"] / 10000, 2),
                "outbound": round(r["outbound"] / 10000, 2),
                "claim_rate": round(r["outbound"] / r["inbound"] * 100, 2) if r["inbound"] > 0 else 0.0,
                "move_cnt": r["move_cnt"],
            }
            for r in rows
        ],
    }
