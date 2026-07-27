"""
库存时间指标计算模块
"""

from datetime import date as dt_date, timedelta
from typing import Any, Dict, List

from utils import query, _get_inventory_rows, _rows_to_float, _get_batch_rows


def _get_batch_age_rows() -> List[Dict]:
    """按物理批次去重，返回每条批次的库存金额和库龄（使用统一的 batch_amounts CTE）。"""
    return _get_batch_rows()


def get_time_indicators(age_ranges: List[tuple] = None) -> Dict:
    """
    9. 长库龄库存金额占比（≥1年）
    10. 库龄结构占比
    11. 平均库龄（金额加权）
    """
    if age_ranges is None:
        age_ranges = [
            (0, 365, "≤1年"),
            (365, 1095, "1~3年"),
            (1095, 1825, "3~5年"),
            (1825, 99999, "≥5年"),
        ]

    # 批次级数据（物理去重，与其他接口统一口径）
    rows = _get_batch_age_rows()
    total_inventory = sum(r["inventory_amount"] for r in rows)

    # 加权平均库龄
    weighted_age_sum = sum(r["inventory_amount"] * r["age_days"] for r in rows)
    avg_age = weighted_age_sum / total_inventory if total_inventory else 0

    # 长库龄占比
    aged_amount = sum(r["inventory_amount"] for r in rows if r["age_days"] >= 365)

    # 库龄结构
    structure = []
    for min_age, max_age, label in age_ranges:
        amt = sum(r["inventory_amount"] for r in rows if min_age <= r["age_days"] < max_age)
        cnt = sum(1 for r in rows if min_age <= r["age_days"] < max_age)
        structure.append({
            "range": label,
            "amount": round(amt, 2),
            "ratio": round(amt / total_inventory, 4) if total_inventory else 0,
            "count": cnt,
        })

    return {
        "aged_ratio_1y": round(aged_amount / total_inventory, 4) if total_inventory else 0,
        "aged_amount_1y": round(aged_amount, 2),
        "age_structure": structure,
        "avg_age_weighted_days": round(avg_age, 2),
    }


def get_age_layers(min_amount: float = 0, min_age: int = 0, max_age: int = None) -> List[Dict]:
    """
    12. 库龄分层统计 — 筛选库存金额>min_amount 且 库龄>min_age 的明细
    """
    rows = _get_inventory_rows()
    result = []
    for r in rows:
        age = r["age_days"]
        amt = r["inventory_amount"]
        if amt >= min_amount and age >= min_age:
            if max_age is None or age <= max_age:
                result.append({
                    "id": r["id"],
                    "material_code": r["material_code"],
                    "material_name": r.get("material_name", ""),
                    "batch_code": r["batch_code"],
                    "inventory_amount": round(amt, 2),
                    "current_quantity": r["current_quantity"],
                    "age_days": int(age),
                    "inbound_date": str(r["inbound_date"]),
                    "unit_price": r["unit_price"],
                    "supplier_code": r["supplier_code"],
                    "project_code": r.get("project_code", ""),
                    "project_name": r.get("project_name", ""),
                })

    result.sort(key=lambda x: x["inventory_amount"], reverse=True)
    return result


