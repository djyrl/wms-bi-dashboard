"""
采购库存 BI Dashboard — 模拟数据生成
=====================================
事实表: procurement_batch (采购批次)
维度表: dim_material, dim_project, dim_purchaser
基于 2026-07-04 为「当前日期」生成数据
"""

import random
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple

random.seed(42)

TODAY = date(2026, 7, 4)

# ================================================================
# 维度表
# ================================================================

DIM_MATERIAL = [
    {"id": 1, "name": "碳钢无缝管", "category": "钢材", "unit": "吨"},
    {"id": 2, "name": "铜芯电力电缆", "category": "电缆", "unit": "米"},
    {"id": 3, "name": "不锈钢球阀", "category": "阀门", "unit": "个"},
    {"id": 4, "name": "离心泵", "category": "泵类", "unit": "台"},
    {"id": 5, "name": "压力变送器", "category": "仪表", "unit": "台"},
    {"id": 6, "name": "HDPE双壁波纹管", "category": "管道", "unit": "米"},
    {"id": 7, "name": "低压开关柜", "category": "电气设备", "unit": "台"},
    {"id": 8, "name": "防静电工作服", "category": "劳保用品", "unit": "套"},
]

DIM_PROJECT = [
    {"id": 1, "name": "东海炼化一体化项目", "department": "炼化事业部"},
    {"id": 2, "name": "西部天然气管道工程", "department": "管道事业部"},
    {"id": 3, "name": "南方电网升级改造", "department": "电力事业部"},
    {"id": 4, "name": "北方供热管网扩建", "department": "市政事业部"},
    {"id": 5, "name": "长江水处理厂建设", "department": "水务事业部"},
    {"id": 6, "name": "滨海码头仓储工程", "department": "物流事业部"},
]

DIM_PURCHASER = [
    {"id": 1, "name": "张建国", "department": "采购一部"},
    {"id": 2, "name": "李明远", "department": "采购一部"},
    {"id": 3, "name": "王海涛", "department": "采购二部"},
    {"id": 4, "name": "陈晓峰", "department": "采购二部"},
    {"id": 5, "name": "赵永强", "department": "采购三部"},
]


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


# ================================================================
# 生成 80 条采购批次
# ================================================================

def _generate_batches() -> List[Dict]:
    presets = [
        # ---- 高领用率 (>85%) 批次 (2024-2025) ----
        *[(random.randint(1, 8), random.randint(1, 6), random.randint(1, 5),
           date(2024, 6, 1), date(2025, 12, 31), (20, 200), (0.85, 1.0), random.randint(100, 2000))
          for _ in range(30)],
        # ---- 中等领用率 (50-85%) 批次 (2022-2024) ----
        *[(random.randint(1, 8), random.randint(1, 6), random.randint(1, 5),
           date(2022, 1, 1), date(2024, 5, 31), (30, 300), (0.50, 0.85), random.randint(200, 3000))
          for _ in range(20)],
        # ---- 低领用率 (<50%) 旧批次 (2020-2022)，制造长库龄 ----
        *[(random.randint(1, 8), random.randint(1, 6), random.randint(1, 5),
           date(2019, 1, 1), date(2022, 6, 30), (50, 500), (0.05, 0.50), random.randint(500, 5000))
          for _ in range(15)],
        # ---- 极低领用 / 未领用，形成历史沉淀 ----
        *[(random.randint(1, 5), random.randint(1, 6), random.randint(1, 5),
           date(2018, 1, 1), date(2021, 12, 31), (80, 500), (0.0, 0.15), random.randint(1000, 8000))
          for _ in range(10)],
        # ---- 额外混合 ----
        *[(random.randint(1, 8), random.randint(1, 6), random.randint(1, 5),
           date(2020, 1, 1), date(2025, 12, 31), (10, 300), (0.20, 0.95), random.randint(50, 4000))
          for _ in range(5)],
    ]

    batches = []
    for i, preset in enumerate(presets[:80]):
        mat_id, proj_id, pur_id, start_d, end_d, amt_range, claim_range, qty_base = preset
        inbound_date = _random_date(start_d, end_d)
        inbound_amount = round(random.uniform(*amt_range) * 10000, 2)
        claim_rate = round(random.uniform(*claim_range), 2)
        claimed_amount = round(inbound_amount * claim_rate, 2)
        inventory_amount = round(inbound_amount - claimed_amount, 2)
        qty_base_actual = qty_base
        claimed_qty = round(qty_base_actual * claim_rate, 2)
        inventory_qty = round(qty_base_actual - claimed_qty, 2)
        age_days = (TODAY - inbound_date).days

        batches.append({
            "id": i + 1,
            "batch_no": f"PO-{inbound_date.year}-{i+1:04d}",
            "material_id": mat_id,
            "project_id": proj_id,
            "purchaser_id": pur_id,
            "inbound_date": inbound_date.isoformat(),
            "inbound_amount": inbound_amount,
            "inbound_quantity": qty_base_actual,
            "claimed_amount": claimed_amount,
            "claimed_quantity": claimed_qty,
            "inventory_amount": inventory_amount,
            "inventory_quantity": inventory_qty,
            "claim_rate_amount": round(claim_rate, 4),
            "claim_rate_quantity": round(claim_rate, 4),
            "inventory_age_days": age_days,
        })

    random.shuffle(batches)
    for i, b in enumerate(batches):
        b["id"] = i + 1
        b["batch_no"] = f"PO-{b['inbound_date'][:4]}-{i+1:04d}"
    return batches


