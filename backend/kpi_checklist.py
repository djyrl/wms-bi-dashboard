"""
采购库存 BI — KPI 考核清单模块
===============================
计算 KPI 考核清单的全部指标（K1-K9 + T1-T2）。

═══════════════════════════════════════════════════════════════════════════
数据来源（完全统一）：
  所有数据均来自 v_project_inventory_wide 视图 + utils 公共模块，
  不再重复编写去重 SQL。

  数据获取层次：
    1. _get_wide_batch_aggregates(year=None) → 批次级总额（入库/领用/库存）
    2. _get_batch_rows()                     → 批次级明细（库龄结构、加权平均）
    3. _get_inventory_rows()                 → 项目级明细（TOP排行等）
    4. _get_wide_structure_aggregates()      → 项目/采购人库存占比
    5. get_by_project()                      → K8 项目维度分析（来自 dimension_indicators）
    6. get_by_purchaser()                    → K9 采购人维度分析（来自 dimension_indicators）

═══════════════════════════════════════════════════════════════════════════
指标结构：
  第一类 核心考核指标 K1-K3:
    K1 - 采购领用率（金额）
    K2 - 当前库存金额
    K3 - 长库龄库存金额占比（≥1年）

  第二类 约束类指标 K4-K5:
    K4 - 未领用采购金额
    K5 - 项目未消耗库存

  第三类 结构分析指标 K6-K9:
    K6 - 库存结构分析（项目占比、采购人占比）
    K7 - 时间分析（平均库龄、未动用天数、库龄结构）
    K8 - 项目分析
    K9 - 采购人分析

  第四类 TOP 指标 T1-T2（不纳入考核）:
    T1 - 未领用库存 TOP 10（金额）
    T2 - 领用 TOP 10（金额 + 数量）
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
#  辅助：状态判定
# ================================================================

def _status_for_rate(rate: float, target: float, direction: str = "up") -> str:
    """
    根据达成率和目标值判定指标状态。

    Args:
        rate:      当前达成率（如 75 表示 75%）
        target:    目标值（如 80 表示 ≥80%）
        direction: "up"=越高越好, "down"=越低越好

    Returns:
        "ok" | "warning" | "alert"
          - ok:      达成（rate ≥ target 或 rate ≤ target）
          - warning: 接近目标（差值 ≤ 15%）
          - alert:   未达成
    """
    if direction == "up":
        if rate >= target:
            return "ok"
        elif rate >= target * 0.85:  # 达成 85% 以上视为 warning
            return "warning"
        else:
            return "alert"
    else:
        if rate <= target:
            return "ok"
        elif rate <= target * 1.15:  # 超出 ≤ 15% 视为 warning
            return "warning"
        else:
            return "alert"


# ================================================================
#  主入口：一次性拉取数据 + 内存计算全部指标
# ================================================================

def get_kpi_checklist() -> Dict[str, Any]:
    """
    获取 KPI 考核清单（完整版）。

    分四步完成：
      Step 1 — 拉取数据（6 个数据来源）
      Step 2 — 内存计算核心指标 K1-K5
      Step 3 — 组装结构指标 K6-K9（引用 dimension_indicators）
      Step 4 — 组装 TOP 指标 T1-T2

    Returns:
        包含 summary, core_kpis, constraint_kpis, structure_kpis, top_kpis 的完整字典
    """

    # ================================================================
    #  Step 1: 拉取数据
    # ================================================================
    # 1a. 批次级总额（入库/领用/库存/数量）— 绝对权威值
    agg = _get_wide_batch_aggregates(year=None)
    total_inbound_amt = agg["total_inbound_amount"]        # 入库总额（元）
    total_claimed_amt = agg["total_claimed_amount"]        # 领用总额（元）
    total_inventory_amt = agg["total_inventory_amount"]    # 库存总额（元）
    total_inbound_qty = agg["original_quantity"]           # 入库总数量
    total_outbound_qty = agg["total_outbound_quantity"]    # 出库总数量

    # 1b. 批次级明细（用于库龄结构和加权计算）
    batch_rows = _get_batch_rows()

    # 1c. 项目级明细（用于 TOP 排行、未动用天数等）
    inv_rows = _get_inventory_rows()

    # 1d. 库存结构（项目/采购人占比）— 用于 K6
    structure_data = _get_wide_structure_aggregates()

    # 1e. 项目维度分析 — 用于 K8（所有项目）
    k8_projects = get_by_project()

    # 1e-bis. 特定类型项目（Q类）— 用于 K5 项目未消耗库存
    k5_projects = get_by_project(owner_project_type='Q')

    # 1f. 采购人维度分析 — 用于 K9
    k9_purchasers = get_by_purchaser()

    # ================================================================
    #  Step 2: 内存计算核心指标 K1-K5
    # ================================================================

    # ── 2a. 库龄结构 & 加权平均库龄（从批次级明细）──
    # 库龄段定义
    AGE_BUCKETS: List[Tuple[str, int, int]] = [
        ("≤1年", 0, 365),
        ("1~3年", 365, 1095),
        ("3~5年", 1095, 1825),
        ("≥5年", 1825, 999999),
    ]
    age_amt = {label: 0.0 for label, _, _ in AGE_BUCKETS}  # 各段金额
    age_cnt = {label: 0 for label, _, _ in AGE_BUCKETS}     # 各段批次数

    age_weighted_sum = 0.0   # Σ(库存金额 × 库龄)
    aged_365_amt = 0.0       # 库龄 ≥ 365 天的库存金额

    for r in batch_rows:
        amt = r["inventory_amount"]
        age = r["age_days"]

        # 加权库龄累积
        age_weighted_sum += amt * age
        # 长库龄（≥1年）累积
        if age >= 365:
            aged_365_amt += amt

        # 归入对应库龄段
        for label, lo, hi in AGE_BUCKETS:
            if lo <= age < hi:
                age_amt[label] += amt
                age_cnt[label] += 1
                break

    # ── 2b. 派生指标 ──

    # 综合领用率（金额）= 领用 / 入库 × 100%
    claim_rate_amt = round(total_claimed_amt / total_inbound_amt * 100, 2) \
        if total_inbound_amt else 0.0
    # 数量领用率
    claim_rate_qty = round(total_outbound_qty / total_inbound_qty * 100, 2) \
        if total_inbound_qty else 0.0
    # 未领用金额（万元）= (入库 - 领用) / 10000
    # 恒等式下 ≈ 当前库存金额
    unclaimed_amt = round((total_inbound_amt - total_claimed_amt) / 10000, 2)
    # 万元转换
    total_inbound_wan = round(total_inbound_amt / 10000, 2)
    total_claimed_wan = round(total_claimed_amt / 10000, 2)
    total_inventory_wan = round(total_inventory_amt / 10000, 2)
    # 未领用占比（%）
    unclaimed_ratio = round(
        (total_inbound_amt - total_claimed_amt) / total_inbound_amt * 100, 2
    ) if total_inbound_amt else 0.0

    # ── 库龄结构（按段）──
    # 使用 age_structure 内部总和作为分母，确保各段占比之和 = 100%
    age_total = sum(age_amt.values())
    age_structure = []
    aged_365_ratio = 0.0  # 长库龄（≥1年）总占比
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

    # 加权平均库龄 = Σ(金额 × 库龄) / Σ(金额)
    avg_age_days = round(age_weighted_sum / total_inventory_amt, 2) \
        if total_inventory_amt else 0.0
    # 长库龄占比（比例形式）
    aged_ratio = round(aged_365_ratio, 4)

    # ── 2c. 未动用天数（从项目级明细）──
    # 「未动用」定义：claimed_amount = 0 且 current_quantity > 0
    unused_weighted = 0.0   # Σ(未动用库存金额 × 库龄)
    unused_total_amt = 0.0  # 未动用库存总金额
    # 库存总数量 = 批次级当前数量合计（与 WMS 库存口径一致）。
    # 勿在 inv_rows（项目台账）上累加：部分批次无台账行或台账滞后，会比库存行总额偏小
    total_inventory_qty = sum(r["current_quantity"] for r in batch_rows)
    min_inbound_date = None
    max_inbound_date = None
    max_outbound_time = None   # 最后出库时间（用于「数据截至」取较新者）

    for r in inv_rows:
        inventory = r["inventory_amount"]
        age = r["age_days"]

        # 日期范围
        d = r.get("inbound_date")
        if d is not None:
            if hasattr(d, 'date'):
                d = d.date()
            if min_inbound_date is None or d < min_inbound_date:
                min_inbound_date = d
            if max_inbound_date is None or d > max_inbound_date:
                max_inbound_date = d

        # 最后出库时间（批次级，可能为 None）
        ot = r.get("last_outbound_time")
        if ot is not None:
            if hasattr(ot, 'date'):
                ot = ot.date()
            if max_outbound_time is None or ot > max_outbound_time:
                max_outbound_time = ot

        # 未动用：从未领用过且有库存
        if r["claimed_amount"] == 0 and r["current_quantity"] > 0:
            unused_weighted += inventory * age
            unused_total_amt += inventory

    # 未动用天数 = 金额加权平均未动用库龄
    unused_days = round(unused_weighted / unused_total_amt, 2) \
        if unused_total_amt else 0.0

    # ================================================================
    #  Step 3: 组装 KPI 指标
    # ================================================================

    # ── K1: 采购领用率（金额）──
    K1_status = _status_for_rate(claim_rate_amt, 60, "up")
    core_kpis = {
        "K1": {
            "key": "K1",
            "name": "采购领用率（金额）",
            "formula": "领用金额 / 入库金额 × 100%",
            "value": claim_rate_amt,
            "unit": "%",
            "target": "≥60%",
            "target_value": 60,
            "direction": "up",
            "status": K1_status,
            "detail": {
                "claimed_amount_wan": total_claimed_wan,
                "inbound_amount_wan": total_inbound_wan,
                "unclaimed_amount_wan": unclaimed_amt,
                "claim_rate_quantity": claim_rate_qty,
                # 恒等式说明：inbound - claimed ≈ inventory
                "note": "未领用金额 ≈ 当前库存金额（恒等式 inbound - claimed ≈ inventory）",
            },
        },

        # ── K2: 当前库存金额 ──
        "K2": {
            "key": "K2",
            "name": "当前库存金额",
            "formula": "SUM(current_quantity × unit_price) = v_total_price",
            "value": total_inventory_wan,
            "unit": "万元",
            "target": "控制上限，同比下降",
            "target_value": None,
            "direction": "down",
            "status": "info",
            "detail": {
                "inventory_quantity": round(total_inventory_qty, 2),
                "batch_count": len(batch_rows),
                "note": "v_total_price 按物理批次去重后求和，与 summary 模块口径一致",
            },
        },

        # ── K3: 长库龄库存金额占比（≥1年）──
        "K3": {
            "key": "K3",
            "name": "长库龄库存金额占比（≥1年）",
            "formula": "库龄≥365天的库存金额 / 总库存金额 × 100%",
            "value": round(aged_ratio * 100, 2),
            "unit": "%",
            "target": "逐年下降",
            "target_value": None,
            "direction": "down",
            # 长库龄 > 15% 视为 warning
            "status": "warning" if aged_ratio > 0.15 else "ok",
            "detail": {
                # 所有 ≥1 年的库龄段金额汇总（万元）
                "aged_amount_1y_wan": round(sum(
                    age_amt[label] for label, lo, _ in AGE_BUCKETS if lo >= 365
                ) / 10000, 2),
                "avg_age_weighted_days": avg_age_days,
                "age_structure": age_structure,
                "note": "库龄 = CURRENT_DATE - COALESCE(inbound_date, create_date)，在 inv_agg CTE 中用 MIN(inbound_date) 取批次最早日期",
            },
        },
    }

    # ── K4: 未领用采购金额 ──
    K4_status = "warning" if unclaimed_ratio > 30 else "ok"
    constraint_kpis = {
        "K4": {
            "key": "K4",
            "name": "未领用采购金额",
            "formula": "入库金额 - 领用金额",
            "value": unclaimed_amt,
            "unit": "万元",
            "target": "控制新增库存",
            "target_value": None,
            "direction": "down",
            "status": K4_status,
            "detail": {
                "unclaimed_amount_wan": unclaimed_amt,
                "unclaimed_ratio": unclaimed_ratio,
                "total_inbound_wan": total_inbound_wan,
                "total_claimed_wan": total_claimed_wan,
                "note": "未领用 = inbound - claimed，恒等式下 ≈ inventory。两者的差异见 identity_check",
            },
        },

        # ── K5: 项目未消耗库存 ──
        # 使用特定类型（owner_project_type='Q'）的项目数据
        "K5": {
            "key": "K5",
            "name": "项目未消耗库存",
            "formula": "按项目汇总 inventory_amount（仅 owner_project_type='Q'，批次去重 × project_ratio 分配）",
            "value": round(sum(p["unclaimed_amount"] for p in k5_projects) / 10000, 2),
            "unit": "万元",
            "target": "项目采购约束（A修、技改等特定范围）",
            "target_value": None,
            "direction": "down",
            "status": "info",
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
                "note": f"项目未消耗库存 = Σ(owner_project_type='Q' 项目的 inventory_amount)，数据来自 dimension_indicators.get_by_project(owner_project_type='Q')，共 {len(k5_projects)} 个Q类项目",
            },
        },
    }

    # ── K6: 库存结构分析（项目占比、采购人占比）──
    project_rows = structure_data["project_rows"]
    purchaser_rows = structure_data["purchaser_rows"]
    structure_kpis = {
        "K6": {
            "key": "K6",
            "name": "库存结构分析",
            "description": "项目库存占比 TOP 10、采购人库存占比 TOP 10",
            "project_ratios": [
                {
                    "project_code": p["owner_project_code"],
                    "project_name": p["project_name"] or "",
                    "project_submitter": p.get("project_submitter") or "",
                    "project_contact": p.get("project_contact") or "",
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
            "note": "金额来源于 _get_wide_structure_aggregates()：批次去重 × project_ratio",
        },

        # ── K7: 时间分析 ──
        "K7": {
            "key": "K7",
            "name": "时间分析",
            "description": "平均库龄、未动用天数、库龄结构",
            "avg_age_weighted_days": avg_age_days,
            "unused_days": unused_days,
            "age_structure": age_structure,
            "aged_ratio_1y": round(aged_ratio * 100, 2),
            "note": "未动用天数 = Σ(未动用库存金额 × 库龄) / Σ(未动用库存金额)，未动用定义为 claimed_amount=0 且 current_quantity>0",
        },

        # ── K8: 项目分析 ──
        "K8": {
            "key": "K8",
            "name": "项目分析",
            "description": "回答：哪个项目带来库存 | 数据来源：dimension_indicators.get_by_project()",
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

        # ── K9: 采购人分析 ──
        "K9": {
            "key": "K9",
            "name": "采购人分析",
            "description": "采购人领用率、未消耗库存、库龄 | 数据来源：dimension_indicators.get_by_purchaser()",
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
    #  Step 4: TOP 指标 T1-T2（从项目级明细 inv_rows 计算）
    # ================================================================

    # ── T1: 未领用库存 TOP 10（按 inventory_amount 降序）──
    # inventory_amount 是项目分配后的值，但 TOP 需要的是批次总额
    # 这里使用 inv_rows 按 material_code 聚合，对同一物料的多个项目行求和
    mat_agg: Dict[str, Dict] = {}
    for r in inv_rows:
        code = r["material_code"]
        if code not in mat_agg:
            mat_agg[code] = {
                "material_code": code,
                "material_name": r["material_name"],
                "inventory_amount": 0.0,
                "current_quantity": 0.0,
                "unit": r["unit"],
                "age_days": 0,
                "age_weight": 0.0,
                "project_code": "",
                "project_name": "",
                "purchaser_name": "",
            }
        a = mat_agg[code]
        a["inventory_amount"] += r["inventory_amount"]
        a["current_quantity"] += r["current_quantity"]
        a["age_weight"] += r["inventory_amount"] * r["age_days"]
        # 取库龄最大的项目信息
        if r["age_days"] > a["age_days"]:
            a["age_days"] = int(r["age_days"])
            a["project_code"] = r.get("project_code", "")
            a["project_name"] = r.get("project_name", "")
            a["purchaser_name"] = r.get("purchaser_name", "")

    sorted_by_inventory = sorted(mat_agg.values(),
                                 key=lambda x: x["inventory_amount"], reverse=True)
    top10_unclaimed = sorted_by_inventory[:10]

    t1_items = []
    for idx, r in enumerate(top10_unclaimed):
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

    # ── T2: 领用 TOP 10 ──
    # T2 分两组：按领用金额 + 按领用数量

    # 按金额聚合
    mat_claimed_amt: Dict[str, Dict] = {}
    for r in inv_rows:
        code = r["material_code"]
        if code not in mat_claimed_amt:
            mat_claimed_amt[code] = {
                "material_code": code,
                "material_name": r["material_name"],
                "claimed_amount": 0.0,
                "inbound_amount": 0.0,
                "inbound_date": "",
            }
        a = mat_claimed_amt[code]
        a["claimed_amount"] += r["claimed_amount"]
        a["inbound_amount"] += r["inbound_amount"]
        if str(r["inbound_date"]) > a["inbound_date"]:
            a["inbound_date"] = str(r["inbound_date"])

    sorted_by_claimed = sorted(mat_claimed_amt.values(),
                               key=lambda x: x["claimed_amount"], reverse=True)
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

    # 按数量聚合
    mat_claimed_qty: Dict[str, Dict] = {}
    for r in inv_rows:
        code = r["material_code"]
        if code not in mat_claimed_qty:
            mat_claimed_qty[code] = {
                "material_code": code,
                "material_name": r["material_name"],
                "used_quantity": 0.0,
                "original_quantity": 0.0,
                "inbound_date": "",
            }
        a = mat_claimed_qty[code]
        a["used_quantity"] += r["used_quantity"]
        a["original_quantity"] += r["original_quantity"]
        if str(r["inbound_date"]) > a["inbound_date"]:
            a["inbound_date"] = str(r["inbound_date"])

    sorted_by_qty = sorted(mat_claimed_qty.values(),
                           key=lambda x: x["used_quantity"], reverse=True)
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
            "key": "T1",
            "name": "未领用库存 TOP 10（金额）",
            "description": "每月必须输出，责任到项目、跟踪处理。按物料编码聚合所有项目后取 TOP 10。",
            "is_kpi": False,
            "items": t1_items,
        },
        "T2": {
            "key": "T2",
            "name": "领用 TOP 10",
            "description": "每月必须输出，用于优化备货、识别关键物资。",
            "is_kpi": False,
            "by_amount": t2_by_amount,
            "by_quantity": t2_by_quantity,
        },
    }

    # ================================================================
    #  Step 5: 组装 Summary
    # ================================================================

    # 统计 K1-K5 的状态分布
    all_status_kpis = [
        core_kpis["K1"], core_kpis["K2"], core_kpis["K3"],
        constraint_kpis["K4"], constraint_kpis["K5"],
    ]
    ok_count = sum(1 for k in all_status_kpis if k["status"] == "ok")
    warning_count = sum(1 for k in all_status_kpis if k["status"] == "warning")
    alert_count = sum(1 for k in all_status_kpis if k["status"] == "alert")

    # 会计恒等式校验
    calculated_inventory = total_inbound_amt - total_claimed_amt
    inventory_deviation_pct = round(
        abs(calculated_inventory - total_inventory_amt) / total_inventory_amt * 100, 4
    ) if total_inventory_amt else 0.0

    # 数据截至：取「最晚入库日期」与「最后出库时间」中较新者
    data_end = max_inbound_date
    if max_outbound_time is not None and (data_end is None or max_outbound_time > data_end):
        data_end = max_outbound_time

    summary = {
        "update_time": date.today().strftime("%Y-%m-%d"),
        # 数据覆盖日期范围
        "data_start_date": min_inbound_date.strftime("%Y-%m-%d") if min_inbound_date else "",
        "data_end_date": data_end.strftime("%Y-%m-%d") if data_end else "",
        # 核心汇总（万元）
        "total_inbound_wan": total_inbound_wan,
        "total_claimed_wan": total_claimed_wan,
        "current_inventory_wan": total_inventory_wan,
        # 综合领用率
        "overall_claim_rate": claim_rate_amt,
        # 长库龄占比
        "aged_ratio_1y": round(aged_ratio * 100, 2),
        # 考核状态统计
        "ok_count": ok_count,
        "warning_count": warning_count,
        "alert_count": alert_count,
        # 恒等式校验
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
