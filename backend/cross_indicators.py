"""
交叉分析指标模块
================
按（项目 × 时间）二维矩阵聚合库存指标，供热力图展示。
"""

from typing import Dict, List
from datetime import date as dt_date, timedelta
from collections import OrderedDict

from utils import _get_inventory_rows, _f, query


def get_project_matrix(
    metric: str = "inventory_amount",
    project_type: str = None,
    months: int = 12,
) -> Dict:
    """
    按 (project_code, 月份) 聚合指定指标，返回热力图矩阵。

    参数：
      metric:       inventory_amount | inbound_amount | claimed_amount | claim_rate | age_days
      project_type: 项目类型筛选
      months:       返回最近 N 个月

    返回：
      { projects, project_codes, months, data, metric, unit }
    """
    if metric not in {"inventory_amount", "inbound_amount", "claimed_amount", "claim_rate", "age_days"}:
        metric = "inventory_amount"

    rows = _get_inventory_rows()

    # 生成最近 N 个月标签
    today = dt_date.today()
    month_labels = []
    for i in range(months - 1, -1, -1):
        d = today.replace(day=1) - timedelta(days=1)
        d = d.replace(day=1)
        # 逐月回退
        y, m = today.year, today.month
        m -= i
        while m <= 0:
            y -= 1
            m += 12
        month_labels.append(f"{y}-{m:02d}")

    # 按 (project_code, month) 聚合
    matrix: Dict[str, Dict[str, float]] = {}
    project_inv_totals: Dict[str, float] = {}
    project_names: Dict[str, str] = {}

    for r in rows:
        code = r["project_code"] or ""
        if not code:
            continue

        # 筛选项目类型
        if project_type:
            pt = r.get("project_type") or ""
            if pt != project_type:
                continue

        d = r["inbound_date"]
        if d is None:
            continue
        if hasattr(d, 'date'):
            d = d.date()
        mon = f"{d.year}-{d.month:02d}"
        if mon not in month_labels:
            continue

        inv_amt = r["inventory_amount"]

        if code not in matrix:
            matrix[code] = {}
            project_names[code] = (r.get("project_name") or code)

        if mon not in matrix[code]:
            matrix[code][mon] = {"inv": 0.0, "inb": 0.0, "clm": 0.0, "age_w": 0.0}

        cell = matrix[code][mon]
        cell["inv"] += inv_amt
        cell["inb"] += r["inbound_amount"]
        cell["clm"] += r["claimed_amount"]
        cell["age_w"] += inv_amt * r["age_days"]

        if code not in project_inv_totals:
            project_inv_totals[code] = 0.0
        project_inv_totals[code] += inv_amt

    # 取 TOP 15 项目
    top_projects = sorted(project_inv_totals.items(), key=lambda x: x[1], reverse=True)[:15]
    project_list = [p[0] for p in top_projects]
    project_label_list = [project_names.get(p, p) for p in project_list]

    # 构建二维数据
    data = []
    for proj in project_list:
        row = []
        for mon in month_labels:
            cell = matrix.get(proj, {}).get(mon)
            if cell is None:
                row.append(0)
            elif metric == "claim_rate":
                val = cell["clm"] / cell["inb"] * 100 if cell["inb"] > 0 else 0
                row.append(round(val, 2))
            elif metric == "age_days":
                val = cell["age_w"] / cell["inv"] if cell["inv"] > 0 else 0
                row.append(round(val, 2))
            elif metric == "inbound_amount":
                row.append(round(cell["inb"] / 10000, 2))
            elif metric == "claimed_amount":
                row.append(round(cell["clm"] / 10000, 2))
            else:  # inventory_amount
                row.append(round(cell["inv"] / 10000, 2))
        data.append(row)

    unit_map = {
        "claim_rate": "%", "age_days": "天",
        "inventory_amount": "万元", "inbound_amount": "万元", "claimed_amount": "万元",
    }

    return {
        "projects": project_label_list,
        "project_codes": project_list,
        "months": month_labels,
        "data": data,
        "metric": metric,
        "unit": unit_map.get(metric, "万元"),
    }


