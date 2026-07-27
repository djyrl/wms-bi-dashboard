from datetime import date
from typing import Dict

from utils import _get_wide_batch_aggregates


def _build_claim_range(agg: Dict[str, float]) -> Dict:
    """由聚合指标构建当年/全部统一的指标区间字典。"""
    total_inbound_amt = agg.get("total_inbound_amount", 0.0)
    total_claimed_amt = agg.get("total_claimed_amount", 0.0)
    total_inbound_qty = agg.get("original_quantity", 0.0)
    total_claimed_qty = agg.get("total_outbound_quantity", 0.0)
    unclaimed_amt = total_inbound_amt - total_claimed_amt

    return {
        "claim_rate_amount": round(total_claimed_amt / total_inbound_amt * 100, 2) if total_inbound_amt else 0.0,
        "claim_rate_quantity": round(total_claimed_qty / total_inbound_qty * 100, 2) if total_inbound_qty else 0.0,
        "unclaimed_amount": round(unclaimed_amt / 10000, 2),
        "unclaimed_amount_ratio": round(unclaimed_amt / total_inbound_amt * 100, 2) if total_inbound_amt else 0.0,
        "total_inbound_amount": round(total_inbound_amt / 10000, 2),
        "total_claimed_amount": round(total_claimed_amt / 10000, 2),
        "total_inbound_quantity": round(total_inbound_qty, 2),
        "total_claimed_quantity": round(total_claimed_qty, 2),
    }


def get_claim_indicators() -> Dict:
    """
    1. 采购领用率（金额）
    2. 采购领用率（数量）
    3. 未领用采购金额
    4. 未领用采购占比（金额）

    以上 4 个指标均按「当年」与「全部」两个时间区间拆分。
    数据来源：v_project_inventory_wide，按物理批次去重后聚合。
    当年：按 inbound_date 所在自然年统计；NULL 日期不计入当年。
    """
    current_year = date.today().year
    all_agg = _get_wide_batch_aggregates(year=None)
    year_agg = _get_wide_batch_aggregates(year=current_year)

    return {
        "current_year": current_year,
        "year_start": f"{current_year}-01-01",
        "year_end": f"{current_year}-12-31",
        "all": _build_claim_range(all_agg),
        "year": _build_claim_range(year_agg),
    }