BATCHES = _generate_batches()
TOTALS = {
    "inbound_amount": sum(b["inbound_amount"] for b in BATCHES),
    "inbound_quantity": sum(b["inbound_quantity"] for b in BATCHES),
    "claimed_amount": sum(b["claimed_amount"] for b in BATCHES),
    "claimed_quantity": sum(b["claimed_quantity"] for b in BATCHES),
    "inventory_amount": sum(b["inventory_amount"] for b in BATCHES),
    "inventory_quantity": sum(b["inventory_quantity"] for b in BATCHES),
}


# ================================================================
# 辅助函数
# ================================================================

def _mat(b: dict) -> dict:
    m = next(m for m in DIM_MATERIAL if m["id"] == b["material_id"])
    return {"id": m["id"], "name": m["name"], "category": m["category"], "unit": m["unit"]}

def _proj(b: dict) -> dict:
    p = next(p for p in DIM_PROJECT if p["id"] == b["project_id"])
    return {"id": p["id"], "name": p["name"], "department": p["department"]}

def _pur(b: dict) -> dict:
    p = next(p for p in DIM_PURCHASER if p["id"] == b["purchaser_id"])
    return {"id": p["id"], "name": p["name"], "department": p["department"]}

def _weighted_avg_age(batches: List[Dict]) -> float:
    total = sum(b["inventory_amount"] for b in batches)
    if total == 0:
        return 0
    return sum(b["inventory_amount"] * b["inventory_age_days"] for b in batches) / total

def _enrich(batch: dict) -> dict:
    return {**batch, "material": _mat(batch), "project": _proj(batch), "purchaser": _pur(batch)}


# ================================================================
# API 数据函数
# ================================================================

def get_summary() -> dict:
    aged = [b for b in BATCHES if b["inventory_age_days"] >= 365]
    aged_amt = sum(b["inventory_amount"] for b in aged)
    ti = TOTALS
    return {
        "total_inbound_amount": round(ti["inbound_amount"], 2),
        "total_claimed_amount": round(ti["claimed_amount"], 2),
        "total_inventory_amount": round(ti["inventory_amount"], 2),
        "overall_claim_rate": round(ti["claimed_amount"] / ti["inbound_amount"] * 100, 2) if ti["inbound_amount"] else 0,
        "aged_ratio_1y": round(aged_amt / ti["inventory_amount"] * 100, 2) if ti["inventory_amount"] else 0,
        "avg_age_weighted_days": round(_weighted_avg_age(BATCHES), 1),
        "batch_count": len(BATCHES),
        "total_inventory_quantity": round(ti["inventory_quantity"], 2),
    }


