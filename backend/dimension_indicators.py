"""
维度指标计算模块
================
按项目和采购人维度的库存分析指标。
金额统一来源于 _get_inventory_rows() → batch_amounts 去重 × project_ratio 分配。
"""

from typing import Any, Dict, List

from utils import query, _f, _rows_to_float, _get_inventory_rows


ALLOWED_SORT_COLUMNS = {
    "claim_rate": "claim_rate",
    "age_days": "age_days",
    "avg_age_days": "avg_age_days",
    "inventory_amount": "inventory_amount",
    "inbound_amount": "inbound_amount",
    "inbound_date": "inbound_date",
}


def get_by_project() -> List[Dict]:
    """13-15. 项目采购领用率 / 未消耗库存金额 / 平均库龄"""
    rows = _get_inventory_rows()

    proj_stats: Dict[str, Dict] = {}
    proj_names: Dict[str, str] = {}
    for r in rows:
        code = r.get("project_code") or ""
        if code not in proj_stats:
            proj_stats[code] = {"inb": 0.0, "clm": 0.0, "inv": 0.0, "age_w": 0.0, "over90": 0.0, "cnt": 0}
        proj_stats[code]["inb"] += r["inbound_amount"]
        proj_stats[code]["clm"] += r["claimed_amount"]
        proj_stats[code]["inv"] += r["inventory_amount"]
        proj_stats[code]["age_w"] += r["inventory_amount"] * r["age_days"]
        if r["age_days"] >= 90:
            proj_stats[code]["over90"] += r["inventory_amount"]
        proj_stats[code]["cnt"] += 1
        if code and code not in proj_names:
            proj_names[code] = r.get("project_name") or code

    result = []
    for code, s in proj_stats.items():
        inb, clm, inv, age_w, over90 = s["inb"], s["clm"], s["inv"], s["age_w"], s["over90"]
        result.append({
            "project_code": code,
            "project_name": proj_names.get(code, code),
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "unclaimed_amount": round(inv, 2),
            "claim_rate": min(round(clm / inb * 100, 2), 100.00) if inb else 0,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
            "over90_ratio": round(over90 / inv * 100, 1) if inv else 0,
            "record_count": s["cnt"],
        })
    result.sort(key=lambda x: x["unclaimed_amount"], reverse=True)
    return result


def get_by_purchaser() -> List[Dict]:
    """16-18. 采购人领用率 / 未消耗库存金额 / 库存库龄（按联系人）"""
    rows = _get_inventory_rows()

    pur_stats: Dict[str, Dict] = {}
    for r in rows:
        name = (r.get("contact_name") or "").strip()
        if not name:
            continue
        if name not in pur_stats:
            pur_stats[name] = {"inb": 0.0, "clm": 0.0, "inv": 0.0, "age_w": 0.0, "cnt": 0}
        pur_stats[name]["inb"] += r["inbound_amount"]
        pur_stats[name]["clm"] += r["claimed_amount"]
        pur_stats[name]["inv"] += r["inventory_amount"]
        pur_stats[name]["age_w"] += r["inventory_amount"] * r["age_days"]
        pur_stats[name]["cnt"] += 1

    result = []
    for name, s in pur_stats.items():
        inb, clm, inv, age_w = s["inb"], s["clm"], s["inv"], s["age_w"]
        result.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "unclaimed_amount": round(inv, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else 0,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
            "record_count": s["cnt"],
        })
    result.sort(key=lambda x: x["unclaimed_amount"], reverse=True)
    return result


def get_project_summary(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
) -> Dict:
    """按项目维度汇总：入库/领用/库存金额、领用率、平均库龄"""
    rows = _get_inventory_rows()

    proj_data: Dict[str, Dict] = {}
    proj_label: Dict[str, str] = {}
    for r in rows:
        code = r.get("project_code") or ""
        name = r.get("project_name") or ""
        label = name if name else code if code else "(未归属项目)"
        if code not in proj_data:
            proj_data[code] = {"inb": 0.0, "clm": 0.0, "inv": 0.0, "age_w": 0.0}
            proj_label[code] = label
        proj_data[code]["inb"] += r["inbound_amount"]
        proj_data[code]["clm"] += r["claimed_amount"]
        proj_data[code]["inv"] += r["inventory_amount"]
        proj_data[code]["age_w"] += r["inventory_amount"] * r["age_days"]

    result = []
    for code, s in proj_data.items():
        inb, clm, inv, age_w = s["inb"], s["clm"], s["inv"], s["age_w"]
        result.append({
            "project_name": proj_label.get(code, code),
            "project_code": code,
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "inventory_amount": round(inv, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else None,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
        })

    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, "inventory_amount")
    reverse = sort_order.lower() == "desc"
    result.sort(key=lambda x: x.get(sort_col, 0) or 0, reverse=reverse)
    return {"total": len(result), "rows": result}


def get_purchaser_summary(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
) -> Dict:
    """按联系人维度汇总"""
    rows = _get_inventory_rows()

    pur_data: Dict[str, Dict] = {}
    for r in rows:
        name = (r.get("contact_name") or "").strip()
        label = name if name else "(未归属联系人)"
        if label not in pur_data:
            pur_data[label] = {"inb": 0.0, "clm": 0.0, "inv": 0.0, "age_w": 0.0}
        pur_data[label]["inb"] += r["inbound_amount"]
        pur_data[label]["clm"] += r["claimed_amount"]
        pur_data[label]["inv"] += r["inventory_amount"]
        pur_data[label]["age_w"] += r["inventory_amount"] * r["age_days"]

    result = []
    for label, s in pur_data.items():
        inb, clm, inv, age_w = s["inb"], s["clm"], s["inv"], s["age_w"]
        result.append({
            "purchaser_name": label,
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "inventory_amount": round(inv, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else None,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
        })

    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, "inventory_amount")
    reverse = sort_order.lower() == "desc"
    result.sort(key=lambda x: x.get(sort_col, 0) or 0, reverse=reverse)
    return {"total": len(result), "rows": result}
