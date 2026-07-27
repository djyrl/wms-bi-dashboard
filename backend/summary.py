from typing import Dict

from utils import _get_inventory_rows, _get_wide_batch_aggregates


def get_summary() -> Dict:
    """汇总统计：入库总额、领用总额、当前库存、记录数"""
    # 汇总金额使用批次级去重聚合（与 claim_indicators 统一口径）
    agg = _get_wide_batch_aggregates(year=None)
    total_inbound = agg.get("total_inbound_amount", 0.0)
    total_claimed = agg.get("total_claimed_amount", 0.0)
    total_inventory = agg.get("total_inventory_amount", 0.0)
    total_qty = agg.get("original_quantity", 0.0)

    # 行级数据用于计算库龄、长库龄占比等
    rows = _get_inventory_rows()
    total_records = len(rows)

    # 加权平均库龄
    weighted_age_sum = sum(
        r["inventory_amount"] * r["age_days"]
        for r in rows
    )
    avg_age = weighted_age_sum / total_inventory if total_inventory else 0

    # 长库龄占比（≥365天）
    aged_amount = sum(
        r["inventory_amount"]
        for r in rows if r["age_days"] >= 365
    )
    aged_ratio = aged_amount / total_inventory if total_inventory else 0

    return {
        "total_inbound_amount": round(total_inbound / 10000, 2),
        "total_claimed_amount": round(total_claimed / 10000, 2),
        "total_inventory_amount": round(total_inventory / 10000, 2),
        "total_inventory_quantity": round(total_qty, 2),
        "total_records": total_records,
        "aged_amount_1y": round(aged_amount / 10000, 2),
        "aged_ratio_1y": round(aged_ratio, 4),
        "avg_age_weighted_days": round(avg_age, 2),
    }