def get_available_dimensions() -> List[Dict]:
    """返回所有可用的分析维度（供前端横轴/纵轴/筛选下拉使用）。"""
    return [
        {"label": "时间(月)", "value": "month", "type": "time"},
        {"label": "时间(周)", "value": "week", "type": "time"},
        {"label": "项目", "value": "project", "type": "entity"},
        {"label": "采购人", "value": "purchaser", "type": "entity"},
        {"label": "项目类型", "value": "project_type", "type": "entity"},
        {"label": "批次", "value": "batch_code", "type": "entity"},
        {"label": "入库金额(万元)", "value": "inbound_amount", "type": "metric"},
        {"label": "领用金额(万元)", "value": "claimed_amount", "type": "metric"},
        {"label": "库存金额(万元)", "value": "inventory_amount", "type": "metric"},
        {"label": "领用率(%)", "value": "claim_rate", "type": "metric"},
        {"label": "平均库龄(天)", "value": "age_days", "type": "metric"},
        {"label": "物料", "value": "material_code", "type": "entity"},
    ]


def get_project_types() -> List[str]:
    """返回视图中所有非空的 project_type 值，供筛选下拉使用。"""
    rows = query("""
        SELECT plan_category AS project_type
        FROM v_project_inventory_wide
        WHERE char_length(COALESCE(plan_category, '')) > 0
        GROUP BY plan_category
        ORDER BY COUNT(*) DESC
    """)
    return [r["project_type"] for r in rows]


def get_top_projects(metric: str = "inventory_amount", project_type: str = None, limit: int = 15, group_by: str = "project") -> Dict:
    """TOP N 数据，按 group_by (project/month/purchaser/project_type) 分组。"""
    rows = _get_inventory_rows()
    data: Dict[str, float] = {}
    names: Dict[str, str] = {}
    weight_div: Dict[str, float] = {}  # 加权分母：claim_rate用inbound，age_days用inventory

    for r in rows:
        if project_type and (r.get("project_type") or "") != project_type:
            continue

        d = r.get("inbound_date")
        if hasattr(d, 'date'):
            d = d.date()

        if group_by == "month":
            key = f"{d.year}-{d.month:02d}" if d else "未知"
        elif group_by == "purchaser":
            key = (r.get("purchaser_name") or "").strip() or "未知"
        elif group_by == "project_type":
            key = (r.get("project_type") or "").strip() or "未分类"
        else:
            key = r.get("project_code") or ""
            if not key:
                continue
            names[key] = r.get("project_name") or key

        if group_by not in ("project",):
            names[key] = key

        inv = r.get("inventory_amount", 0) or 0
        if metric == "claim_rate":
            data[key] = data.get(key, 0.0) + r.get("claimed_amount", 0)
            weight_div[key] = weight_div.get(key, 0.0) + r.get("inbound_amount", 0)
        elif metric == "age_days":
            data[key] = data.get(key, 0.0) + inv * r.get("age_days", 0)
            weight_div[key] = weight_div.get(key, 0.0) + inv
        else:
            data[key] = data.get(key, 0.0) + (r.get(metric, 0) or 0)

    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:limit]

    labels, values = [], []
    for key, val in sorted_items:
        if metric == "claim_rate":
            dv = weight_div.get(key, 1)
            display_val = round(val / dv * 100, 2) if dv else 0
        elif metric == "age_days":
            dv = weight_div.get(key, 1)
            display_val = round(val / dv, 2) if dv else 0
        elif metric in ("inbound_amount", "claimed_amount", "inventory_amount"):
            display_val = round(val / 10000, 2)
        else:
            display_val = round(val, 2)
        labels.append(names.get(key, key))
        values.append(display_val)

    unit_map = {"claim_rate": "%", "age_days": "天", "inventory_amount": "万元", "inbound_amount": "万元", "claimed_amount": "万元"}
    return {"labels": labels, "values": values, "unit": unit_map.get(metric, "万元")}

