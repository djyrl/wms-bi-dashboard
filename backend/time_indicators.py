"""
采购库存 BI — 库龄时间指标模块
===============================
计算库存库龄相关指标：
  - 长库龄库存金额占比（≥1年）
  - 库龄结构占比（≤1年 / 1~3年 / 3~5年 / ≥5年）
  - 金额加权平均库龄
  - 库龄分层明细（按金额和库龄筛选物料）
  - 平均库龄月度趋势
  - 滞留库存热力图（物料类别 × 库龄段）

数据来源：v_project_inventory_wide → _get_batch_rows()（批次去重）。
库龄计算基于视图中的 age_days 字段（CURRENT_DATE - COALESCE(inbound_date, create_date)）。

金额加权平均库龄：
  含义：以库存金额为权重计算的平均存放时间。
  公式：Σ(inventory_amount × age_days) / Σ(inventory_amount)
  解读：值越大，说明库存在仓库中沉淀越久。
"""

from datetime import date as dt_date, timedelta
from typing import Any, Dict, List

from utils import query, _rows_to_float, _BATCH_AMOUNTS_SQL, _get_batch_rows, _get_inventory_rows


# ================================================================
#  核心库龄指标
# ================================================================

def get_time_indicators(age_ranges: List[tuple] = None) -> Dict:
    """
    获取库龄时间核心指标。

    基于批次去重数据计算：
      - 加权平均库龄（按库存金额加权）
      - 长库龄占比（库龄 ≥ 365 天）
      - 库龄结构（各库龄段的金额、占比、批次数量）

    Args:
        age_ranges: 库龄分段定义，默认：
                    [(0, 365, "≤1年"), (365, 1095, "1~3年"),
                     (1095, 1825, "3~5年"), (1825, 99999, "≥5年")]
                    每项为 (min_days, max_days, label)

    Returns:
        {
            "aged_ratio_1y":          长库龄占比（比例，如 0.15 表示 15%）
            "aged_amount_1y":         长库龄金额（元）
            "age_structure":          [{range, amount, ratio, count}, ...]
            "avg_age_weighted_days":  加权平均库龄（天）
        }
    """
    if age_ranges is None:
        age_ranges = [
            (0, 365, "≤1年"),
            (365, 1095, "1~3年"),
            (1095, 1825, "3~5年"),
            (1825, 99999, "≥5年"),
        ]

    # ── Step 1: 获取批次级明细 ──
    rows = _get_batch_rows()
    total_inventory = sum(r["inventory_amount"] for r in rows)

    # ── Step 2: 金额加权平均库龄 ──
    # 公式：Σ(库存金额 × 库龄) / Σ(库存金额)
    weighted_age_sum = sum(r["inventory_amount"] * r["age_days"] for r in rows)
    avg_age = weighted_age_sum / total_inventory if total_inventory else 0

    # ── Step 3: 长库龄占比（≥1年）──
    # 库龄 ≥ 365 天的库存金额 / 总库存金额
    aged_amount = sum(r["inventory_amount"] for r in rows if r["age_days"] >= 365)
    aged_ratio = aged_amount / total_inventory if total_inventory else 0

    # ── Step 4: 库龄结构 ──
    # 将库存按 age_days 分入各库龄段，统计每段的金额、占比、批次数
    structure = []
    for min_age, max_age, label in age_ranges:
        # 筛选该库龄段的批次
        amt = sum(r["inventory_amount"] for r in rows
                  if min_age <= r["age_days"] < max_age)
        cnt = sum(1 for r in rows if min_age <= r["age_days"] < max_age)
        structure.append({
            "range": label,
            "amount": round(amt, 2),
            # 占比 = 该段金额 / 总库存金额
            "ratio": round(amt / total_inventory, 4) if total_inventory else 0,
            "count": cnt,
        })

    return {
        "aged_ratio_1y": round(aged_ratio, 4),
        "aged_amount_1y": round(aged_amount, 2),
        "age_structure": structure,
        "avg_age_weighted_days": round(avg_age, 2),
    }


# ================================================================
#  库龄分层明细
# ================================================================

def get_age_layers(min_amount: float = 0, min_age: int = 0, max_age: int = None) -> List[Dict]:
    """
    库龄分层明细统计。

    按库存金额和库龄筛选具体物料行（项目级明细）。

    Args:
        min_amount: 最小库存金额（元），筛选条件
        min_age:    最小库龄（天），筛选条件
        max_age:    最大库龄（天），None 表示不限制上限

    Returns:
        [{id, material_code, material_name, batch_code, inventory_amount,
          current_quantity, age_days, inbound_date, unit_price,
          supplier_code, project_code, project_name}, ...]
        按 inventory_amount 降序排列
    """
    # 获取项目级明细
    rows = _get_inventory_rows()

    # ── 筛选 & 格式化 ──
    result = []
    for r in rows:
        age = r["age_days"]
        amt = r["inventory_amount"]

        # 三个筛选条件：金额 >= min_amount，库龄 >= min_age，库龄 <= max_age
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

    # 按金额降序
    result.sort(key=lambda x: x["inventory_amount"], reverse=True)
    return result


# ================================================================
#  平均库龄月度趋势
# ================================================================

