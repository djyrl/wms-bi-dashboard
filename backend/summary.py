"""
采购库存 BI — KPI 总览模块
==========================
计算核心汇总指标：入库总额、领用总额、当前库存金额、加权平均库龄、综合领用率、
长库龄占比、批次数量。

数据来源：v_project_inventory_wide → _get_batch_rows()（批次去重明细）。
所有金额基于 utils.py 中的计算标准：
  - 入库金额 = original_quantity × v_unit_price
  - 领用金额 = total_outbound_quantity × v_unit_price
  - 库存金额 = v_total_price = SUM(current_quantity × unit_price)

会计恒等式：inbound ≈ claimed + inventory
前提：dim_outbound_log_cache 从 wms_inventory 通过 wms_inventory_log 关联填充，
      original_quantity ≈ current_quantity + total_outbound_quantity
"""

from typing import Dict

from utils import _get_batch_rows


def get_summary() -> Dict:
    """
    获取 KPI 总览。

    一次查询所有批次数据，在 Python 内存中聚合，避免重复扫描视图。

    返回字典包含以下字段：
      - total_inbound_amount:     入库总额（万元）
      - total_claimed_amount:     领用总额（万元）
      - total_inventory_amount:   当前库存金额（万元）
      - total_inventory_quantity: 当前库存总数量
      - total_records:            批次总条数
      - claim_rate:               综合领用率（%）= claimed / inbound × 100
      - aged_amount_1y:           库龄≥1年的库存金额（万元）
      - aged_ratio_1y:            长库龄库存金额占比（%）= aged / inventory × 100
      - avg_age_weighted_days:    金额加权平均库龄（天）
      - identity_check:           恒等式校验信息（inbound - claimed vs inventory）

    Returns:
        Dict: KPI 总览数据
    """
    # ── Step 1: 获取批次级明细 ──
    # _get_batch_rows() 返回物理去重后的批次行，每行包含三个核心金额
    rows = _get_batch_rows()

    # ── Step 2: Python 内存聚合 ──
    # 三个核心金额：遍历所有批次行求和
    total_inbound = sum(r["inbound_amount"] for r in rows)    # 入库总额（元）
    total_claimed = sum(r["claimed_amount"] for r in rows)    # 领用总额（元）
    total_inventory = sum(r["inventory_amount"] for r in rows) # 库存总额（元）
    total_qty = sum(r["original_quantity"] for r in rows)      # 原始数量总和
    total_records = len(rows)                                  # 批次数量

    # ── Step 3: 加权平均库龄 ──
    # 公式：Σ(inventory_amount × age_days) / Σ(inventory_amount)
    # 含义：以库存金额为权重，反映「钱在仓库放了多久」
    weighted_age_sum = sum(r["inventory_amount"] * r["age_days"] for r in rows)
    avg_age = weighted_age_sum / total_inventory if total_inventory else 0

    # ── Step 4: 长库龄占比（≥1年）──
    # 库龄 ≥ 365 天的库存金额 / 总库存金额
    aged_amount = sum(r["inventory_amount"] for r in rows if r["age_days"] >= 365)
    aged_ratio = aged_amount / total_inventory if total_inventory else 0

    # ── Step 5: 综合领用率 ──
    # 公式：claimed / inbound × 100
    # 含义：入库的物资中有多少已被领用
    claim_rate = round(total_claimed / total_inbound * 100, 2) if total_inbound else 0.0

    # ── Step 6: 会计恒等式校验 ──
    # 验证 inbound ≈ claimed + inventory
    # expected_inventory = inbound - claimed，与实际 inventory 对比
    calculated_inventory = total_inbound - total_claimed
    inventory_deviation = abs(calculated_inventory - total_inventory)
    inventory_deviation_pct = (
        round(inventory_deviation / total_inventory * 100, 4)
        if total_inventory else 0.0
    )

    return {
        # 核心金额（万元）
        "total_inbound_amount": round(total_inbound / 10000, 2),
        "total_claimed_amount": round(total_claimed / 10000, 2),
        "total_inventory_amount": round(total_inventory / 10000, 2),
        # 数量 & 批次
        "total_inventory_quantity": round(total_qty, 2),
        "total_records": total_records,
        # 领用率
        "claim_rate": claim_rate,
        # 长库龄
        "aged_amount_1y": round(aged_amount / 10000, 2),
        "aged_ratio_1y": round(aged_ratio * 100, 2),
        "avg_age_weighted_days": round(avg_age, 2),
        # 恒等式校验（供调试和监控）
        "identity_check": {
            "inbound_minus_claimed": round(calculated_inventory / 10000, 2),
            "actual_inventory": round(total_inventory / 10000, 2),
            "deviation_wan": round(inventory_deviation / 10000, 4),
            "deviation_pct": inventory_deviation_pct,
            "holds": inventory_deviation_pct < 1.0,  # 偏差 < 1% 视为成立
        },
    }