def get_claim_indicators() -> dict:
    ti = TOTALS
    unclaimed_amt = round(ti["inbound_amount"] - ti["claimed_amount"], 2)
    unclaimed_qty = round(ti["inbound_quantity"] - ti["claimed_quantity"], 2)
    return {
        "claim_rate_amount": round(ti["claimed_amount"] / ti["inbound_amount"] * 100, 2) if ti["inbound_amount"] else 0,
        "claim_rate_quantity": round(ti["claimed_quantity"] / ti["inbound_quantity"] * 100, 2) if ti["inbound_quantity"] else 0,
        "unclaimed_amount": unclaimed_amt,
        "unclaimed_quantity": unclaimed_qty,
        "unclaimed_amount_ratio": round(unclaimed_amt / ti["inbound_amount"] * 100, 2) if ti["inbound_amount"] else 0,
        "total_inbound_amount": round(ti["inbound_amount"], 2),
        "total_claimed_amount": round(ti["claimed_amount"], 2),
    }


def get_structure_indicators() -> dict:
    ti = TOTALS
    project_ratios = []
    for p in DIM_PROJECT:
        pb = [b for b in BATCHES if b["project_id"] == p["id"]]
        amt = round(sum(b["inventory_amount"] for b in pb), 2)
        project_ratios.append({
            "project_id": p["id"], "project_name": p["name"],
            "inventory_amount": amt,
            "ratio": round(amt / ti["inventory_amount"] * 100, 2) if ti["inventory_amount"] else 0,
            "batch_count": len(pb),
        })
    purchaser_ratios = []
    for p in DIM_PURCHASER:
        pb = [b for b in BATCHES if b["purchaser_id"] == p["id"]]
        amt = round(sum(b["inventory_amount"] for b in pb), 2)
        purchaser_ratios.append({
            "purchaser_id": p["id"], "purchaser_name": p["name"],
            "inventory_amount": amt,
            "ratio": round(amt / ti["inventory_amount"] * 100, 2) if ti["inventory_amount"] else 0,
            "batch_count": len(pb),
        })
    return {
        "current_inventory_amount": round(ti["inventory_amount"], 2),
        "current_inventory_quantity": round(ti["inventory_quantity"], 2),
        "project_ratios": project_ratios,
        "purchaser_ratios": purchaser_ratios,
    }


def get_time_indicators(age_ranges: List[Tuple[int, int, str]] = None) -> Dict:
    if age_ranges is None:
        age_ranges = [(0, 365, "≤1年"), (365, 1095, "1~3年"), (1095, 1825, "3~5年"), (1825, 99999, "≥5年")]
    ti = TOTALS
    aged = [b for b in BATCHES if b["inventory_age_days"] >= 365]
    aged_amt = sum(b["inventory_amount"] for b in aged)
    structure = []
    for lo, hi, label in age_ranges:
        layer = [b for b in BATCHES if lo <= b["inventory_age_days"] < hi]
        amt = round(sum(b["inventory_amount"] for b in layer), 2)
        structure.append({
            "range": label, "amount": amt,
            "ratio": round(amt / ti["inventory_amount"] * 100, 2) if ti["inventory_amount"] else 0,
            "batch_count": len(layer),
        })
    return {
        "aged_ratio_1y": round(aged_amt / ti["inventory_amount"] * 100, 2) if ti["inventory_amount"] else 0,
        "aged_amount_1y": round(aged_amt, 2),
        "age_structure": structure,
        "avg_age_weighted_days": round(_weighted_avg_age(BATCHES), 1),
    }


