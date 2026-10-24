"""
领用率双口径对比（WMS × ERP）
==============================
提供「上架月份（cohort）」与「发生月份（flow）」两种口径的月度领用率，
WMS 与 ERP 并列展示，并附当年累计（YTD）汇总。

口径定义：
  - 上架月份（cohort）：WMS 按 putaway_date 归集批次，领用金额为该批次「累计」领用
    （沿用 other_indicators.get_claim_monthly 的既有口径）；
    ERP 无「上架」概念，仍按凭证日期 BLDAT（发生月份）。
  - 发生月份（flow）  ：WMS 入库按 inbound_date、领用按出库完成时间 operation_time
    （change_type=31 + business_type=REQUISITION_ORDER，真领用；30=锁库存 / 37=取消释放
    不计入领用）；ERP 按凭证日期 BLDAT（101+102 入库 / 201+221+Z61 出库）。

金额统一以「万元」返回。
"""

from datetime import date
from typing import Any, Dict, List, Optional

from utils import query, _f
from other_indicators import get_claim_monthly
from erp_inventory import get_erp_claim_monthly


def _wms_flow_monthly() -> Dict:
    """WMS 发生月份流水：返回 {months, inbound_map, claim_map}（金额单位：元）。"""
    # 入库金额：按批次去重后，以 inbound_date 归集（original_quantity × 加权均价）
    inbound_rows = query("""
        WITH b AS (
            SELECT material_code, batch_code,
                   SUM(original_quantity) AS orig_qty,
                   MIN(inbound_date)::date AS inbound_date,
                   CASE WHEN SUM(current_quantity) > 0
                        THEN SUM(current_quantity * unit_price) / SUM(current_quantity)
                        ELSE AVG(unit_price)
                   END AS v_unit_price
            FROM wms_inventory
            WHERE del_flag = '0' AND status = 1
            GROUP BY material_code, batch_code
        )
        SELECT to_char(inbound_date, 'YYYY-MM') AS m,
               SUM(orig_qty * v_unit_price) AS inbound_amt
        FROM b
        WHERE inbound_date IS NOT NULL
        GROUP BY 1
    """)
    # 领用金额：出库完成（change_type=31 真领用）按 operation_time 归集
    claim_rows = query("""
        SELECT to_char(l.operation_time, 'YYYY-MM') AS m,
               SUM(l.change_quantity * i.unit_price) AS claim_amt
        FROM wms_inventory_log l
        JOIN wms_inventory i ON i.id = l.inventory_id
        WHERE l.change_type = 31
          AND l.business_type = 'REQUISITION_ORDER'
          AND l.del_flag = '0'
          AND l.operation_time IS NOT NULL
        GROUP BY 1
    """)
    inbound_map = {r["m"]: _f(r["inbound_amt"]) for r in inbound_rows}
    claim_map = {r["m"]: _f(r["claim_amt"]) for r in claim_rows}
    months = sorted(set(inbound_map) | set(claim_map))
    return {"months": months, "inbound_map": inbound_map, "claim_map": claim_map}


def _erp_monthly_map(year: int) -> Dict:
    """ERP 发生月份：{month: (inbound_wan, outbound_wan, rate)}（金额单位：万元）。"""
    res = get_erp_claim_monthly(year)
    out: Dict[str, tuple] = {}
    for r in res.get("rows", []):
        out[r["doc_month"]] = (r["inbound"], r["outbound"], r["claim_rate"])
    return out


def _merge_rows(months: List[str], wms_inbound_map: Dict, wms_claim_map: Dict,
                erp_map: Dict, divisor: float = 1.0) -> List[Dict]:
    """按月份合并 WMS（元，需除以 divisor）与 ERP（万元），返回月度行列表。"""
    rows = []
    for m in months:
        wi = wms_inbound_map.get(m, 0.0) / divisor
        wc = wms_claim_map.get(m, 0.0) / divisor
        wr = round(wc / wi * 100, 2) if wi else 0.0
        ei, ec, er = erp_map.get(m, (0.0, 0.0, 0.0))
        rows.append({
            "month": m,
            "wms_inbound": round(wi, 2),
            "wms_claimed": round(wc, 2),
            "wms_rate": wr,
            "erp_inbound": round(ei, 2),
            "erp_claimed": round(ec, 2),
            "erp_rate": er,
        })
    return rows


def _summary(rows: List[Dict]) -> Dict:
    """从月度行计算当年累计（YTD）汇总。"""
    wi = sum(r["wms_inbound"] for r in rows)
    wc = sum(r["wms_claimed"] for r in rows)
    ei = sum(r["erp_inbound"] for r in rows)
    ec = sum(r["erp_claimed"] for r in rows)
    return {
        "wms_inbound": round(wi, 2),
        "wms_claimed": round(wc, 2),
        "wms_rate": round(wc / wi * 100, 2) if wi else 0.0,
        "erp_inbound": round(ei, 2),
        "erp_claimed": round(ec, 2),
        "erp_rate": round(ec / ei * 100, 2) if ei else 0.0,
    }


def get_claim_compare(year: Optional[int] = None) -> Dict:
    """
    领用率双口径对比（WMS × ERP）。

    Returns:
        {
            "year": 2026,
            "flow":   {"months", "rows", "summary"},   # 发生月份口径
            "cohort": {"months", "rows", "summary"},   # 上架月份口径
        }
        rows: [{month, wms_inbound, wms_claimed, wms_rate,
                erp_inbound, erp_claimed, erp_rate}]   # 金额单位：万元
    """
    year = year or date.today().year
    erp_map = _erp_monthly_map(year)

    # ---- 发生月份口径（flow）----
    flow = _wms_flow_monthly()
    flow_months = [m for m in sorted(set(flow["months"]) | set(erp_map))
                   if m.startswith(str(year))]
    flow_rows = _merge_rows(flow_months, flow["inbound_map"], flow["claim_map"],
                            erp_map, divisor=10000.0)

    # ---- 上架月份口径（cohort）----
    cohort_res = get_claim_monthly(False)
    cohort_inbound = {d["month"]: d["inbound_amount"] for d in cohort_res.get("data", [])}
    cohort_claim = {d["month"]: d["claimed_amount"] for d in cohort_res.get("data", [])}
    cohort_months = [m for m in cohort_res.get("months", []) if m.startswith(str(year))]
    cohort_rows = _merge_rows(cohort_months, cohort_inbound, cohort_claim,
                              erp_map, divisor=10000.0)

    return {
        "year": year,
        "flow": {"months": flow_months, "rows": flow_rows, "summary": _summary(flow_rows)},
        "cohort": {"months": cohort_months, "rows": cohort_rows, "summary": _summary(cohort_rows)},
    }
