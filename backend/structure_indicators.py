"""
库存结构指标计算模块
数据来源：v_project_inventory_wide。
金额统一使用 _get_wide_batch_aggregates + _get_wide_structure_aggregates。
"""

from datetime import date
from typing import Any, Dict

from utils import query, _f, _rows_to_float, _get_wide_batch_aggregates, _get_wide_structure_aggregates, _get_inventory_rows


def get_structure_indicators() -> Dict:
    """
    5. 当前库存金额（全部 / 当年）
    6. 当前库存数量
    7. 项目库存占比
    8. 采购人库存占比
    """
    current_year = date.today().year

    all_agg = _get_wide_batch_aggregates(year=None)
    year_agg = _get_wide_batch_aggregates(year=current_year)

    total_inventory_amt = all_agg.get("total_inventory_amount", 0.0)
    total_inventory_qty = all_agg.get("original_quantity", 0.0)

    structure_agg = _get_wide_structure_aggregates()
    project_rows = structure_agg.get("project_rows", [])
    purchaser_rows = structure_agg.get("purchaser_rows", [])

    project_ratios = []
    for r in project_rows:
        pa = _f(r.get("inventory_amount", 0.0))
        code = r.get("owner_project_code") or ""
        display_name = r.get("project_name") or code
        project_ratios.append({
            "project_code": code,
            "project_name": display_name,
            "inventory_amount": round(pa, 2),
            "ratio": round(pa / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    purchaser_ratios = []
    for r in purchaser_rows:
        pa = _f(r.get("inventory_amount", 0.0))
        name = r.get("purchaser_name") or "未知"
        purchaser_ratios.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inventory_amount": round(pa, 2),
            "ratio": round(pa / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    return {
        "current_year": current_year,
        "year_start": f"{current_year}-01-01",
        "year_end": f"{current_year}-12-31",
        "current_inventory_amount": round(total_inventory_amt / 10000, 2),
        "current_year_inventory_amount": round(year_agg.get("total_inventory_amount", 0.0) / 10000, 2),
        "current_inventory_quantity": round(total_inventory_qty, 2),
        "project_ratios": project_ratios,
        "purchaser_ratios": purchaser_ratios,
    }


def get_structure_by_category() -> Dict:
    """按物料编码统计库存金额，计算安全上下限。"""
    rows = query("""
        SELECT
            material_code,
            COALESCE(NULLIF(material_name, ''), material_code) AS category,
            SUM(total_price) AS inventory_amount,
            COUNT(DISTINCT batch_code) AS record_count
        FROM v_project_inventory_wide
        GROUP BY material_code, material_name
        ORDER BY inventory_amount DESC
    """)
    rows = _rows_to_float(rows, "inventory_amount")

    top_n = 10
    top_rows = rows[:top_n]
    rest_amount = sum(r["inventory_amount"] for r in rows[top_n:])
    rest_record = sum(int(r["record_count"]) if r["record_count"] else 0 for r in rows[top_n:])

    amounts = [r["inventory_amount"] for r in top_rows]
    mean_amt = sum(amounts) / len(amounts) if amounts else 0

    data = []
    for r in top_rows:
        amt = r["inventory_amount"]
        data.append({
            "material_code": r["material_code"],
            "category": r["category"],
            "current": round(amt, 2),
            "safe_max": round(mean_amt * 1.5, 2),
            "safe_min": round(mean_amt * 0.5, 2),
            "record_count": int(r["record_count"]) if r["record_count"] else 0,
        })

    if rest_amount > 0:
        data.append({
            "material_code": "-",
            "category": "其他",
            "current": round(rest_amount, 2),
            "safe_max": round(mean_amt * 1.5, 2),
            "safe_min": round(mean_amt * 0.5, 2),
            "record_count": rest_record,
        })

    return {"data": data}


def get_source_structure() -> Dict:
    """按项目统计库存金额及其占比。金额汇总使用批次去重。"""
    rows = _get_inventory_rows()

    proj_data: Dict[str, Dict] = {}
    for r in rows:
        code = r.get("project_code") or ""
        name = r.get("project_name") or ""
        label = name if name else code if code else "(未归属项目)"
        if label not in proj_data:
            proj_data[label] = {"amt": 0.0}
        proj_data[label]["amt"] += r["inventory_amount"]

    result_rows = [
        {"source_name": label, "inventory_amount": round(s["amt"], 2)}
        for label, s in proj_data.items()
    ]
    result_rows.sort(key=lambda x: x["inventory_amount"], reverse=True)

    # 使用批次去重总额作为分母，与 summary 统一
    agg = _get_wide_batch_aggregates(year=None)
    total_amt = agg.get("total_inventory_amount", 0.0)

    return {
        "total_amount": round(total_amt, 2),
        "rows": [
            {
                "source_name": r["source_name"],
                "inventory_amount": r["inventory_amount"],
                "ratio": round(r["inventory_amount"] / total_amt * 100, 2) if total_amt > 0 else 0,
            }
            for r in result_rows
        ],
    }
