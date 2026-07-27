"""
Additional BI indicator computation functions.
Extracted from compute_indicators.py — each function imports from utils as needed.
"""

from datetime import date as dt_date, timedelta
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set

from utils import query, _f, _get_inventory_rows, _rows_to_float, _PROJECT_RATIO_SQL


def query_one(sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    rows = query(sql, params)
    return rows[0] if rows else None


# ================================================================
# 时序统计接口
# ================================================================

def get_claim_monthly() -> Dict:
    """
    按月统计入库金额、领用金额、领用率（最近12个月）。
    供「领用率月度趋势」「入库vs领用对比」两个图表使用。
    """
    rows = _get_inventory_rows()

    monthly: OrderedDict[str, Dict[str, float]] = OrderedDict()
    for r in rows:
        d = r["putaway_date"] or r["inbound_date"]
        if d is None:
            continue
        if hasattr(d, 'strftime'):
            month = d.strftime("%Y-%m")
        else:
            month = str(d)[:7]
        if month not in monthly:
            monthly[month] = {"inbound": 0.0, "claimed": 0.0}
        monthly[month]["inbound"] += r["inbound_amount"]
        monthly[month]["claimed"] += r["claimed_amount"]

    all_months = list(monthly.keys())
    recent_months = all_months[-12:] if len(all_months) > 12 else all_months

    months = []
    data = []
    for month in recent_months:
        v = monthly[month]
        inbound = v["inbound"]
        claimed = v["claimed"]
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        months.append(month)
        data.append({
            "month": month,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })

    return {"months": months, "data": data}


def get_claim_yearly() -> Dict:
    """
    按年统计入库金额、领用金额、领用率（全部年份）。
    """
    rows = _get_inventory_rows()

    yearly: OrderedDict[str, Dict[str, float]] = OrderedDict()
    for r in rows:
        d = r["putaway_date"] or r["inbound_date"]
        if d is None:
            continue
        if hasattr(d, 'strftime'):
            year = d.strftime("%Y")
        else:
            year = str(d)[:4]
        if year not in yearly:
            yearly[year] = {"inbound": 0.0, "claimed": 0.0}
        yearly[year]["inbound"] += r["inbound_amount"]
        yearly[year]["claimed"] += r["claimed_amount"]

    years = []
    data = []
    for year in sorted(yearly.keys()):
        v = yearly[year]
        inbound = v["inbound"]
        claimed = v["claimed"]
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        years.append(year)
        data.append({
            "year": year,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })

    return {"years": years, "data": data}


def get_claim_daily() -> Dict:
    """
    按天统计上个月+当月入库金额、领用金额、领用率（两个月）。
    供「领用率当月趋势」图表使用。
    """
    rows = _get_inventory_rows()
    today = dt_date.today()
    # 上个月第一天
    first_day_current = today.replace(day=1)
    first_day_prev = (first_day_current - timedelta(days=1)).replace(day=1)

    # 按天聚合两个月数据
    day_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d is None or d < first_day_prev:
            continue
        key = d.strftime("%Y-%m-%d")
        if key not in day_map:
            day_map[key] = {"inbound": 0.0, "claimed": 0.0}
        day_map[key]["inbound"] += r["inbound_amount"]
        day_map[key]["claimed"] += r["claimed_amount"]

    days = []
    data = []
    d = first_day_prev
    while d <= today:
        key = d.strftime("%Y-%m-%d")
        label = d.strftime("%Y-%m-%d")
        if key in day_map:
            inbound = day_map[key]["inbound"]
            claimed = day_map[key]["claimed"]
        else:
            inbound = 0.0
            claimed = 0.0
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        days.append(label)
        data.append({
            "day": label,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })
        d += timedelta(days=1)

    return {"days": days, "data": data}


def get_claim_weekly() -> Dict:
    """
    按周统计入库金额、领用金额、领用率（最近12周）。
    供「领用率趋势」「入库vs领用对比」图表使用。
    """
    rows = _get_inventory_rows()
    today = dt_date.today()
    # 往前推 12 周
    cutoff = today - timedelta(weeks=12)

    # 按 ISO 周聚合
    week_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d is None or d < cutoff:
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        if week_key not in week_map:
            # 该周周一
            monday = d - timedelta(days=d.weekday())
            week_map[week_key] = {"inbound": 0.0, "claimed": 0.0, "monday": monday}
        week_map[week_key]["inbound"] += r["inbound_amount"]
        week_map[week_key]["claimed"] += r["claimed_amount"]

    weeks = []
    data = []
    for week_key in sorted(week_map.keys()):
        v = week_map[week_key]
        inbound = v["inbound"]
        claimed = v["claimed"]
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        monday = v["monday"]
        sunday = monday + timedelta(days=6)
        label = f"{monday.strftime('%Y-%m-%d')} ~ {sunday.strftime('%Y-%m-%d')}"
        weeks.append(label)
        data.append({
            "week": label,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })

    return {"weeks": weeks, "data": data}


# ================================================================
# 类别气泡图
# ================================================================

def get_category_bubble() -> Dict:
    """
    按物资类别（material_group_code）统计库存金额、领用率、SKU数。
    数据来源：v_project_inventory_wide，按物理批次去重后聚合。
    供「按物料类别 · 库存金额与领用率」气泡图使用。
    """
    rows = query("""
        WITH distinct_inventory AS (
            SELECT DISTINCT ON (tenant_id, material_code, batch_code, COALESCE(inventory_code, ''))
                material_group_code, material_code, batch_code,
                total_price,
                original_quantity * unit_price   AS inbound_amt,
                total_outbound_quantity * unit_price AS claimed_amt
            FROM v_project_inventory_wide
        )
        SELECT
            material_group_code AS category_code,
            SUM(total_price) AS inventory_amount,
            SUM(inbound_amt) AS inbound_amount,
            SUM(claimed_amt) AS claimed_amount,
            COUNT(DISTINCT material_code) AS sku_count,
            COUNT(DISTINCT batch_code) AS record_count
        FROM distinct_inventory
        WHERE material_group_code IS NOT NULL
        GROUP BY material_group_code
        ORDER BY inventory_amount DESC
    """)
    rows = _rows_to_float(rows, "inventory_amount", "inbound_amount", "claimed_amount")

    # ---- 取类别名称（维度表轻量查找） ----
    cat_name_map: Dict[str, str] = {}
    cat_codes = [r["category_code"] for r in rows if r["category_code"]]
    if cat_codes:
        placeholders = ','.join(['%s'] * len(cat_codes))
        # batch query in chunks to avoid too many params
        name_rows = query(f"""
            SELECT code, name FROM wms_material_group
            WHERE code IN ({placeholders}) AND del_flag = '0'
        """, tuple(cat_codes))
        cat_name_map = {r2["code"]: r2["name"] or r2["code"] for r2 in name_rows}

    top_n = 10
    top_rows = rows[:top_n]
    rest_amount = sum(r["inventory_amount"] for r in rows[top_n:])
    rest_inbound = sum(r["inbound_amount"] for r in rows[top_n:])
    rest_claimed = sum(r["claimed_amount"] for r in rows[top_n:])
    rest_sku = sum(int(r["sku_count"] or 0) for r in rows[top_n:])

    data = []
    for r in top_rows:
        amt = r["inventory_amount"]
        inb = r["inbound_amount"]
        clm = r["claimed_amount"]
        code = r["category_code"]
        data.append({
            "category_code": code,
            "category_name": cat_name_map.get(code, code or "未知"),
            "inventory_amount": round(amt, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else 0,
            "sku_count": int(r["sku_count"] or 0),
            "record_count": int(r["record_count"] or 0),
        })

    if rest_amount > 0:
        data.append({
            "category_code": "-",
            "category_name": "其他",
            "inventory_amount": round(rest_amount, 2),
            "claim_rate": round(rest_claimed / rest_inbound * 100, 2) if rest_inbound else 0,
            "sku_count": rest_sku,
            "record_count": 0,
        })

    return {"data": data}


# ================================================================
# 异常检测（按周）
# ================================================================

def get_anomaly_daily(days: int = 30) -> Dict:
    """
    异常检测（近12周），两个维度：
      1. 新项目：近 days 天内有新项目创建，标记对应周
      2. 周度环比：本周领用 vs 上周领用，波动超 ±30% 预警
    """
    rows = _get_inventory_rows()
    today = dt_date.today()
    AMPLITUDE = 0.30

    # Step 1 — 新建项目检测
    new_cutoff = today - timedelta(days=days)
    proj_rows = query("""
        SELECT owner_project_code, MIN(create_date)::date AS first_date
        FROM v_project_inventory_wide
        WHERE owner_project_code IS NOT NULL
        GROUP BY owner_project_code
    """)
    new_project_weeks: Set[str] = set()
    new_project_map: Dict[str, List[str]] = {}
    for r in proj_rows:
        fd = r["first_date"]
        if hasattr(fd, 'date'):
            fd = fd.date()
        if not fd or fd < new_cutoff:
            continue
        iso = fd.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        new_project_weeks.add(wk)
        new_project_map.setdefault(wk, []).append(r["owner_project_code"] or "(未命名)")

    # Step 2 — 按 ISO 周聚合（近 16 周，给环比留余量）
    cutoff = today - timedelta(weeks=16)
    week_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d is None or d < cutoff:
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        if week_key not in week_map:
            monday = d - timedelta(days=d.weekday())
            week_map[week_key] = {
                "inbound_amount": 0.0,
                "claimed_amount": 0.0,
                "monday": monday,
            }
        week_map[week_key]["inbound_amount"] += r["inbound_amount"]
        week_map[week_key]["claimed_amount"] += r["claimed_amount"]

    sorted_weeks = sorted(week_map.keys())

    # Step 3 — 逐周异常判定
    data = []
    for i, week_key in enumerate(sorted_weeks):
        v = week_map[week_key]
        monday = v["monday"]
        sunday = monday + timedelta(days=6)
        date_label = f"{monday.month}/{monday.day}-{sunday.month}/{sunday.day}"

        cl_val = v["claimed_amount"]
        in_val = v["inbound_amount"]
        anomaly_parts: List[str] = []
        huanbi = None

        # 新项目
        if week_key in new_project_weeks:
            proj_list = new_project_map.get(week_key, [])
            short = "、".join(proj_list[:2])
            if len(proj_list) > 2:
                short += f"等{len(proj_list)}个"
            anomaly_parts.append(f"新项目({short})")

        # 周度环比
        if i > 0:
            prev_cl = week_map[sorted_weeks[i - 1]]["claimed_amount"]
            if prev_cl > 0:
                huanbi = round((cl_val - prev_cl) / prev_cl * 100, 1)
                if abs(huanbi) > AMPLITUDE * 100:
                    arrow = "↑" if huanbi > 0 else "↓"
                    anomaly_parts.append(f"环比{arrow}{abs(huanbi)}%")

        data.append({
            "date": date_label,
            "inbound_amount": round(in_val / 10000, 2),
            "claimed_amount": round(cl_val / 10000, 2),
            "type": 1 if anomaly_parts else 0,
            "label": "、".join(anomaly_parts) if anomaly_parts else "正常",
            "huanbi": huanbi,
        })

    # 只返回近 12 周
    result = data[-12:] if len(data) > 12 else data
    result.reverse()
    return {"data": result}


# ================================================================
# 批次消化进度
# ================================================================

def get_batch_digest() -> Dict:
    """
    按 batch_code 取 TOP 6 批次，模拟逐月消化进度（基于当前剩余占比和库龄估算月均消耗率）。
    数据来源：v_project_inventory_wide，按物理批次去重。
    供「按入库批次 · 库存消化进度」图表使用。
    """
    rows = query("""
        WITH distinct_inventory AS (
            SELECT DISTINCT ON (tenant_id, material_code, batch_code, COALESCE(inventory_code, ''))
                batch_code, inbound_date, age_days,
                original_quantity * unit_price   AS inbound_amt,
                total_price                     AS remain_amt
            FROM v_project_inventory_wide
        )
        SELECT
            batch_code,
            MIN(inbound_date)::date AS first_inbound,
            SUM(inbound_amt) AS inbound_amt,
            SUM(remain_amt) AS remain_amt,
            ROUND(AVG(age_days)) AS avg_age_days
        FROM distinct_inventory
        WHERE batch_code IS NOT NULL
        GROUP BY batch_code
        ORDER BY inbound_amt DESC
        LIMIT 6
    """)
    rows = _rows_to_float(rows, "inbound_amt", "remain_amt", "avg_age_days")

    labels = ['入库月', '+1月', '+2月', '+3月', '+4月', '+5月', '+6月']
    colors = ['#3b82f6', '#f59e0b', '#f43f5e', '#10b981', '#8b5cf6', '#ec4899']
    series = []

    for idx, r in enumerate(rows):
        inbound = r["inbound_amt"] or 0
        remain = r["remain_amt"] or 0
        age_days = r["avg_age_days"] or 30

        if inbound > 0:
            total_remain_pct = remain / inbound * 100
        else:
            total_remain_pct = 100

        months = max(age_days / 30.0, 1)
        # 月均消耗率 = 已消耗百分比 / 库龄月数
        monthly_consume_rate = (100 - total_remain_pct) / months if months > 0 else 0

        data = [100]
        for m in range(1, 7):
            pct = max(0, round(100 - monthly_consume_rate * m, 1))
            data.append(pct)

        series.append({
            "batch_code": r["batch_code"],
            "inbound_wan": round(inbound / 10000, 2),
            "remain_pct": round(total_remain_pct, 1),
            "color": colors[idx % len(colors)],
            "data": data,
        })

    return {
        "labels": labels,
        "series": series,
    }


# ================================================================
# 采购批次库存报表
# ================================================================

ALLOWED_SORT_COLUMNS = {
    "claim_rate": "claim_rate",
    "age_days": "age_days",
    "avg_age_days": "avg_age_days",
    "inventory_amount": "inventory_amount",
    "inbound_amount": "inbound_amount",
    "inbound_date": "inbound_date",
}


def get_inventory_report(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
    limit: int = 500,
    offset: int = 0,
) -> Dict:
    """
    采购批次库存报表。
    支持按领用率、库龄、库存金额等字段排序。
    """
    # 安全校验排序字段，防止 SQL 注入
    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, "inventory_amount")
    order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

    # 明细总行数（分页用，保持项目级行数）
    total_row = query_one("SELECT COUNT(*) AS total FROM v_project_inventory_wide")
    total = int(total_row["total"]) if total_row else 0

    # 汇总金额（使用批次去重，与其他接口统一）
    summary_row = query_one("""
        WITH batch_dedup AS (
            SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
                original_quantity * unit_price       AS inbound_amt,
                total_outbound_quantity * unit_price AS claimed_amt,
                total_price                         AS inventory_amt
            FROM v_project_inventory_wide
        )
        SELECT
            COALESCE(SUM(inbound_amt), 0)   AS total_inbound,
            COALESCE(SUM(claimed_amt), 0)   AS total_claimed,
            COALESCE(SUM(inventory_amt), 0) AS total_inventory
        FROM batch_dedup
    """)

    # 查数据
    sql = f"""
        WITH wide_with_ratio AS (
            SELECT
                w.*,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
        )
        SELECT
            r.project_inventory_id                  AS id,
            r.batch_code                            AS purchase_batch,
            r.material_name,
            r.material_code,
            r.owner_project_code                    AS project_code,
            r.project_name,
            r.purchaser_name,
            r.project_submitter                     AS submitter_name,
            r.project_contact                       AS contact_name,
            r.plan_category                         AS project_type,
            r.inbound_date::date                    AS inbound_date,
            r.putaway_date::date                    AS putaway_date,
            r.batch_code,
            r.original_quantity,
            r.pi_current_quantity                   AS current_quantity,
            ROUND((r.total_outbound_quantity
                   * r.project_ratio)::numeric, 4)  AS used_quantity,
            ROUND((r.pick_quantity
                   * r.project_ratio)::numeric, 4)  AS pick_quantity,
            ROUND((r.repair_quantity
                   * r.project_ratio)::numeric, 4)  AS repair_quantity,
            ROUND((r.scrap_quantity
                   * r.project_ratio)::numeric, 4)  AS scrap_quantity,
            ROUND((r.repaired_quantity
                   * r.project_ratio)::numeric, 4)  AS repaired_quantity,
            r.unit_price,
            r.material_unit                         AS unit,
            r.supplier_code,
            ROUND((r.original_quantity * r.unit_price
                   * r.project_ratio)::numeric, 2)  AS inbound_amount,
            ROUND((r.total_outbound_quantity * r.unit_price
                   * r.project_ratio)::numeric, 2)  AS claimed_amount,
            ROUND((r.total_price
                   * r.project_ratio)::numeric, 2)  AS inventory_amount,
            CASE WHEN r.original_quantity > 0
                 THEN LEAST(ROUND(r.total_outbound_quantity::numeric
                          / r.original_quantity * 100, 2), 100.00)
                 ELSE 0
            END                                     AS claim_rate,
            CASE WHEN r.original_quantity > 0
                 THEN LEAST(ROUND(r.total_outbound_quantity::numeric
                          / r.original_quantity * 100, 2), 100.00)
                 ELSE 0
            END                                     AS claim_rate_on_inbound,
            r.age_days
        FROM wide_with_ratio r
        ORDER BY {sort_col} {order_dir} NULLS LAST
        LIMIT %s OFFSET %s
    """
    rows = query(sql, (limit, offset))
    rows = _rows_to_float(rows,
        "inbound_amount", "claimed_amount", "inventory_amount", "claim_rate",
        "original_quantity", "current_quantity", "used_quantity",
        "pick_quantity", "repair_quantity", "scrap_quantity", "repaired_quantity",
        "unit_price")

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "summary": {
            "total_inbound": round(_f(summary_row["total_inbound"]) if summary_row else 0, 2),
            "total_claimed": round(_f(summary_row["total_claimed"]) if summary_row else 0, 2),
            "total_inventory": round(_f(summary_row["total_inventory"]) if summary_row else 0, 2),
        },
        "rows": [
            {
                "id": r["id"],
                "purchase_batch": r["purchase_batch"] or "",
                "material_name": r["material_name"] or "",
                "material_code": r["material_code"] or "",
                "project_code": r["project_code"] or "",
                "project_name": r["project_name"] or "",
                "purchaser_name": r["purchaser_name"] or "",
                "project_type": r["project_type"] or "",
                "inbound_date": str(r["inbound_date"]) if r["inbound_date"] else "",
                "putaway_date": str(r["putaway_date"]) if r.get("putaway_date") else "",
                "batch_code": r["batch_code"] or "",
                "original_quantity": round(_f(r["original_quantity"]), 4),
                "current_quantity": round(_f(r["current_quantity"]), 4),
                "used_quantity": round(_f(r["used_quantity"]), 4),
                "pick_quantity": round(_f(r.get("pick_quantity", 0)), 4),
                "repair_quantity": round(_f(r.get("repair_quantity", 0)), 4),
                "scrap_quantity": round(_f(r.get("scrap_quantity", 0)), 4),
                "repaired_quantity": round(_f(r.get("repaired_quantity", 0)), 4),
                "unit_price": round(_f(r["unit_price"]), 4),
                "unit": r.get("unit") or "",
                "supplier_code": r.get("supplier_code") or "",
                "inbound_amount": round(_f(r["inbound_amount"]), 2),
                "claimed_amount": round(_f(r["claimed_amount"]), 2),
                "inventory_amount": round(_f(r["inventory_amount"]), 2),
                "claim_rate": round(_f(r["claim_rate"]), 2),
                "age_days": int(r["age_days"]) if r["age_days"] is not None else 0,
            }
            for r in rows
        ],
    }
