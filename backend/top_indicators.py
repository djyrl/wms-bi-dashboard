"""
TOP 排行与优化建议模块
======================
未领用/已领用 TOP N 排行、智能备货优化建议。
"""

from typing import Dict, List

from utils import _f, _get_inventory_rows


def get_top_unclaimed_amount(limit: int = 10) -> List[Dict]:
    """19. 未领用库存 TOP（金额），附带项目归属和采购人。
    数据来源：v_project_inventory_wide，项目名称和采购人直接从宽表字段取。"""
    rows = _get_inventory_rows()
    rows.sort(key=lambda r: r["inventory_amount"], reverse=True)
    top_rows = rows[:limit]

    return [
        {
            "id": r["id"],
            "material_code": r["material_code"],
            "material_name": r["material_name"],
            "batch_code": r["batch_code"],
            "inventory_amount": round(r["inventory_amount"], 2),
            "current_quantity": r["current_quantity"],
            "unit": r["unit"],
            "age_days": int(r["age_days"]),
            "inbound_date": str(r["inbound_date"]),
            "unit_price": r["unit_price"],
            "owner_project_code": r.get("project_code", ""),
            "owner_project_name": r.get("project_name", ""),
            "purchaser_name": r.get("purchaser_name", ""),
        }
        for r in top_rows
    ]


def get_optimize_suggest(limit: int = 8, safety_days: int = 60) -> List[Dict]:
    """智能备货优化建议：按物料汇总，基于日均消耗推荐安全库存上限"""
    rows = _get_inventory_rows()

    # ---- 按物料编码汇总 ----
    mat_stats: Dict[str, Dict] = {}
    for r in rows:
        code = r["material_code"]
        if code not in mat_stats:
            mat_stats[code] = {
                "name": r["material_name"],
                "current": 0.0,        # 当前库存金额
                "claimed": 0.0,        # 已领用金额
                "age_weighted": 0.0,   # 金额加权库龄
                "inv_total": 0.0,      # 库存金额合计（用于加权）
            }
        s = mat_stats[code]
        s["current"] += r["inventory_amount"]
        s["claimed"] += r["claimed_amount"]
        s["age_weighted"] += r["inventory_amount"] * r["age_days"]
        s["inv_total"] += r["inventory_amount"]

    # ---- 计算日均消耗 & 建议上限 ----
    result = []
    for code, s in mat_stats.items():
        current_wan = s["current"] / 10000
        if current_wan <= 0:
            continue

        # 金额加权平均库龄
        avg_age = s["age_weighted"] / s["inv_total"] if s["inv_total"] > 0 else 0
        if avg_age <= 0:
            continue

        # 日均消耗（万元/天）= 已领用金额 / 平均库龄
        daily_use = (s["claimed"] / avg_age) / 10000

        # 建议上限 = 日均消耗 × 安全库存天数
        max_stock = daily_use * safety_days

        # 只保留当前库存超标的物料
        if current_wan > max_stock and daily_use > 0:
            result.append({
                "name": s["name"],
                "current": round(current_wan, 2),
                "dailyUse": round(daily_use, 2),
                "maxStock": round(max_stock, 2),
            })

    # 按超出量降序排列
    result.sort(key=lambda x: x["current"] - x["maxStock"], reverse=True)
    return result[:limit]


def get_top_unclaimed_quantity(limit: int = 10) -> List[Dict]:
    """20. 未领用库存 TOP（数量）"""
    rows = _get_inventory_rows()
    rows.sort(key=lambda r: r["current_quantity"], reverse=True)
    return [
        {
            "id": r["id"],
            "material_code": r["material_code"],
            "material_name": r["material_name"],
            "batch_code": r["batch_code"],
            "inventory_amount": round(r["inventory_amount"], 2),
            "current_quantity": r["current_quantity"],
            "age_days": int(r["age_days"]),
            "inbound_date": str(r["inbound_date"]),
        }
        for r in rows[:limit]
    ]


def get_top_claimed_amount(limit: int = 10) -> List[Dict]:
    """21. 领用 TOP（金额）— 按物料编码聚合"""
    rows = _get_inventory_rows()
    agg: Dict[str, Dict] = {}
    for r in rows:
        code = r["material_code"]
        if code not in agg:
            agg[code] = {
                "material_code": code,
                "material_name": r.get("material_name", ""),
                "claimed_amount": 0.0,
                "inbound_amount": 0.0,
                "inbound_date": "",
            }
        a = agg[code]
        a["claimed_amount"] += _f(r["claimed_amount"])
        a["inbound_amount"] += _f(r["inbound_amount"])
        if str(r["inbound_date"]) > a["inbound_date"]:
            a["inbound_date"] = str(r["inbound_date"])
    result = sorted(agg.values(), key=lambda x: x["claimed_amount"], reverse=True)
    for a in result:
        a["claimed_amount"] = round(a["claimed_amount"], 2)
        a["inbound_amount"] = round(a["inbound_amount"], 2)
    return result[:limit]


def get_top_claimed_quantity(limit: int = 10) -> List[Dict]:
    """22. 领用 TOP（数量）— 按物料编码聚合"""
    rows = _get_inventory_rows()
    agg: Dict[str, Dict] = {}
    for r in rows:
        code = r["material_code"]
        if code not in agg:
            agg[code] = {
                "material_code": code,
                "material_name": r.get("material_name", ""),
                "claimed_quantity": 0.0,
                "inbound_quantity": 0.0,
                "inbound_date": "",
            }
        a = agg[code]
        a["claimed_quantity"] += _f(r["used_quantity"])
        a["inbound_quantity"] += _f(r["original_quantity"])
        if str(r["inbound_date"]) > a["inbound_date"]:
            a["inbound_date"] = str(r["inbound_date"])
    result = sorted(agg.values(), key=lambda x: x["claimed_quantity"], reverse=True)
    for a in result:
        a["claimed_quantity"] = round(a["claimed_quantity"], 2)
        a["inbound_quantity"] = round(a["inbound_quantity"], 2)
    return result[:limit]
