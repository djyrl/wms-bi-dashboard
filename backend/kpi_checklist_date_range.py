"""
采购库存 BI — KPI 考核清单模块（时间区间版）
===========================================
与 kpi_checklist.py 完全相同的计算逻辑，但支持按入库日期区间过滤。

所有指标计算基于 start_date ~ end_date 窗口内的入库批次数据。
不修改原 kpi_checklist.py，独立提供接口。

═══════════════════════════════════════════════════════════════════════════
使用方式：
  get_kpi_checklist_by_date_range("2024-01-01", "2024-12-31")
═══════════════════════════════════════════════════════════════════════════
"""

from datetime import date
from typing import Any, Dict, List, Tuple

from utils import (
    _get_inventory_rows,
    _get_batch_rows,
    _get_wide_batch_aggregates,
    _get_wide_structure_aggregates,
)
from dimension_indicators import get_by_project, get_by_purchaser

TODAY = date.today()


# ================================================================
#  辅助：状态判定（与 kpi_checklist.py 完全一致）
# ================================================================

def _status_for_rate(rate: float, target: float, direction: str = "up") -> str:
    if direction == "up":
        if rate >= target:
            return "ok"
        elif rate >= target * 0.85:
            return "warning"
        else:
            return "alert"
    else:
        if rate <= target:
            return "ok"
        elif rate <= target * 1.15:
            return "warning"
        else:
            return "alert"


# ================================================================
#  主入口：按日期区间计算全部 KPI 指标
# ================================================================