def get_project_trend(project_type: str = None, metric: str = "inventory_amount", months: int = 12) -> Dict:
    """TOP 8 项目月度趋势（每条项目一根折线）。"""
    from datetime import date as dt_date, timedelta

    today = dt_date.today()
    month_labels = []
    for i in range(months - 1, -1, -1):
        y, m = today.year, today.month
        m -= i
        while m <= 0:
            y -= 1
            m += 12
        month_labels.append(f"{y}-{m:02d}")

    rows = _get_inventory_rows()
    proj_month: Dict[str, Dict[str, float]] = {}
    proj_totals: Dict[str, float] = {}
    proj_names: Dict[str, str] = {}

    for r in rows:
        code = r["project_code"] or ""
        if not code:
            continue
        if project_type:
            if (r.get("project_type") or "") != project_type:
                continue
        d = r["inbound_date"]
        if d is None:
            continue
        if hasattr(d, 'date'):
            d = d.date()
        mon = f"{d.year}-{d.month:02d}"
        if mon not in month_labels:
            continue

        val = r.get(metric, 0) or 0
        proj_names[code] = r.get("project_name") or code
        proj_totals[code] = proj_totals.get(code, 0.0) + val
        if code not in proj_month:
            proj_month[code] = {}
        proj_month[code][mon] = proj_month[code].get(mon, 0.0) + val

    top8 = sorted(proj_totals.items(), key=lambda x: x[1], reverse=True)[:8]

    unit_map = {
        "claim_rate": "%", "age_days": "天",
        "inventory_amount": "万元", "inbound_amount": "万元", "claimed_amount": "万元",
    }
    divisor = 10000 if metric in ("inventory_amount", "inbound_amount", "claimed_amount") else 1

    series = []
    for code, _ in top8:
        data = [round(proj_month.get(code, {}).get(mon, 0) / divisor, 2) for mon in month_labels]
        series.append({"name": proj_names.get(code, code), "data": data})

    return {"months": month_labels, "series": series, "unit": unit_map.get(metric, "万元")}


def get_source_distribution(project_type: str = None) -> Dict:
    """来源分布：按采购人聚合库存金额（饼图）。"""
    rows = _get_inventory_rows()
    purchaser_data: Dict[str, float] = {}
    for r in rows:
        if project_type:
            if (r.get("project_type") or "") != project_type:
                continue
        name = (r.get("purchaser_name") or "").strip()
        if not name:
            name = "未知"
        purchaser_data[name] = purchaser_data.get(name, 0.0) + r["inventory_amount"]

    sorted_data = sorted(purchaser_data.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "labels": [x[0] for x in sorted_data],
        "values": [round(x[1] / 10000, 2) for x in sorted_data],
        "unit": "万元",
    }


def get_distinct_values(field: str, project_type: str = None, project_code: str = None) -> List[str]:
    """返回视图中指定字段的所有可选值列表。数据来源：v_project_inventory_wide。"""
    if field == "project_type":
        return get_project_types()

    if field == "project_code":
        rows = query("SELECT DISTINCT owner_project_code FROM v_project_inventory_wide WHERE char_length(COALESCE(owner_project_code, '')) > 0 ORDER BY owner_project_code")
        return [r["owner_project_code"] for r in rows if r["owner_project_code"]]

    if field == "material_code":
        rows = query("SELECT DISTINCT material_code FROM v_project_inventory_wide WHERE char_length(COALESCE(material_code, '')) > 0 ORDER BY material_code")
        return [r["material_code"] for r in rows if r["material_code"]]

    if field == "purchaser_name":
        rows = query("SELECT DISTINCT project_submitter FROM v_project_inventory_wide WHERE char_length(COALESCE(project_submitter, '')) > 0 ORDER BY project_submitter")
        return [r["project_submitter"] for r in rows if r["project_submitter"]]

    if field == "applicant_name":
        rows = query("SELECT DISTINCT purchaser_name FROM v_project_inventory_wide WHERE char_length(COALESCE(purchaser_name, '')) > 0 ORDER BY purchaser_name")
        return [r["purchaser_name"] for r in rows if r["purchaser_name"]]

    if field == "submitter_name":
        rows = query("SELECT DISTINCT project_submitter FROM v_project_inventory_wide WHERE char_length(COALESCE(project_submitter, '')) > 0 ORDER BY project_submitter")
        return [r["project_submitter"] for r in rows if r["project_submitter"]]

    if field == "contact_name":
        rows = query("SELECT DISTINCT project_contact FROM v_project_inventory_wide WHERE char_length(COALESCE(project_contact, '')) > 0 ORDER BY project_contact")
        return [r["project_contact"] for r in rows if r["project_contact"]]

    if field == "batch_code":
        sql = "SELECT DISTINCT batch_code FROM v_project_inventory_wide WHERE char_length(COALESCE(batch_code, '')) > 0"
        params = None
        if project_code:
            sql += " AND owner_project_code = %s"
            params = (project_code,)
        sql += " ORDER BY batch_code"
        rows = query(sql, params)
        return [r["batch_code"] for r in rows if r["batch_code"]]

    return []