def get_age_layers(min_amount: float = 0, min_age: int = 0, max_age: int = None) -> List[Dict]:
    result = []
    for b in BATCHES:
        if b["inventory_amount"] < min_amount: continue
        if b["inventory_age_days"] < min_age: continue
        if max_age is not None and b["inventory_age_days"] > max_age: continue
        result.append(_enrich(b))
    result.sort(key=lambda x: x["inventory_amount"], reverse=True)
    return result


def get_by_project() -> List[Dict]:
    result = []
    for p in DIM_PROJECT:
        pb = [b for b in BATCHES if b["project_id"] == p["id"]]
        inbound = sum(b["inbound_amount"] for b in pb)
        claimed = sum(b["claimed_amount"] for b in pb)
        result.append({
            "project_id": p["id"], "project_name": p["name"], "department": p["department"],
            "inbound_amount": round(inbound, 2), "claimed_amount": round(claimed, 2),
            "unclaimed_amount": round(inbound - claimed, 2),
            "claim_rate": round(claimed / inbound * 100, 2) if inbound else 0,
            "avg_age_days": round(_weighted_avg_age(pb), 1),
            "batch_count": len(pb),
        })
    result.sort(key=lambda x: x["unclaimed_amount"], reverse=True)
    return result


def get_by_purchaser() -> List[Dict]:
    result = []
    for pur in DIM_PURCHASER:
        pb = [b for b in BATCHES if b["purchaser_id"] == pur["id"]]
        inbound = sum(b["inbound_amount"] for b in pb)
        claimed = sum(b["claimed_amount"] for b in pb)
        result.append({
            "purchaser_id": pur["id"], "purchaser_name": pur["name"], "department": pur["department"],
            "inbound_amount": round(inbound, 2), "claimed_amount": round(claimed, 2),
            "unclaimed_amount": round(inbound - claimed, 2),
            "claim_rate": round(claimed / inbound * 100, 2) if inbound else 0,
            "avg_age_days": round(_weighted_avg_age(pb), 1),
            "batch_count": len(pb),
        })
    result.sort(key=lambda x: x["unclaimed_amount"], reverse=True)
    return result


def get_top_unclaimed_amount(limit=10) -> List[Dict]:
    return [_enrich(b) for b in sorted(BATCHES, key=lambda b: b["inventory_amount"], reverse=True)[:limit]]


def get_top_unclaimed_quantity(limit=10) -> List[Dict]:
    return [_enrich(b) for b in sorted(BATCHES, key=lambda b: b["inventory_quantity"], reverse=True)[:limit]]


def get_top_claimed_amount(limit=10) -> List[Dict]:
    return [_enrich(b) for b in sorted(BATCHES, key=lambda b: b["claimed_amount"], reverse=True)[:limit]]


def get_top_claimed_quantity(limit=10) -> List[Dict]:
    return [_enrich(b) for b in sorted(BATCHES, key=lambda b: b["claimed_quantity"], reverse=True)[:limit]]


def get_dimensions(dim_type: str) -> List[Dict]:
    return {"materials": DIM_MATERIAL, "projects": DIM_PROJECT, "purchasers": DIM_PURCHASER}.get(dim_type, [])


def drill_batches(
    project_id: int = None, material_id: int = None, purchaser_id: int = None,
    age_min: int = None, age_max: int = None,
) -> List[Dict]:
    result = BATCHES
    if project_id is not None: result = [b for b in result if b["project_id"] == project_id]
    if material_id is not None: result = [b for b in result if b["material_id"] == material_id]
    if purchaser_id is not None: result = [b for b in result if b["purchaser_id"] == purchaser_id]
    if age_min is not None: result = [b for b in result if b["inventory_age_days"] >= age_min]
    if age_max is not None: result = [b for b in result if b["inventory_age_days"] <= age_max]
    enriched = [_enrich(b) for b in result]
    enriched.sort(key=lambda x: x["inventory_amount"], reverse=True)
    return enriched