def get_kpi_checklist_by_date_range(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    获取 KPI 考核清单（按入库日期区间过滤版）。

    Args:
        start_date: 入库日期下限，格式 'YYYY-MM-DD'
        end_date:   入库日期上限，格式 'YYYY-MM-DD'

    Returns:
        与 get_kpi_checklist() 结构完全一致：
        { summary, core_kpis, constraint_kpis, structure_kpis, top_kpis }
    """

    # ================================================================
    #  Step 1: 拉取数据（全部传入日期区间）
    # ================================================================
    agg = _get_wide_batch_aggregates(start_date=start_date, end_date=end_date)
    total_inbound_amt = agg["total_inbound_amount"]
    total_claimed_amt = agg["total_claimed_amount"]
    total_inventory_amt = agg["total_inventory_amount"]
    total_inbound_qty = agg["original_quantity"]
    total_outbound_qty = agg["total_outbound_quantity"]

    batch_rows = _get_batch_rows(start_date=start_date, end_date=end_date)
    inv_rows = _get_inventory_rows(start_date=start_date, end_date=end_date)
    structure_data = _get_wide_structure_aggregates(start_date=start_date, end_date=end_date)

    k8_projects = get_by_project(start_date=start_date, end_date=end_date)
    k5_projects = get_by_project(owner_project_type='Q', start_date=start_date, end_date=end_date)
    k9_purchasers = get_by_purchaser(start_date=start_date, end_date=end_date)

    # ================================================================
    #  Step 2: 内存计算核心指标 K1-K5
    # ================================================================

    AGE_BUCKETS: List[Tuple[str, int, int]] = [
        ("≤1年", 0, 365),
        ("1~3年", 365, 1095),
        ("3~5年", 1095, 1825),
        ("≥5年", 1825, 999999),
    ]
    age_amt = {label: 0.0 for label, _, _ in AGE_BUCKETS}
    age_cnt = {label: 0 for label, _, _ in AGE_BUCKETS}

    age_weighted_sum = 0.0
    aged_365_amt = 0.0

    for r in batch_rows:
        amt = r["inventory_amount"]
        age = r["age_days"]
        age_weighted_sum += amt * age
        if age >= 365:
            aged_365_amt += amt
        for label, lo, hi in AGE_BUCKETS:
            if lo <= age < hi:
                age_amt[label] += amt
                age_cnt[label] += 1
                break

    claim_rate_amt = round(total_claimed_amt / total_inbound_amt * 100, 2) \
        if total_inbound_amt else 0.0
    claim_rate_qty = round(total_outbound_qty / total_inbound_qty * 100, 2) \
        if total_inbound_qty else 0.0
    unclaimed_amt = round((total_inbound_amt - total_claimed_amt) / 10000, 2)
    total_inbound_wan = round(total_inbound_amt / 10000, 2)
    total_claimed_wan = round(total_claimed_amt / 10000, 2)
    total_inventory_wan = round(total_inventory_amt / 10000, 2)
    unclaimed_ratio = round(
        (total_inbound_amt - total_claimed_amt) / total_inbound_amt * 100, 2
    ) if total_inbound_amt else 0.0

    age_total = sum(age_amt.values())
    age_structure = []
    aged_365_ratio = 0.0
    for label, lo, hi in AGE_BUCKETS:
        amt = age_amt[label]
        ratio = round(amt / age_total, 4) if age_total else 0
        age_structure.append({
            "range": label,
            "amount": round(amt, 2),
            "ratio": ratio,
            "count": age_cnt[label],
        })
        if lo >= 365:
            aged_365_ratio += ratio

    avg_age_days = round(age_weighted_sum / total_inventory_amt, 2) \
        if total_inventory_amt else 0.0
    aged_ratio = round(aged_365_ratio, 4)

    unused_weighted = 0.0
    unused_total_amt = 0.0
    total_inventory_qty = 0.0
    min_inbound_date = None
    max_inbound_date = None

    for r in inv_rows:
        inventory = r["inventory_amount"]
        age = r["age_days"]
        d = r.get("inbound_date")
        if d is not None:
            if hasattr(d, 'date'):
                d = d.date()
            if min_inbound_date is None or d < min_inbound_date:
                min_inbound_date = d
            if max_inbound_date is None or d > max_inbound_date:
                max_inbound_date = d
        total_inventory_qty += r["current_quantity"]
        if r["claimed_amount"] == 0 and r["current_quantity"] > 0:
            unused_weighted += inventory * age
            unused_total_amt += inventory

    unused_days = round(unused_weighted / unused_total_amt, 2) \
        if unused_total_amt else 0.0

    # ================================================================
    #  Step 3: 组装 KPI 指标
    # ================================================================

    K1_status = _status_for_rate(claim_rate_amt, 80, "up")
    core_kpis = {
        "K1": {
            "key": "K1", "name": "采购领用率（金额）",
            "formula": "领用金额 / 入库金额 × 100%",
            "value": claim_rate_amt, "unit": "%", "target": "≥80%",
            "target_value": 80, "direction": "up", "status": K1_status,
            "detail": {
                "claimed_amount_wan": total_claimed_wan,
                "inbound_amount_wan": total_inbound_wan,
                "unclaimed_amount_wan": unclaimed_amt,
                "claim_rate_quantity": claim_rate_qty,
            },
        },
        "K2": {
            "key": "K2", "name": "当前库存金额",
            "formula": "SUM(current_quantity × unit_price) = v_total_price",
            "value": total_inventory_wan, "unit": "万元",
            "target": "控制上限，同比下降", "target_value": None,
            "direction": "down", "status": "info",
            "detail": {
                "inventory_quantity": round(total_inventory_qty, 2),
                "batch_count": len(batch_rows),
            },
        },
        "K3": {
            "key": "K3", "name": "长库龄库存金额占比（≥1年）",
            "formula": "库龄≥365天的库存金额 / 总库存金额 × 100%",
            "value": round(aged_ratio * 100, 2), "unit": "%",
            "target": "逐年下降", "target_value": None, "direction": "down",
            "status": "warning" if aged_ratio > 0.15 else "ok",
            "detail": {
                "aged_amount_1y_wan": round(sum(
                    age_amt[label] for label, lo, _ in AGE_BUCKETS if lo >= 365
                ) / 10000, 2),
                "avg_age_weighted_days": avg_age_days,
                "age_structure": age_structure,
            },
        },
    }

    K4_status = "warning" if unclaimed_ratio > 30 else "ok"
    constraint_kpis = {
        "K4": {
            "key": "K4", "name": "未领用采购金额",
            "formula": "入库金额 - 领用金额",
            "value": unclaimed_amt, "unit": "万元",
            "target": "控制新增库存", "target_value": None,
            "direction": "down", "status": K4_status,
            "detail": {
                "unclaimed_amount_wan": unclaimed_amt,
                "unclaimed_ratio": unclaimed_ratio,
                "total_inbound_wan": total_inbound_wan,
                "total_claimed_wan": total_claimed_wan,
            },
        },
        "K5": {
            "key": "K5", "name": "项目未消耗库存",
            "formula": "按项目汇总 inventory_amount（仅 owner_project_type='Q'）",
            "value": round(sum(p["unclaimed_amount"] for p in k5_projects) / 10000, 2),
            "unit": "万元",
            "target": "项目采购约束（A修、技改等特定范围）",
            "target_value": None, "direction": "down", "status": "info",
            "detail": {
                "projects": [
                    {
                        "project_code": p["project_code"],
                        "project_name": p["project_name"],
                        "unclaimed_amount_wan": round(p["unclaimed_amount"] / 10000, 2),
                        "claim_rate": p["claim_rate"],
                        "avg_age_days": p["avg_age_days"],
                    }
                    for p in k5_projects[:10]
                ],
                "total_count": len(k5_projects),
            },
        },
    }

    # ── K6: 库存结构分析 ──
    project_rows = structure_data["project_rows"]
    purchaser_rows = structure_data["purchaser_rows"]
    structure_kpis = {
        "K6": {
            "key": "K6", "name": "库存结构分析",
            "description": "项目库存占比 TOP 10、采购人库存占比 TOP 10",
            "project_ratios": [
                {
                    "project_code": p["owner_project_code"],
                    "project_name": p["project_name"] or p["owner_project_code"],
                    "inventory_amount_wan": round(p["inventory_amount"] / 10000, 2),
                    "ratio": round(p["inventory_amount"] / total_inventory_amt * 100, 2)
                    if total_inventory_amt else 0,
                }
                for p in project_rows[:10]
            ],
            "purchaser_ratios": [
                {
                    "purchaser_name": p["purchaser_name"],
                    "inventory_amount_wan": round(p["inventory_amount"] / 10000, 2),
                    "ratio": round(p["inventory_amount"] / total_inventory_amt * 100, 2)
                    if total_inventory_amt else 0,
                }
                for p in purchaser_rows[:10]
            ],
        },
        "K7": {
            "key": "K7", "name": "时间分析",
            "description": "平均库龄、未动用天数、库龄结构",
            "avg_age_weighted_days": avg_age_days,
            "unused_days": unused_days,
            "age_structure": age_structure,
            "aged_ratio_1y": round(aged_ratio * 100, 2),
        },
        "K8": {
            "key": "K8", "name": "项目分析",
            "description": "回答：哪个项目带来库存",
            "items": [
                {
                    "project_code": p["project_code"],
                    "project_name": p["project_name"],
                    "claim_rate": p["claim_rate"],
                    "inventory_amount_wan": round(p["unclaimed_amount"] / 10000, 2),
                    "avg_age_days": p["avg_age_days"],
                    "over90_ratio": p["over90_ratio"],
                }
                for p in k8_projects
            ],
        },
        "K9": {
            "key": "K9", "name": "采购人分析",
            "description": "采购人领用率、未消耗库存、库龄",
            "items": [
                {
                    "purchaser_name": p["purchaser_name"],
                    "claim_rate": p["claim_rate"],
                    "unclaimed_amount_wan": round(p["unclaimed_amount"] / 10000, 2),
                    "avg_age_days": p["avg_age_days"],
                }
                for p in k9_purchasers
            ],
        },
    }

    # ================================================================
    #  Step 4: TOP 指标 T1-T2
    # ================================================================

    mat_agg: Dict[str, Dict] = {}
    for r in inv_rows:
        code = r["material_code"]
        if code not in mat_agg:
            mat_agg[code] = {
                "material_code": code,
                "material_name": r["material_name"],
                "inventory_amount": 0.0, "current_quantity": 0.0,
                "unit": r["unit"], "age_days": 0, "age_weight": 0.0,
                "project_code": "", "project_name": "", "purchaser_name": "",
            }
        a = mat_agg[code]
        a["inventory_amount"] += r["inventory_amount"]
        a["current_quantity"] += r["current_quantity"]
        a["age_weight"] += r["inventory_amount"] * r["age_days"]
        if r["age_days"] > a["age_days"]:
            a["age_days"] = int(r["age_days"])
            a["project_code"] = r.get("project_code", "")
            a["project_name"] = r.get("project_name", "")
            a["purchaser_name"] = r.get("purchaser_name", "")

    sorted_by_inventory = sorted(mat_agg.values(), key=lambda x: x["inventory_amount"], reverse=True)
    t1_items = []
    for idx, r in enumerate(sorted_by_inventory[:10]):
        t1_items.append({
            "rank": idx + 1,
            "material_code": r["material_code"],
            "material_name": r["material_name"],
            "inventory_amount_wan": round(r["inventory_amount"] / 10000, 2),
            "current_quantity": r["current_quantity"],
            "unit": r["unit"],
            "age_days": r["age_days"],
            "owner_project_code": r["project_code"],
            "owner_project_name": r["project_name"],
            "purchaser_name": r["purchaser_name"],
        })

    mat_claimed_amt: Dict[str, Dict] = {}
    for r in inv_rows:
        code = r["material_code"]
        if code not in mat_claimed_amt:
            mat_claimed_amt[code] = {
                "material_code": code, "material_name": r["material_name"],
                "claimed_amount": 0.0, "inbound_amount": 0.0, "inbound_date": "",
            }
        a = mat_claimed_amt[code]
        a["claimed_amount"] += r["claimed_amount"]
        a["inbound_amount"] += r["inbound_amount"]
        if str(r["inbound_date"]) > a["inbound_date"]:
            a["inbound_date"] = str(r["inbound_date"])

    sorted_by_claimed = sorted(mat_claimed_amt.values(), key=lambda x: x["claimed_amount"], reverse=True)
    t2_by_amount = [
        {
            "rank": idx + 1,
            "material_code": r["material_code"],
            "material_name": r["material_name"],
            "claimed_amount_wan": round(r["claimed_amount"] / 10000, 2),
            "inbound_amount_wan": round(r["inbound_amount"] / 10000, 2),
            "inbound_date": r["inbound_date"],
        }
        for idx, r in enumerate(sorted_by_claimed[:10])
    ]

    mat_claimed_qty: Dict[str, Dict] = {}
    for r in inv_rows:
        code = r["material_code"]
        if code not in mat_claimed_qty:
            mat_claimed_qty[code] = {
                "material_code": code, "material_name": r["material_name"],
                "used_quantity": 0.0, "original_quantity": 0.0, "inbound_date": "",
            }
        a = mat_claimed_qty[code]
        a["used_quantity"] += r["used_quantity"]
        a["original_quantity"] += r["original_quantity"]
        if str(r["inbound_date"]) > a["inbound_date"]:
            a["inbound_date"] = str(r["inbound_date"])

    sorted_by_qty = sorted(mat_claimed_qty.values(), key=lambda x: x["used_quantity"], reverse=True)
    t2_by_quantity = [
        {
            "rank": idx + 1,
            "material_code": r["material_code"],
            "material_name": r["material_name"],
            "claimed_quantity": round(r["used_quantity"], 2),
            "inbound_quantity": round(r["original_quantity"], 2),
            "inbound_date": r["inbound_date"],
        }
        for idx, r in enumerate(sorted_by_qty[:10])
    ]

    top_kpis = {
        "T1": {
            "key": "T1", "name": "未领用库存 TOP 10（金额）",
            "description": "每月必须输出，责任到项目、跟踪处理。按物料编码聚合所有项目后取 TOP 10。",
            "is_kpi": False, "items": t1_items,
        },
        "T2": {
            "key": "T2", "name": "领用 TOP 10",
            "description": "每月必须输出，用于优化备货、识别关键物资。",
            "is_kpi": False, "by_amount": t2_by_amount, "by_quantity": t2_by_quantity,
        },
    }

    # ================================================================
    #  Step 5: 组装 Summary
    # ================================================================

    all_status_kpis = [
        core_kpis["K1"], core_kpis["K2"], core_kpis["K3"],
        constraint_kpis["K4"], constraint_kpis["K5"],
    ]
    ok_count = sum(1 for k in all_status_kpis if k["status"] == "ok")
    warning_count = sum(1 for k in all_status_kpis if k["status"] == "warning")
    alert_count = sum(1 for k in all_status_kpis if k["status"] == "alert")

    calculated_inventory = total_inbound_amt - total_claimed_amt
    inventory_deviation_pct = round(
        abs(calculated_inventory - total_inventory_amt) / total_inventory_amt * 100, 4
    ) if total_inventory_amt else 0.0

    summary = {
        "update_time": TODAY.strftime("%Y-%m-%d"),
        "data_start_date": min_inbound_date.strftime("%Y-%m-%d") if min_inbound_date else "",
        "data_end_date": max_inbound_date.strftime("%Y-%m-%d") if max_inbound_date else "",
        "date_filter_start": start_date,
        "date_filter_end": end_date,
        "total_inbound_wan": total_inbound_wan,
        "total_claimed_wan": total_claimed_wan,
        "current_inventory_wan": total_inventory_wan,
        "overall_claim_rate": claim_rate_amt,
        "aged_ratio_1y": round(aged_ratio * 100, 2),
        "ok_count": ok_count,
        "warning_count": warning_count,
        "alert_count": alert_count,
        "identity_check": {
            "inbound_minus_claimed_wan": round(calculated_inventory / 10000, 2),
            "actual_inventory_wan": total_inventory_wan,
            "deviation_pct": inventory_deviation_pct,
            "holds": inventory_deviation_pct < 1.0,
        },
    }

    return {
        "summary": summary,
        "core_kpis": core_kpis,
        "constraint_kpis": constraint_kpis,
        "structure_kpis": structure_kpis,
        "top_kpis": top_kpis,
    }