def get_age_monthly() -> Dict:
    """
    按月计算加权平均库龄和超 90 天占比（最近 12 个月）。

    计算逻辑：
      对每个历史月份的月末，回溯「当月已入库」的批次：
        - 加权平均库龄 = Σ(inbound_amount × age_in_that_month) / Σ(inbound_amount)
        - 超 90 天占比  = Σ(inbound_amount WHERE age >= 90) / Σ(inbound_amount)

    权重使用 inbound_amount（入库金额）而非 inventory_amount（库存金额）：
      原因：回溯历史月份时，需要反映该批次在「入库时」的完整价值，
           而非「当前剩余」的库存价值。

    供「平均库龄月度趋势」图表使用。

    Returns:
        {months: [label, ...], data: [{month, avg_age, over90_rate}, ...]}
    """
    today = dt_date.today()

    # ── 生成最近 12 个月的月末日期（从最早到最晚）──
    month_ends: List[dt_date] = []
    for i in range(11, -1, -1):
        y = today.year
        m = today.month - i
        # 跨年回退
        while m <= 0:
            m += 12
            y -= 1
        first_day = dt_date(y, m, 1)
        # 计算该月最后一天
        if m == 12:
            last_day = dt_date(y, 12, 31)
        else:
            last_day = dt_date(y, m + 1, 1) - timedelta(days=1)
        month_ends.append(last_day)

    # ── 获取项目级明细 ──
    rows = _get_inventory_rows()

    months: List[str] = []
    data: List[Dict] = []

    # ── 逐月计算 ──
    for month_end in month_ends:
        total_weight = 0.0      # 入库金额总和（权重分母）
        age_weighted_sum = 0.0  # Σ(入库金额 × 库龄)
        over90_weight = 0.0     # 库龄 ≥ 90 天的入库金额

        for r in rows:
            d = r["inbound_date"]
            if hasattr(d, 'date'):
                d = d.date()
            elif isinstance(d, str):
                d = dt_date.fromisoformat(d)

            # 该月末还未入库 → 跳过
            if d is None or d > month_end:
                continue

            # 到该月末时的库龄 = 月末 - 入库日期
            age = (month_end - d).days
            # 使用入库金额作为权重
            weight = r["inbound_amount"]
            total_weight += weight
            age_weighted_sum += weight * age
            if age >= 90:
                over90_weight += weight

        # 当月加权平均库龄
        avg_age = round(age_weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
        # 当月超 90 天入库金额占比
        over90_rate = round(over90_weight / total_weight * 100, 1) if total_weight > 0 else 0.0

        label = f"{month_end.year}年{month_end.month}月"
        months.append(label)
        data.append({
            "month": label,
            "avg_age": avg_age,
            "over90_rate": over90_rate,
        })

    return {"months": months, "data": data}


# ================================================================
#  滞留库存热力图（物料类别 × 库龄段）
# ================================================================

def get_age_heatmap() -> Dict:
    """
    按物料类别 × 库龄段交叉统计库存金额（TOP 10 类别 × 6 库龄段）。

    ⚠️ FIX：之前直接对 v_project_inventory_wide 做 DISTINCT ON 去重，
           未复用 _BATCH_AMOUNTS_SQL。现在统一使用 utils 中的去重 CTE。

    库龄段（从短到长）：
      - 0-30天, 30-60天, 60-90天, 90-180天, 180-365天, >365天

    供「滞留库存热力图」图表使用，快速定位高库龄的品类集中区。

    Returns:
        {
            categories: [类别名称, ...],       # TOP 10 类别
            age_labels: [库龄段标签, ...],      # 从老到新排列（前端方便反转展示）
            data: [[金额(万元), ...], ...]      # 矩阵：行=库龄段, 列=类别
        }
    """
    # ── 使用统一的 _BATCH_AMOUNTS_SQL 做批次去重 ──
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            ba.material_group_code AS category_code,
            ba.batch_age_days AS age_days,
            ba.batch_inventory AS inventory_amount
        FROM batch_amounts ba
    """)
    rows = _rows_to_float(rows, "inventory_amount", "age_days")

    # ── 库龄段定义 ──
    AGE_RANGES = [
        (0, 30, '0-30天'),
        (30, 60, '30-60天'),
        (60, 90, '60-90天'),
        (90, 180, '90-180天'),
        (180, 365, '180-365天'),
        (365, 99999, '>365天'),
    ]

    # ── 取类别名称（轻量查找 wms_material_group 维度表）──
    cat_name_map: Dict[str, str] = {}
    cat_codes = list({r["category_code"] for r in rows if r["category_code"]})
    if cat_codes:
        placeholders = ','.join(['%s'] * len(cat_codes))
        name_rows = query(f"""
            SELECT code, name FROM wms_material_group
            WHERE code IN ({placeholders}) AND del_flag = '0'
        """, tuple(cat_codes))
        cat_name_map = {r["code"]: r["name"] or r["code"] for r in name_rows}

    # ── 按（类别编码 × 库龄段）聚合 ──
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
        # 分配到对应库龄段
        for min_age, max_age, label in AGE_RANGES:
            if min_age <= age < max_age:
                cat_data[code]["ages"][label] += amt
                break

    # ── 取 TOP 10 类别（按总库存金额降序）──
    top_cats = sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True)[:10]

    # ── 构建矩阵 ──
    # 行 = 库龄段（从老到新，前端方便反转展示）
    # 列 = 类别
    age_labels = [label for _, _, label in reversed(AGE_RANGES)]  # ['>365天', '180-365天', ...]
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