def get_age_monthly() -> Dict:
    """
    按月计算加权平均库龄和超90天占比（最近12个月）。

    对每个历史月份的月末，计算「当前仍持有库存」的：
      - 加权平均库龄（按入库金额加权）
      - 库龄 ≥ 90 天的金额占比

    供「平均库龄月度趋势」图表使用。
    """
    today = dt_date.today()

    # ---- 生成最近12个月的月末日期（从最早到最晚） ----
    month_ends: List[dt_date] = []
    for i in range(11, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        first_day = dt_date(y, m, 1)
        if m == 12:
            last_day = dt_date(y, 12, 31)
        else:
            last_day = dt_date(y, m + 1, 1) - timedelta(days=1)
        month_ends.append(last_day)

    # ---- 获取当前库存数据 ----
    rows = _get_inventory_rows()

    months: List[str] = []
    data: List[Dict] = []

    for month_end in month_ends:
        total_weight = 0.0
        age_weighted_sum = 0.0
        over90_weight = 0.0

        for r in rows:
            d = r["inbound_date"]
            if hasattr(d, 'date'):
                d = d.date()
            elif isinstance(d, str):
                d = dt_date.fromisoformat(d)

            if d is None or d > month_end:
                continue  # 该月末还未入库，不计入

            age = (month_end - d).days
            # 使用入库金额(inbound_amount)作为权重，反映入库时的完整价值
            weight = r["inbound_amount"]
            total_weight += weight
            age_weighted_sum += weight * age
            if age >= 90:
                over90_weight += weight

        avg_age = round(age_weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
        over90_rate = round(over90_weight / total_weight * 100, 1) if total_weight > 0 else 0.0

        label = f"{month_end.year}年{month_end.month}月"
        months.append(label)
        data.append({
            "month": label,
            "avg_age": avg_age,
            "over90_rate": over90_rate,
        })

    return {"months": months, "data": data}


def get_age_heatmap() -> Dict:
    """
    按物料类别 × 库龄段 交叉统计库存金额。

    数据来源：v_project_inventory_wide，按物理批次去重。
    取库存金额 TOP 10 类别，按 6 个库龄段汇总金额。

    供「滞留库存热力图」图表使用。
    """
    rows = query("""
        SELECT
            w.material_group_code AS category_code,
            w.age_days,
            w.inventory_amount
        FROM (
            SELECT DISTINCT ON (tenant_id, material_code, batch_code, COALESCE(inventory_code, ''))
                material_group_code, age_days, total_price AS inventory_amount
            FROM v_project_inventory_wide
        ) w
    """)
    rows = _rows_to_float(rows, "inventory_amount", "age_days")

    # 库龄段定义（从短到长，前端展示时反转）
    AGE_RANGES = [
        (0, 30, '0-30天'),
        (30, 60, '30-60天'),
        (60, 90, '60-90天'),
        (90, 180, '90-180天'),
        (180, 365, '180-365天'),
        (365, 99999, '>365天'),
    ]

    # ---- 按类别聚合 ----
    # 取类别名称（维度表轻量查找）
    cat_name_map: Dict[str, str] = {}
    cat_codes = list({r["category_code"] for r in rows if r["category_code"]})
    if cat_codes:
        placeholders = ','.join(['%s'] * len(cat_codes))
        name_rows = query(f"""
            SELECT code, name FROM wms_material_group
            WHERE code IN ({placeholders}) AND del_flag = '0'
        """, tuple(cat_codes))
        cat_name_map = {r["code"]: r["name"] or r["code"] for r in name_rows}

    cat_data: Dict[str, Dict] = {}
    for r in rows:
        code = r["category_code"] or "未知"
        name = cat_name_map.get(code, code)
        age = int(r["age_days"])
        amt = r["inventory_amount"]

        if code not in cat_data:
            cat_data[code] = {
                "name": name,
                "total": 0.0,
                "ages": {label: 0.0 for _, _, label in AGE_RANGES},
            }

        cat_data[code]["total"] += amt
        for min_age, max_age, label in AGE_RANGES:
            if min_age <= age < max_age:
                cat_data[code]["ages"][label] += amt
                break

    # ---- 取 TOP 10 类别 ----
    top_cats = sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True)[:10]

    # ---- 构建矩阵（行 = 库龄段从老到新，列 = 类别） ----
    age_labels = [label for _, _, label in reversed(AGE_RANGES)]  # ['>365天', '180-365', ...]
    matrix: List[List[float]] = []
    for _, _, label in reversed(AGE_RANGES):
        row = []
        for _, cat in top_cats:
            # 转换为万元
            row.append(round(cat["ages"][label] / 10000, 2))
        matrix.append(row)

    categories = [cat["name"] for _, cat in top_cats]

    return {
        "categories": categories,
        "age_labels": age_labels,
        "data": matrix,
    }
