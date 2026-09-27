# -*- coding: utf-8 -*-
"""
采购库存 BI 后台 — 指标计算服务（五页面统一版）
================================================

将原先分散在 summary.py / claim_indicators.py / structure_indicators.py /
time_indicators.py / dimension_indicators.py / top_indicators.py /
other_indicators.py / kpi_checklist.py / erp_inventory.py 中的指标逻辑，
重新整理为本单文件，覆盖以下五个前端界面的全部指标需求：

    #/kpi-checklist         KPI 考核清单
    #/indicator-overview    指标一览
    #/path1                 采消存分析（Path1PurchaseUse）
    #/path2                 责任归属（Path2Responsibility）
    #/path3                 库龄清理（Path3AgingCleanup）

每个指标函数均有中文说明，并标注具体的数据来源表与字段。

═══════════════════════════════════════════════════════════════════════════
一、数据模型与字段总览
═══════════════════════════════════════════════════════════════════════════

1. 核心宽表 v_project_inventory_wide
   （由 sql/01_v_project_inventory_wide_optimized.sql 定义）
   以 wms_inventory（真实物理库存）为主表，先按批次聚合去重，
   再通过主键关联项目台账与各维度缓存表。

   ┌ 来源表                    │ 关联键                                       │ 用途
   ├ wms_inventory             │ (主表)                                       │ 物理库存
   ├ wms_project_inventory     │ tenant_id, material_code, batch_code,        │ 项目台账
   │                           │ erp_inventory                                │
   ├ dim_material_cache        │ material_code                                │ 物料维度
   ├ dim_project_cache         │ project_code = owner_project_code            │ 项目维度
   ├ dim_outbound_log_cache    │ tenant_id, material_code, batch_code,        │ 出库日志
   │                           │ erp_inventory                                │
   └ wms_material_group        │ code（物料组编码）                           │ 物料组维度

   宽表关键字段（各指标引用的字段名）：
   —— 主键 / 批次 ——
      tenant_id                租户ID
      material_code            物料编码
      batch_code               批次编码
      erp_inventory            ERP库存标识
   —— 数量 & 金额 ——
      original_quantity        原始入库数量
      inv_current_quantity     批次当前库存数量
      total_price              批次库存金额 = Σ(current_quantity × unit_price)
      unit_price               当前加权均价
      current_quantity         项目当前库存数量（= pi_current_quantity，供项目分配用）
   —— 物料维度 ——
      material_name            物料名称
      material_unit            物料单位
      material_group_code      物料组编码
   —— 项目维度 ——
      owner_project_code       项目编码
      owner_project_type       项目类型
      project_name             项目名称
      plan_category            计划类别
      purchaser_name           采购员（dim_project_cache.purchaser_name）
      project_submitter        提报人（dim_project_cache.project_submitter）
      project_contact          联系人（dim_project_cache.project_contact）
   —— 时间维度 ——
      inbound_date             入库日期
      putaway_date             货架上架日期
      create_date              台账创建日期
      age_days                 库龄天数 = CURRENT_DATE - COALESCE(inbound_date, create_date)
   —— 出库维度（dim_outbound_log_cache）——
      total_outbound_quantity  总出库数量
      pick_quantity            拣货出库数量（change_type=31）
      repair_quantity          维修出库数量（change_type=34）
      scrap_quantity           报废出库数量（change_type=35）
      repaired_quantity        返修出库数量（change_type=36）
      last_outbound_time       最后出库时间

2. 三个核心金额口径（所有金额指标的公共基础）
      入库金额 inbound   = original_quantity × unit_price          原始入库数量按当前均价重估
      领用金额 claimed   = total_outbound_quantity × unit_price    累计出库数量按当前均价重估
      库存金额 inventory = total_price = Σ(current_quantity × unit_price)
      会计恒等式：inbound ≈ claimed + inventory（偏差 < 1%）

3. ERP 凭证表 erp_catalog_mb51（领用率的另一数据源，补齐 WMS 2026-06 前缺口）
      字段：werks（工厂，取值 '2635'）、bwart（移动类型）、charg（批次）、
            row_json（JSONB：MATNR物料编码 / DMBTR金额 / MENGE数量 /
                      BLDAT凭证日期 / MAKTX物料名称）
      移动类型：入库 = 101(收货) + 102(冲销)；出库 = 201/221/Z61

4. ERP 批次生命周期视图 v_batch_lifecycle
      关键字段：best_inventory_amt（最佳库存金额）、wms_inventory_amt（WMS实物库存）、
               erp_balance_amt（ERP账面余额）、wms_inbound_date / first_inbound_date（入库日期）、
               batch_status（批次状态）

═══════════════════════════════════════════════════════════════════════════
二、视图膨胀问题与去重策略
═══════════════════════════════════════════════════════════════════════════
v_project_inventory_wide 存在行膨胀：一个物理批次（inv_agg 已按货位聚合）在
LEFT JOIN wms_project_inventory 后，若批次归属多个项目，会产生 N 行/批次。

因此所有聚合金额必须：
  1. 批次级：DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory) 去重
  2. 项目级：先批次去重得到批次金额，再 × project_ratio 分配到各项目
  3. 严禁直接在视图上 SUM(total_price)（会被膨胀行数放大）⚠️
"""

import json
from datetime import date as dt_date, timedelta
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set, Tuple

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request

from db_config import DB_CONFIG


# ================================================================
# 数据库连接与查询辅助
# ================================================================

def _f(v) -> float:
    """安全转 float，None → 0.0。"""
    if v is None:
        return 0.0
    return float(v)


def _rows_to_float(rows: List[Dict], *fields: str) -> List[Dict]:
    """将结果中指定字段原地转 float（psycopg2 常返回 Decimal）。"""
    for r in rows:
        for f in fields:
            if f in r:
                r[f] = _f(r[f])
    return rows


def get_db():
    """获取数据库连接（autocommit）。"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """执行 SELECT，返回字典列表（RealDictCursor，用完即关连接）。"""
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        if conn:
            conn.close()


def query_one(sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    """执行 SELECT，只返回第一行。"""
    rows = query(sql, params)
    return rows[0] if rows else None


# ================================================================
# 批次去重 CTE 与项目分配因子（所有金额聚合的统一来源）
# ================================================================

_BATCH_AMOUNTS_SQL = """
    batch_amounts AS (
        SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
            tenant_id,
            material_code,
            batch_code,
            erp_inventory                       AS inv_code,

            -- ★ 三个核心金额（字段口径见文件头）：
            --   batch_inbound   入库金额 = original_quantity × unit_price
            --   batch_claimed   领用金额 = total_outbound_quantity × unit_price
            --   batch_inventory 库存金额 = total_price（视图 v_total_price）
            original_quantity * unit_price       AS batch_inbound,
            total_outbound_quantity * unit_price AS batch_claimed,
            total_price                         AS batch_inventory,

            -- 分项出库金额（31=拣货/34=维修/35=报废/36=返修）
            pick_quantity * unit_price           AS batch_pick,
            repair_quantity * unit_price         AS batch_repair,
            scrap_quantity * unit_price          AS batch_scrap,
            repaired_quantity * unit_price       AS batch_repaired,

            -- 数量字段
            original_quantity                   AS batch_orig_qty,
            total_outbound_quantity             AS batch_outbound_qty,
            current_quantity                    AS batch_current_qty,
            unit_price                          AS batch_unit_price,
            age_days                            AS batch_age_days,

            -- 维度字段
            inbound_date,
            plan_category,
            material_group_code
        FROM v_project_inventory_wide
    )
"""

_PROJECT_RATIO_SQL = """
    CASE
        -- 批次无项目台账行 → 100%% 归属当前行
        WHEN COUNT(w.pi_current_quantity) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        ) = 0 THEN 1.0
        -- 有项目台账但数量全为 0 → 平均分配
        WHEN COALESCE(SUM(w.pi_current_quantity) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        ), 0) = 0
        THEN 1.0::numeric / COUNT(w.pi_current_quantity) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        )
        -- 正常：按各项目当前库存数量占比分配
        ELSE COALESCE(w.pi_current_quantity, 0)::numeric / SUM(w.pi_current_quantity) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        )
    END
"""


def _date_filter_sql(start_date=None, end_date=None, table_alias="ba"):
    """生成入库日期区间过滤 SQL 片段（inbound_date 字段）。"""
    col_prefix = f"{table_alias}." if table_alias else ""
    parts = []
    if start_date:
        parts.append(f"{col_prefix}inbound_date >= '{start_date}'::date")
    if end_date:
        parts.append(f"{col_prefix}inbound_date <= '{end_date}'::date")
    if not parts:
        return ""
    return " AND " + " AND ".join(parts)


# ================================================================
# 数据获取基础函数（批次级 / 项目级 / 汇总 / 结构）
# ================================================================

def _get_inventory_rows(start_date=None, end_date=None) -> List[Dict]:
    """项目级库存明细（批次去重 × project_ratio 分配）。

    返回行关键字段（各指标直接引用）：
      id(=project_inventory_id)、batch_code/purchase_batch、material_name、material_code、
      project_code(=owner_project_code)、project_name、
      purchaser_name(=project_submitter 提报人)、applicant_name(=purchaser_name 采购员)、
      contact_name(=project_contact 联系人)、plan_category(=project_type)、
      inbound_date、putaway_date、original_quantity、current_quantity(=pi_current_quantity)、
      used_quantity(领用数量)、pick/repair/scrap/repaired_quantity(分项出库数量)、
      unit_price、unit、supplier_code、
      inbound_amount/claimed_amount/inventory_amount(项目级金额 = 批次金额 × project_ratio)、
      claim_rate、age_days
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.*,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
                ba.batch_orig_qty,
                ba.batch_outbound_qty,
                ba.batch_unit_price,
                ba.batch_age_days,
                ba.batch_pick,
                ba.batch_repair,
                ba.batch_scrap,
                ba.batch_repaired,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE 1=1{_date_filter_sql(start_date, end_date)}
        )
        SELECT
            r.project_inventory_id                  AS id,
            r.batch_code                            AS purchase_batch,
            r.material_name,
            r.material_code,
            r.owner_project_code                    AS project_code,
            r.project_name,
            r.project_submitter                     AS purchaser_name,   -- 提报人（采购归属）
            r.purchaser_name                        AS applicant_name,   -- 采购员
            r.project_contact                       AS contact_name,     -- 联系人
            r.plan_category                         AS project_type,
            r.inbound_date::date                    AS inbound_date,
            r.putaway_date::date                    AS putaway_date,
            r.last_outbound_time                    AS last_outbound_time,
            r.batch_code,
            r.original_quantity,
            r.pi_current_quantity                   AS current_quantity,
            ROUND((r.total_outbound_quantity
                   * r.project_ratio)::numeric, 4)  AS used_quantity,
            ROUND((r.pick_quantity
                   * r.project_ratio)::numeric, 4)  AS pick_quantity,
            ROUND((r.repair_quantity
                   * r.project_ratio)::numeric, 4)  AS repair_quantity,
            ROUND((r.scrap_quantity
                   * r.project_ratio)::numeric, 4)  AS scrap_quantity,
            ROUND((r.repaired_quantity
                   * r.project_ratio)::numeric, 4)  AS repaired_quantity,
            r.batch_unit_price                      AS unit_price,
            r.material_unit                         AS unit,
            r.supplier_code,
            ROUND((r.batch_inbound
                   * r.project_ratio)::numeric, 2)  AS inbound_amount,
            ROUND((r.batch_claimed
                   * r.project_ratio)::numeric, 2)  AS claimed_amount,
            ROUND((r.batch_inventory
                   * r.project_ratio)::numeric, 2)  AS inventory_amount,
            CASE WHEN r.batch_orig_qty > 0
                 THEN LEAST(ROUND(r.batch_outbound_qty::numeric
                          / r.batch_orig_qty * 100, 2), 100.00)
                 ELSE 0
            END                                     AS claim_rate,
            CASE WHEN r.batch_orig_qty > 0
                 THEN LEAST(ROUND(r.batch_outbound_qty::numeric
                          / r.batch_orig_qty * 100, 2), 100.00)
                 ELSE 0
            END                                     AS claim_rate_on_inbound,
            r.batch_age_days                        AS age_days
        FROM wide_with_ratio r
    """)
    return _rows_to_float(rows,
        "original_quantity", "current_quantity", "used_quantity",
        "pick_quantity", "repair_quantity", "scrap_quantity", "repaired_quantity",
        "unit_price", "inbound_amount", "claimed_amount",
        "inventory_amount", "claim_rate", "age_days")


def _get_batch_rows(start_date=None, end_date=None) -> List[Dict]:
    """批次级明细（物理去重，不做项目分配）。

    返回每行对应一个物理批次，字段：
      inbound_amount / claimed_amount / inventory_amount（三核心金额）、
      original_quantity / used_quantity / current_quantity、
      pick/repair/scrap/repaired_quantity（分项出库数量）、
      unit_price、age_days、inbound_date、material_group_code
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            batch_inbound   AS inbound_amount,
            batch_claimed   AS claimed_amount,
            batch_inventory AS inventory_amount,
            batch_orig_qty      AS original_quantity,
            batch_outbound_qty  AS used_quantity,
            batch_current_qty   AS current_quantity,
            batch_pick          AS pick_quantity,
            batch_repair        AS repair_quantity,
            batch_scrap         AS scrap_quantity,
            batch_repaired      AS repaired_quantity,
            batch_unit_price    AS unit_price,
            batch_age_days      AS age_days,
            inbound_date,
            material_group_code
        FROM batch_amounts
        WHERE 1=1{_date_filter_sql(start_date, end_date, table_alias="")}
    """)
    return _rows_to_float(rows,
        "inbound_amount", "claimed_amount", "inventory_amount",
        "original_quantity", "used_quantity", "current_quantity",
        "pick_quantity", "repair_quantity", "scrap_quantity", "repaired_quantity",
        "unit_price", "age_days")


def _get_wide_batch_aggregates(year: Optional[int] = None, start_date=None, end_date=None) -> Dict[str, float]:
    """按物理批次去重聚合，返回核心金额汇总（绝对总额，不区分项目）。

    Args:
        year:       只统计该自然年入库（inbound_date 年份）的批次，None 为全部
        start_date / end_date: 入库日期区间过滤

    Returns:
        total_inbound_amount / total_claimed_amount / total_inventory_amount、
        original_quantity / total_outbound_quantity / total_current_quantity、
        total_pick_amount / total_repair_amount / total_scrap_amount / total_repaired_amount
    """
    date_clause = _date_filter_sql(start_date, end_date, table_alias="")
    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            COALESCE(SUM(batch_inbound), 0)   AS total_inbound_amount,
            COALESCE(SUM(batch_claimed), 0)   AS total_claimed_amount,
            COALESCE(SUM(batch_inventory), 0) AS total_inventory_amount,
            COALESCE(SUM(batch_orig_qty), 0)      AS original_quantity,
            COALESCE(SUM(batch_outbound_qty), 0)  AS total_outbound_quantity,
            COALESCE(SUM(batch_current_qty), 0)   AS total_current_quantity,
            COALESCE(SUM(batch_pick), 0)       AS total_pick_amount,
            COALESCE(SUM(batch_repair), 0)     AS total_repair_amount,
            COALESCE(SUM(batch_scrap), 0)      AS total_scrap_amount,
            COALESCE(SUM(batch_repaired), 0)   AS total_repaired_amount
        FROM batch_amounts
        WHERE (%s IS NULL OR EXTRACT(YEAR FROM inbound_date) = %s){date_clause}
    """
    rows = query(sql, (year, year))
    if not rows:
        return {
            "total_inbound_amount": 0.0, "total_claimed_amount": 0.0,
            "total_inventory_amount": 0.0, "original_quantity": 0.0,
            "total_outbound_quantity": 0.0, "total_current_quantity": 0.0,
            "total_pick_amount": 0.0, "total_repair_amount": 0.0,
            "total_scrap_amount": 0.0, "total_repaired_amount": 0.0,
        }
    return _rows_to_float(rows, *rows[0].keys())[0]


def _get_wide_structure_aggregates(start_date=None, end_date=None) -> Dict[str, List[Dict]]:
    """按项目和采购人聚合库存金额（项目分摊后），供 K6 库存结构分析。

    字段口径：
      project_rows:   [{owner_project_code, project_name, project_submitter,
                        project_contact, inventory_amount}, ...]  按金额降序
      purchaser_rows: [{purchaser_name, inventory_amount}, ...]   按金额降序
                      ⚠️ 此处 purchaser_name = project_contact（项目联系人）
    """
    date_clause = _date_filter_sql(start_date, end_date)
    project_rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.owner_project_code,
                w.project_name,
                w.project_submitter,
                w.project_contact,
                ba.batch_inventory,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE 1=1{date_clause}
        )
        SELECT
            owner_project_code,
            MAX(project_name) AS project_name,
            MAX(project_submitter) AS project_submitter,
            MAX(project_contact) AS project_contact,
            SUM(batch_inventory * project_ratio) AS inventory_amount
        FROM wide_with_ratio
        GROUP BY owner_project_code
        ORDER BY inventory_amount DESC NULLS LAST
    """, None)
    project_rows = _rows_to_float(project_rows, "inventory_amount")

    purchaser_rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.project_contact,
                ba.batch_inventory,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE w.project_contact IS NOT NULL
              AND char_length(w.project_contact) > 0{date_clause}
        )
        SELECT
            project_contact AS purchaser_name,
            SUM(batch_inventory * project_ratio) AS inventory_amount
        FROM wide_with_ratio
        GROUP BY project_contact
        ORDER BY inventory_amount DESC
    """, None)
    purchaser_rows = _rows_to_float(purchaser_rows, "inventory_amount")

    return {"project_rows": project_rows, "purchaser_rows": purchaser_rows}


# ================================================================
# 第一类：核心汇总指标
#   get_summary             → #/indicator-overview / #/path1 / #/path3
#   get_claim_indicators    → #/path1
#   get_structure_indicators→ #/indicator-overview / #/path2
#   get_time_indicators     → #/indicator-overview / #/path3
#   get_age_layers          → #/indicator-overview / #/path3
#   get_age_monthly         → #/path3
#   get_age_heatmap         → #/path3
# ================================================================

def get_summary() -> Dict:
    """0. KPI 总览（页面 #/indicator-overview / #/path1 / #/path3）。

    指标（金额单位为万元）：
      total_inbound_amount   入库总额   = Σ original_quantity × unit_price
      total_claimed_amount   领用总额   = Σ total_outbound_quantity × unit_price
      total_inventory_amount 当前库存   = Σ total_price
      total_inventory_quantity 库存总数量 = Σ original_quantity
      total_records          批次总条数
      claim_rate             综合领用率 = claimed / inbound × 100%
      aged_amount_1y         库龄≥1年库存金额
      aged_ratio_1y          长库龄占比 = 库龄≥365天金额 / 总库存
      avg_age_weighted_days  金额加权平均库龄 = Σ(inventory×age_days)/Σ(inventory)

    数据来源：v_project_inventory_wide → 批次去重明细 _get_batch_rows()
    涉及字段：original_quantity、unit_price、total_outbound_quantity、total_price、age_days
    """
    rows = _get_batch_rows()
    total_inbound = sum(r["inbound_amount"] for r in rows)
    total_claimed = sum(r["claimed_amount"] for r in rows)
    total_inventory = sum(r["inventory_amount"] for r in rows)
    total_qty = sum(r["original_quantity"] for r in rows)
    total_records = len(rows)

    weighted_age_sum = sum(r["inventory_amount"] * r["age_days"] for r in rows)
    avg_age = weighted_age_sum / total_inventory if total_inventory else 0

    aged_amount = sum(r["inventory_amount"] for r in rows if r["age_days"] >= 365)
    aged_ratio = aged_amount / total_inventory if total_inventory else 0

    claim_rate = round(total_claimed / total_inbound * 100, 2) if total_inbound else 0.0

    calculated_inventory = total_inbound - total_claimed
    inventory_deviation = abs(calculated_inventory - total_inventory)
    inventory_deviation_pct = (
        round(inventory_deviation / total_inventory * 100, 4)
        if total_inventory else 0.0
    )

    return {
        "total_inbound_amount": round(total_inbound / 10000, 2),
        "total_claimed_amount": round(total_claimed / 10000, 2),
        "total_inventory_amount": round(total_inventory / 10000, 2),
        "total_inventory_quantity": round(total_qty, 2),
        "total_records": total_records,
        "claim_rate": claim_rate,
        "aged_amount_1y": round(aged_amount / 10000, 2),
        "aged_ratio_1y": round(aged_ratio * 100, 2),
        "avg_age_weighted_days": round(avg_age, 2),
        "identity_check": {
            "inbound_minus_claimed": round(calculated_inventory / 10000, 2),
            "actual_inventory": round(total_inventory / 10000, 2),
            "deviation_wan": round(inventory_deviation / 10000, 4),
            "deviation_pct": inventory_deviation_pct,
            "holds": inventory_deviation_pct < 1.0,
        },
    }


def _query_claim_aggregates(current_year: int) -> Dict[str, Dict[str, float]]:
    """一次查询返回「全部」和「当年」两个维度的批次聚合指标。"""
    sql = f"""
        WITH batch_amounts AS (
            SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
                original_quantity * unit_price       AS batch_inbound,
                total_outbound_quantity * unit_price AS batch_claimed,
                total_price                         AS batch_inventory,
                original_quantity                   AS batch_orig_qty,
                total_outbound_quantity             AS batch_outbound_qty,
                inbound_date
            FROM v_project_inventory_wide
        )
        SELECT
            COALESCE(SUM(batch_inbound), 0)      AS inbound_all,
            COALESCE(SUM(batch_claimed), 0)      AS claimed_all,
            COALESCE(SUM(batch_inventory), 0)    AS inventory_all,
            COALESCE(SUM(batch_orig_qty), 0)     AS orig_qty_all,
            COALESCE(SUM(batch_outbound_qty), 0) AS outbound_qty_all,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_inbound ELSE 0 END), 0) AS inbound_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_claimed ELSE 0 END), 0) AS claimed_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_inventory ELSE 0 END), 0) AS inventory_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_orig_qty ELSE 0 END), 0) AS orig_qty_year,
            COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                         THEN batch_outbound_qty ELSE 0 END), 0) AS outbound_qty_year
        FROM batch_amounts
    """
    rows = query(sql)
    row = _rows_to_float(rows, *rows[0].keys())[0]
    return {
        "all": {
            "total_inbound_amount": row["inbound_all"],
            "total_claimed_amount": row["claimed_all"],
            "total_inventory_amount": row["inventory_all"],
            "original_quantity": row["orig_qty_all"],
            "total_outbound_quantity": row["outbound_qty_all"],
        },
        "year": {
            "total_inbound_amount": row["inbound_year"],
            "total_claimed_amount": row["claimed_year"],
            "total_inventory_amount": row["inventory_year"],
            "original_quantity": row["orig_qty_year"],
            "total_outbound_quantity": row["outbound_qty_year"],
        },
    }


def _build_claim_range(agg: Dict[str, float]) -> Dict:
    """基于聚合金额计算领用率指标（金额/数量领用率、未领用金额及占比）。"""
    total_inbound_amt = agg.get("total_inbound_amount", 0.0)
    total_claimed_amt = agg.get("total_claimed_amount", 0.0)
    total_inbound_qty = agg.get("original_quantity", 0.0)
    total_claimed_qty = agg.get("total_outbound_quantity", 0.0)
    unclaimed_amt = total_inbound_amt - total_claimed_amt

    return {
        "claim_rate_amount": round(total_claimed_amt / total_inbound_amt * 100, 2)
        if total_inbound_amt else 0.0,
        "claim_rate_quantity": round(total_claimed_qty / total_inbound_qty * 100, 2)
        if total_inbound_qty else 0.0,
        "unclaimed_amount": round(unclaimed_amt / 10000, 2),
        "unclaimed_amount_ratio": round(unclaimed_amt / total_inbound_amt * 100, 2)
        if total_inbound_amt else 0.0,
        "total_inbound_amount": round(total_inbound_amt / 10000, 2),
        "total_claimed_amount": round(total_claimed_amt / 10000, 2),
        "total_inbound_quantity": round(total_inbound_qty, 2),
        "total_claimed_quantity": round(total_claimed_qty, 2),
    }


def get_claim_indicators() -> Dict:
    """1. 采购领用率指标（页面 #/path1），按「当年/全部」拆分。

    指标：
      领用率（金额） = claimed / inbound × 100%
      领用率（数量） = outbound_qty / original_qty × 100%
      未领用金额      = inbound - claimed（万元）
      未领用占比      = (inbound - claimed) / inbound × 100%

    数据来源：v_project_inventory_wide（批次去重）
    涉及字段：original_quantity、unit_price、total_outbound_quantity、total_price、inbound_date
    """
    current_year = dt_date.today().year
    aggs = _query_claim_aggregates(current_year)
    return {
        "current_year": current_year,
        "year_start": f"{current_year}-01-01",
        "year_end": f"{current_year}-12-31",
        "all": _build_claim_range(aggs["all"]),
        "year": _build_claim_range(aggs["year"]),
    }


def get_structure_indicators() -> Dict:
    """5-8. 库存结构指标（页面 #/indicator-overview / #/path2）。

    指标：
      current_inventory_amount       当前库存金额（全部，万元）
      current_year_inventory_amount  当年入库库存金额（万元）
      current_inventory_quantity     当前库存总数量
      project_ratios                 项目库存占比 TOP（含 project_submitter / project_contact）
      purchaser_ratios               采购员库存占比 TOP（按 purchaser_name = 采购员）

    数据来源：v_project_inventory_wide → 批次去重 × project_ratio
    涉及字段：total_price、original_quantity、inbound_date、owner_project_code、
             project_name、purchaser_name、pi_current_quantity
    """
    current_year = dt_date.today().year

    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        all_totals AS (
            SELECT
                COALESCE(SUM(batch_inventory), 0) AS total_inventory,
                COALESCE(SUM(batch_inbound), 0)   AS total_inbound,
                COALESCE(SUM(batch_orig_qty), 0)  AS total_qty,
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                             THEN batch_inventory ELSE 0 END), 0) AS year_inventory
            FROM batch_amounts
        ),
        wide_with_ratio AS (
            SELECT
                w.owner_project_code,
                w.project_name,
                w.purchaser_name,
                ba.batch_inventory,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
        ),
        project_agg AS (
            SELECT
                owner_project_code,
                MAX(project_name) AS project_name,
                SUM(batch_inventory * project_ratio) AS inventory_amount
            FROM wide_with_ratio
            GROUP BY owner_project_code
        ),
        purchaser_agg AS (
            SELECT
                purchaser_name,
                SUM(batch_inventory * project_ratio) AS inventory_amount
            FROM wide_with_ratio
            WHERE purchaser_name IS NOT NULL AND char_length(purchaser_name) > 0
            GROUP BY purchaser_name
        )
        SELECT
            (SELECT total_inventory FROM all_totals) AS total_inventory_amt,
            (SELECT total_qty FROM all_totals)       AS total_inventory_qty,
            (SELECT year_inventory FROM all_totals)  AS year_inventory_amt,
            (SELECT json_agg(row_to_json(project_agg.*)
             ORDER BY project_agg.inventory_amount DESC) FROM project_agg) AS project_json,
            (SELECT json_agg(row_to_json(purchaser_agg.*)
             ORDER BY purchaser_agg.inventory_amount DESC) FROM purchaser_agg) AS purchaser_json
    """
    row = query_one(sql)
    if not row:
        return {
            "current_year": current_year,
            "year_start": f"{current_year}-01-01",
            "year_end": f"{current_year}-12-31",
            "current_inventory_amount": 0,
            "current_year_inventory_amount": 0,
            "current_inventory_quantity": 0,
            "project_ratios": [],
            "purchaser_ratios": [],
        }

    total_inventory_amt = _f(row["total_inventory_amt"])
    total_inventory_qty = _f(row["total_inventory_qty"])
    year_inventory_amt = _f(row["year_inventory_amt"])

    def _parse_json(val):
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return json.loads(val)

    project_rows = _parse_json(row["project_json"])
    purchaser_rows = _parse_json(row["purchaser_json"])

    project_ratios = []
    for r in project_rows:
        pa = _f(r.get("inventory_amount", 0))
        code = r.get("owner_project_code") or ""
        project_ratios.append({
            "project_code": code,
            "project_name": r.get("project_name") or code,
            "inventory_amount": round(pa, 2),
            "ratio": round(pa / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    purchaser_ratios = []
    for r in purchaser_rows:
        pa = _f(r.get("inventory_amount", 0))
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
        "current_year_inventory_amount": round(year_inventory_amt / 10000, 2),
        "current_inventory_quantity": round(total_inventory_qty, 2),
        "project_ratios": project_ratios,
        "purchaser_ratios": purchaser_ratios,
    }


def get_time_indicators(age_ranges: List[tuple] = None) -> Dict:
    """9-11. 库龄时间核心指标（页面 #/indicator-overview / #/path3）。

    指标：
      aged_ratio_1y          长库龄占比（比例）= 库龄≥365天金额 / 总库存
      aged_amount_1y         长库龄金额（元）
      age_structure          [{range, amount, ratio, count}] 库龄结构
      avg_age_weighted_days  金额加权平均库龄 = Σ(inventory×age_days)/Σ(inventory)

    数据来源：v_project_inventory_wide → 批次去重 _get_batch_rows()
    涉及字段：total_price（库存金额）、age_days（库龄天数）
    """
    if age_ranges is None:
        age_ranges = [
            (0, 365, "≤1年"),
            (365, 1095, "1~3年"),
            (1095, 1825, "3~5年"),
            (1825, 99999, "≥5年"),
        ]

    rows = _get_batch_rows()
    total_inventory = sum(r["inventory_amount"] for r in rows)

    weighted_age_sum = sum(r["inventory_amount"] * r["age_days"] for r in rows)
    avg_age = weighted_age_sum / total_inventory if total_inventory else 0

    aged_amount = sum(r["inventory_amount"] for r in rows if r["age_days"] >= 365)
    aged_ratio = aged_amount / total_inventory if total_inventory else 0

    structure = []
    for min_age, max_age, label in age_ranges:
        amt = sum(r["inventory_amount"] for r in rows if min_age <= r["age_days"] < max_age)
        cnt = sum(1 for r in rows if min_age <= r["age_days"] < max_age)
        structure.append({
            "range": label,
            "amount": round(amt, 2),
            "ratio": round(amt / total_inventory, 4) if total_inventory else 0,
            "count": cnt,
        })

    return {
        "aged_ratio_1y": round(aged_ratio, 4),
        "aged_amount_1y": round(aged_amount, 2),
        "age_structure": structure,
        "avg_age_weighted_days": round(avg_age, 2),
    }


def get_age_layers(min_amount: float = 0, min_age: int = 0, max_age: int = None) -> List[Dict]:
    """12. 库龄分层明细（页面 #/indicator-overview / #/path3）。

    按库存金额 / 库龄筛选具体物料行（项目级明细），返回字段：
      id、material_code、material_name、batch_code、inventory_amount、
      current_quantity、age_days、inbound_date、unit_price、supplier_code、
      project_code、project_name

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：material_code、material_name、batch_code、inventory_amount、
             current_quantity(=pi_current_quantity)、age_days、inbound_date、
             unit_price、supplier_code、owner_project_code、project_name
    """
    rows = _get_inventory_rows()
    result = []
    for r in rows:
        age = r["age_days"]
        amt = r["inventory_amount"]
        if amt >= min_amount and age >= min_age:
            if max_age is None or age <= max_age:
                result.append({
                    "id": r["id"],
                    "material_code": r["material_code"],
                    "material_name": r.get("material_name", ""),
                    "batch_code": r["batch_code"],
                    "inventory_amount": round(amt, 2),
                    "current_quantity": r["current_quantity"],
                    "age_days": int(age),
                    "inbound_date": str(r["inbound_date"]),
                    "unit_price": r["unit_price"],
                    "supplier_code": r["supplier_code"],
                    "project_code": r.get("project_code", ""),
                    "project_name": r.get("project_name", ""),
                })
    result.sort(key=lambda x: x["inventory_amount"], reverse=True)
    return result


def get_age_monthly() -> Dict:
    """平均库龄月度趋势（页面 #/path3，近 12 个月）。

    计算：对每个历史月份的月末，回溯「当月已入库」的批次：
      加权平均库龄 = Σ(入库金额 × 该月末库龄) / Σ(入库金额)
      超90天占比   = Σ(入库金额 WHERE 库龄≥90) / Σ(入库金额)
    权重使用 inbound_amount（入库金额，反映批次入库时的完整价值）。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：inbound_date（入库日期）、inbound_amount（入库金额）
    """
    today = dt_date.today()

    month_ends: List[dt_date] = []
    for i in range(11, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        first_day = dt_date(y, m, 1)
        if m == 12:
            last_day = dt_date(y, 12, 31)
        else:
            last_day = dt_date(y, m + 1, 1) - timedelta(days=1)
        month_ends.append(last_day)

    rows = _get_inventory_rows()

    months: List[str] = []
    data: List[Dict] = []
    for month_end in month_ends:
        total_weight = 0.0
        age_weighted_sum = 0.0
        over90_weight = 0.0
        for r in rows:
            d = r["inbound_date"]
            if hasattr(d, 'date'):
                d = d.date()
            elif isinstance(d, str):
                d = dt_date.fromisoformat(d)
            if d is None or d > month_end:
                continue
            age = (month_end - d).days
            weight = r["inbound_amount"]
            total_weight += weight
            age_weighted_sum += weight * age
            if age >= 90:
                over90_weight += weight

        avg_age = round(age_weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
        over90_rate = round(over90_weight / total_weight * 100, 1) if total_weight > 0 else 0.0
        label = f"{month_end.year}年{month_end.month}月"
        months.append(label)
        data.append({"month": label, "avg_age": avg_age, "over90_rate": over90_rate})

    return {"months": months, "data": data}


def get_age_heatmap() -> Dict:
    """滞留库存热力图（页面 #/path3，物料类别 × 库龄段）。

    按物料组类别（material_group_code）× 6 个库龄段交叉统计库存金额，取 TOP 10 类别。

    数据来源：v_project_inventory_wide（批次去重）+ wms_material_group（类别名称）
    涉及字段：material_group_code、age_days、total_price（batch_inventory）
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            ba.material_group_code AS category_code,
            ba.batch_age_days AS age_days,
            ba.batch_inventory AS inventory_amount
        FROM batch_amounts ba
    """)
    rows = _rows_to_float(rows, "inventory_amount", "age_days")

    AGE_RANGES = [
        (0, 30, '0-30天'),
        (30, 60, '30-60天'),
        (60, 90, '60-90天'),
        (90, 180, '90-180天'),
        (180, 365, '180-365天'),
        (365, 99999, '>365天'),
    ]

    cat_name_map: Dict[str, str] = {}
    cat_codes = list({r["category_code"] for r in rows if r["category_code"]})
    if cat_codes:
        placeholders = ','.join(['%s'] * len(cat_codes))
        name_rows = query(f"""
            SELECT code, name FROM wms_material_group
            WHERE code IN ({placeholders}) AND del_flag = '0'
        """, tuple(cat_codes))
        cat_name_map = {r["code"]: r["name"] or r["code"] for r in name_rows}

    cat_data: Dict[str, Dict] = {}
    for r in rows:
        code = r["category_code"] or "未知"
        name = cat_name_map.get(code, code)
        age = int(r["age_days"])
        amt = r["inventory_amount"]
        if code not in cat_data:
            cat_data[code] = {
                "name": name,
                "total": 0.0,
                "ages": {label: 0.0 for _, _, label in AGE_RANGES},
            }
        cat_data[code]["total"] += amt
        for min_age, max_age, label in AGE_RANGES:
            if min_age <= age < max_age:
                cat_data[code]["ages"][label] += amt
                break

    top_cats = sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True)[:10]
    age_labels = [label for _, _, label in reversed(AGE_RANGES)]
    matrix: List[List[float]] = []
    for _, _, label in reversed(AGE_RANGES):
        row = []
        for _, cat in top_cats:
            row.append(round(cat["ages"][label] / 10000, 2))
        matrix.append(row)

    return {
        "categories": [cat["name"] for _, cat in top_cats],
        "age_labels": age_labels,
        "data": matrix,
    }


# ================================================================
# 第二类：维度指标（项目 / 采购人）
#   get_by_project    → #/indicator-overview / #/path2 / #/path3
#   get_by_purchaser  → #/indicator-overview / #/path2
# ================================================================

def get_by_project(owner_project_type: str = None, start_date=None, end_date=None) -> List[Dict]:
    """13-15. 项目维度分析（页面 #/indicator-overview / #/path2 / #/path3）。

    返回每个项目：
      project_code / project_name          项目编码 / 名称
      inbound_amount / claimed_amount      入库 / 领用金额（项目分配后，元）
      unclaimed_amount                     未消耗库存金额（= 库存金额，元）
      claim_rate                           领用率（%）= claimed / inbound，上限 100%
      avg_age_days                         金额加权平均库龄（天）
      over90_ratio                         库龄≥90天库存占比（%）
      record_count                         记录数

    数据来源：v_project_inventory_wide → 批次去重 × project_ratio → GROUP BY owner_project_code
    涉及字段：owner_project_code、project_name、owner_project_type、
             batch_inbound/batch_claimed/batch_inventory（三核心金额）、age_days
    """
    date_clause = _date_filter_sql(start_date, end_date)
    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.owner_project_code AS project_code,
                w.project_name,
                w.owner_project_type,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
                ba.batch_age_days,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE 1=1{date_clause}
        )
        SELECT
            project_code,
            MAX(project_name) AS project_name,
            SUM(batch_inbound * project_ratio)   AS inbound_amt,
            SUM(batch_claimed * project_ratio)   AS claimed_amt,
            SUM(batch_inventory * project_ratio) AS inventory_amt,
            SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted,
            SUM(CASE WHEN batch_age_days >= 90
                THEN batch_inventory * project_ratio ELSE 0 END) AS over90_amt,
            COUNT(*) AS record_count
        FROM wide_with_ratio
        WHERE %s IS NULL OR wide_with_ratio.owner_project_type = %s
        GROUP BY project_code
        ORDER BY inventory_amt DESC
    """
    rows = query(sql, (owner_project_type, owner_project_type))
    rows = _rows_to_float(rows, "inbound_amt", "claimed_amt", "inventory_amt",
                         "age_weighted", "over90_amt")

    result = []
    for r in rows:
        code = r["project_code"] or ""
        inb, clm, inv, age_w, over90 = (
            r["inbound_amt"], r["claimed_amt"], r["inventory_amt"],
            r["age_weighted"], r["over90_amt"],
        )
        result.append({
            "project_code": code,
            "project_name": r["project_name"] or "",
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "unclaimed_amount": round(inv, 2),
            "claim_rate": min(round(clm / inb * 100, 2), 100.00) if inb else 0,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
            "over90_ratio": round(over90 / inv * 100, 1) if inv else 0,
            "record_count": int(r["record_count"] or 0),
        })
    return result


def get_by_purchaser(start_date=None, end_date=None) -> List[Dict]:
    """16-18. 采购人维度分析（页面 #/indicator-overview / #/path2）。

    与 get_by_project 逻辑相同，但按 project_contact（项目联系人）聚合。

    数据来源：v_project_inventory_wide → 批次去重 × project_ratio → GROUP BY project_contact
    涉及字段：project_contact（联系人）、三核心金额、age_days
    """
    date_clause = _date_filter_sql(start_date, end_date)
    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        wide_with_ratio AS (
            SELECT
                w.project_contact AS contact_name,
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
                ba.batch_age_days,
                {_PROJECT_RATIO_SQL} AS project_ratio
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
                AND ba.inv_code IS NOT DISTINCT FROM w.erp_inventory
            WHERE 1=1{date_clause}
        )
        SELECT
            contact_name AS purchaser_name,
            SUM(batch_inbound * project_ratio)   AS inbound_amt,
            SUM(batch_claimed * project_ratio)   AS claimed_amt,
            SUM(batch_inventory * project_ratio) AS inventory_amt,
            SUM(batch_inventory * project_ratio * batch_age_days) AS age_weighted,
            COUNT(*) AS record_count
        FROM wide_with_ratio
        WHERE contact_name IS NOT NULL AND char_length(contact_name) > 0
        GROUP BY contact_name
        ORDER BY inventory_amt DESC
    """
    rows = query(sql)
    rows = _rows_to_float(rows, "inbound_amt", "claimed_amt", "inventory_amt", "age_weighted")

    result = []
    for r in rows:
        inb, clm, inv, age_w = (
            r["inbound_amt"], r["claimed_amt"], r["inventory_amt"], r["age_weighted"]
        )
        name = r["purchaser_name"]
        result.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "unclaimed_amount": round(inv, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else 0,
            "avg_age_days": round(age_w / inv, 2) if inv else 0,
            "record_count": int(r["record_count"] or 0),
        })
    return result


# ================================================================
# 第三类：TOP 指标（页面 #/indicator-overview）
# ================================================================

def get_top_unclaimed_amount(limit: int = 10) -> List[Dict]:
    """19. 未领用库存 TOP（金额）（页面 #/indicator-overview）。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：inventory_amount（库存金额）、material_code/name、current_quantity、
             unit、age_days、owner_project_code/name、purchaser_name(=提报人)
    """
    rows = _get_inventory_rows()
    rows.sort(key=lambda r: r["inventory_amount"], reverse=True)
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
        for r in rows[:limit]
    ]


def get_top_unclaimed_quantity(limit: int = 10) -> List[Dict]:
    """20. 未领用库存 TOP（数量）（页面 #/indicator-overview）。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：current_quantity（项目当前库存数量）
    """
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
    """21. 领用 TOP（金额）（页面 #/indicator-overview），按物料编码聚合。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：material_code/name、claimed_amount（领用金额）、inbound_amount、inbound_date
    """
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
    """22. 领用 TOP（数量）（页面 #/indicator-overview），按物料编码聚合。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：material_code/name、used_quantity（领用数量）、original_quantity、inbound_date
    """
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


# ================================================================
# 第四类：时序 & 专项图表（页面 #/path1 / #/path2）
# ================================================================

def get_claim_monthly(non_project_only: bool = False) -> Dict:
    """按月入库/领用/领用率（页面 #/path1，最近 12 个月）。

    月份按 putaway_date（上架日期）或 inbound_date（入库日期）归集。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：putaway_date / inbound_date、inbound_amount、claimed_amount
    """
    rows = _get_inventory_rows()
    if non_project_only:
        rows = [r for r in rows if not (r.get("project_name") or "").strip()]

    monthly: OrderedDict[str, Dict[str, float]] = OrderedDict()
    for r in rows:
        d = r["putaway_date"] or r["inbound_date"]
        if d is None:
            continue
        if hasattr(d, 'strftime'):
            month = d.strftime("%Y-%m")
        else:
            month = str(d)[:7]
        if month not in monthly:
            monthly[month] = {"inbound": 0.0, "claimed": 0.0}
        monthly[month]["inbound"] += r["inbound_amount"]
        monthly[month]["claimed"] += r["claimed_amount"]

    all_months = sorted(monthly.keys())
    recent_months = all_months[-12:] if len(all_months) > 12 else all_months

    months, data = [], []
    for month in recent_months:
        v = monthly[month]
        inbound = v["inbound"]
        claimed = v["claimed"]
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        months.append(month)
        data.append({
            "month": month,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })
    return {"months": months, "data": data}


def get_claim_yearly() -> Dict:
    """按年入库/领用/领用率（页面 #/path1，全部年份）。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：putaway_date / inbound_date、inbound_amount、claimed_amount
    """
    rows = _get_inventory_rows()
    yearly: OrderedDict[str, Dict[str, float]] = OrderedDict()
    for r in rows:
        d = r["putaway_date"] or r["inbound_date"]
        if d is None:
            continue
        if hasattr(d, 'strftime'):
            year = d.strftime("%Y")
        else:
            year = str(d)[:4]
        if year not in yearly:
            yearly[year] = {"inbound": 0.0, "claimed": 0.0}
        yearly[year]["inbound"] += r["inbound_amount"]
        yearly[year]["claimed"] += r["claimed_amount"]

    years, data = [], []
    for year in sorted(yearly.keys()):
        v = yearly[year]
        inbound = v["inbound"]
        claimed = v["claimed"]
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        years.append(year)
        data.append({
            "year": year,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })
    return {"years": years, "data": data}


def get_claim_daily() -> Dict:
    """按天入库/领用/领用率（页面 #/path1，上月 + 当月，日粒度）。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：inbound_date、inbound_amount、claimed_amount
    """
    rows = _get_inventory_rows()
    today = dt_date.today()
    first_day_current = today.replace(day=1)
    first_day_prev = (first_day_current - timedelta(days=1)).replace(day=1)

    day_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d is None or d < first_day_prev:
            continue
        key = d.strftime("%Y-%m-%d")
        if key not in day_map:
            day_map[key] = {"inbound": 0.0, "claimed": 0.0}
        day_map[key]["inbound"] += r["inbound_amount"]
        day_map[key]["claimed"] += r["claimed_amount"]

    days, data = [], []
    d = first_day_prev
    while d <= today:
        key = d.strftime("%Y-%m-%d")
        if key in day_map:
            inbound = day_map[key]["inbound"]
            claimed = day_map[key]["claimed"]
        else:
            inbound = claimed = 0.0
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        days.append(key)
        data.append({
            "day": key,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })
        d += timedelta(days=1)
    return {"days": days, "data": data}


def get_claim_weekly() -> Dict:
    """按周入库/领用/领用率（页面 #/path1，最近 12 周，ISO 周）。

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：inbound_date、inbound_amount、claimed_amount
    """
    rows = _get_inventory_rows()
    today = dt_date.today()
    cutoff = today - timedelta(weeks=12)

    week_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d is None or d < cutoff:
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        if week_key not in week_map:
            monday = d - timedelta(days=d.weekday())
            week_map[week_key] = {"inbound": 0.0, "claimed": 0.0, "monday": monday}
        week_map[week_key]["inbound"] += r["inbound_amount"]
        week_map[week_key]["claimed"] += r["claimed_amount"]

    weeks, data = [], []
    for week_key in sorted(week_map.keys()):
        v = week_map[week_key]
        inbound = v["inbound"]
        claimed = v["claimed"]
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        monday = v["monday"]
        sunday = monday + timedelta(days=6)
        label = f"{monday.strftime('%Y-%m-%d')} ~ {sunday.strftime('%Y-%m-%d')}"
        weeks.append(label)
        data.append({
            "week": label,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })
    return {"weeks": weeks, "data": data}


def get_structure_by_category() -> Dict:
    """在库水位 · 安全库存偏离度（页面 #/path1，按物料编码 TOP 10 + 其他）。

    安全上下限：safe_min = 均值×0.5，safe_max = 均值×1.5（均值为 TOP10 物料平均库存金额）。

    数据来源：v_project_inventory_wide（批次去重）+ dim_material_cache（物料名称）
    涉及字段：material_code、batch_inventory（库存金额）、material_name
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            ba.material_code,
            COALESCE(MAX(NULLIF(dm.material_name, '')), ba.material_code) AS category,
            SUM(ba.batch_inventory) AS inventory_amount,
            COUNT(*) AS record_count
        FROM batch_amounts ba
        LEFT JOIN dim_material_cache dm ON dm.material_code = ba.material_code
        GROUP BY ba.material_code
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


def get_category_bubble() -> Dict:
    """物料类别气泡图（页面 #/path2，按 material_group_code 统计库存/领用率/SKU）。

    数据来源：v_project_inventory_wide（批次去重）+ wms_material_group（类别名称）
    涉及字段：material_group_code、total_price、original_quantity、unit_price、
             total_outbound_quantity、material_code、batch_code
    """
    rows = query("""
        WITH distinct_inventory AS (
            SELECT DISTINCT ON (tenant_id, material_code, batch_code, COALESCE(inventory_code, ''))
                material_group_code, material_code, batch_code,
                total_price,
                original_quantity * unit_price   AS inbound_amt,
                total_outbound_quantity * unit_price AS claimed_amt
            FROM v_project_inventory_wide
        )
        SELECT
            material_group_code AS category_code,
            SUM(total_price) AS inventory_amount,
            SUM(inbound_amt) AS inbound_amount,
            SUM(claimed_amt) AS claimed_amount,
            COUNT(DISTINCT material_code) AS sku_count,
            COUNT(DISTINCT batch_code) AS record_count
        FROM distinct_inventory
        WHERE material_group_code IS NOT NULL
        GROUP BY material_group_code
        ORDER BY inventory_amount DESC
    """)
    rows = _rows_to_float(rows, "inventory_amount", "inbound_amount", "claimed_amount")

    cat_name_map: Dict[str, str] = {}
    cat_codes = [r["category_code"] for r in rows if r["category_code"]]
    if cat_codes:
        placeholders = ','.join(['%s'] * len(cat_codes))
        name_rows = query(f"""
            SELECT code, name FROM wms_material_group
            WHERE code IN ({placeholders}) AND del_flag = '0'
        """, tuple(cat_codes))
        cat_name_map = {r2["code"]: r2["name"] or r2["code"] for r2 in name_rows}

    top_n = 10
    top_rows = rows[:top_n]
    rest_amount = sum(r["inventory_amount"] for r in rows[top_n:])
    rest_inbound = sum(r["inbound_amount"] for r in rows[top_n:])
    rest_claimed = sum(r["claimed_amount"] for r in rows[top_n:])
    rest_sku = sum(int(r["sku_count"] or 0) for r in rows[top_n:])

    data = []
    for r in top_rows:
        amt = r["inventory_amount"]
        inb = r["inbound_amount"]
        clm = r["claimed_amount"]
        code = r["category_code"]
        data.append({
            "category_code": code,
            "category_name": cat_name_map.get(code, code or "未知"),
            "inventory_amount": round(amt, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else 0,
            "sku_count": int(r["sku_count"] or 0),
            "record_count": int(r["record_count"] or 0),
        })

    if rest_amount > 0:
        data.append({
            "category_code": "-",
            "category_name": "其他",
            "inventory_amount": round(rest_amount, 2),
            "claim_rate": round(rest_claimed / rest_inbound * 100, 2) if rest_inbound else 0,
            "sku_count": rest_sku,
            "record_count": 0,
        })
    return {"data": data}


def get_anomaly_daily(days: int = 30) -> Dict:
    """异常变动预警（页面 #/path1，近 12 周）。

    两个维度：
      1. 新项目：近 days 天内有「日常」维护项目创建
      2. 周度环比：本周领用 vs 上周领用，波动超 ±30% 预警

    数据来源：v_project_inventory_wide → 项目级明细 _get_inventory_rows()
    涉及字段：owner_project_code、create_date、project_name（含"日常"）、
             inbound_date、inbound_amount、claimed_amount
    """
    rows = _get_inventory_rows()
    today = dt_date.today()
    AMPLITUDE = 0.30

    new_cutoff = today - timedelta(days=days)
    proj_rows = query("""
        SELECT owner_project_code, MIN(create_date)::date AS first_date
        FROM v_project_inventory_wide
        WHERE owner_project_code IS NOT NULL
          AND project_name LIKE '%日常%'
        GROUP BY owner_project_code
    """)
    new_project_weeks: Set[str] = set()
    new_project_map: Dict[str, List[str]] = {}
    for r in proj_rows:
        fd = r["first_date"]
        if hasattr(fd, 'date'):
            fd = fd.date()
        if not fd or fd < new_cutoff:
            continue
        iso = fd.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        new_project_weeks.add(wk)
        new_project_map.setdefault(wk, []).append(r["owner_project_code"] or "(未命名)")

    cutoff = today - timedelta(weeks=16)
    week_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d is None or d < cutoff:
            continue
        if "日常" not in (r.get("project_name") or ""):
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        if week_key not in week_map:
            monday = d - timedelta(days=d.weekday())
            week_map[week_key] = {
                "inbound_amount": 0.0, "claimed_amount": 0.0, "monday": monday,
            }
        week_map[week_key]["inbound_amount"] += r["inbound_amount"]
        week_map[week_key]["claimed_amount"] += r["claimed_amount"]

    sorted_weeks = sorted(week_map.keys())
    data = []
    for i, week_key in enumerate(sorted_weeks):
        v = week_map[week_key]
        monday = v["monday"]
        sunday = monday + timedelta(days=6)
        date_label = f"{monday.month}/{monday.day}-{sunday.month}/{sunday.day}"

        cl_val = v["claimed_amount"]
        in_val = v["inbound_amount"]
        anomaly_parts: List[str] = []
        huanbi = None

        if week_key in new_project_weeks:
            proj_list = new_project_map.get(week_key, [])
            short = "、".join(proj_list[:2])
            if len(proj_list) > 2:
                short += f"等{len(proj_list)}个"
            anomaly_parts.append(f"新项目({short})")

        if i > 0:
            prev_cl = week_map[sorted_weeks[i - 1]]["claimed_amount"]
            if prev_cl > 0:
                huanbi = round((cl_val - prev_cl) / prev_cl * 100, 1)
                if abs(huanbi) > AMPLITUDE * 100:
                    arrow = "↑" if huanbi > 0 else "↓"
                    anomaly_parts.append(f"环比{arrow}{abs(huanbi)}%")

        data.append({
            "date": date_label,
            "inbound_amount": round(in_val / 10000, 2),
            "claimed_amount": round(cl_val / 10000, 2),
            "type": 1 if anomaly_parts else 0,
            "label": "、".join(anomaly_parts) if anomaly_parts else "正常",
            "huanbi": huanbi,
        })

    result = data[-12:] if len(data) > 12 else data
    result.reverse()
    return {"data": result}


def get_batch_digest() -> Dict:
    """批次消化进度（页面 #/path2，按入库批次 TOP 6 模拟逐月消化）。

    数据来源：v_project_inventory_wide（批次去重）
    涉及字段：batch_code、inbound_date、age_days、original_quantity、
             unit_price、total_price
    """
    rows = query("""
        WITH distinct_inventory AS (
            SELECT DISTINCT ON (tenant_id, material_code, batch_code, COALESCE(inventory_code, ''))
                batch_code, inbound_date, age_days,
                original_quantity * unit_price   AS inbound_amt,
                total_price                     AS remain_amt
            FROM v_project_inventory_wide
        )
        SELECT
            batch_code,
            MIN(inbound_date)::date AS first_inbound,
            SUM(inbound_amt) AS inbound_amt,
            SUM(remain_amt) AS remain_amt,
            ROUND(AVG(age_days)) AS avg_age_days
        FROM distinct_inventory
        WHERE batch_code IS NOT NULL
        GROUP BY batch_code
        ORDER BY inbound_amt DESC
        LIMIT 6
    """)
    rows = _rows_to_float(rows, "inbound_amt", "remain_amt", "avg_age_days")

    labels = ['入库月', '+1月', '+2月', '+3月', '+4月', '+5月', '+6月']
    colors = ['#3b82f6', '#f59e0b', '#f43f5e', '#10b981', '#8b5cf6', '#ec4899']
    series = []

    for idx, r in enumerate(rows):
        inbound = r["inbound_amt"] or 0
        remain = r["remain_amt"] or 0
        age_days = r["avg_age_days"] or 30

        total_remain_pct = remain / inbound * 100 if inbound > 0 else 100
        months = max(age_days / 30.0, 1)
        monthly_consume_rate = (100 - total_remain_pct) / months if months > 0 else 0

        data = [100]
        for m in range(1, 7):
            pct = max(0, round(100 - monthly_consume_rate * m, 1))
            data.append(pct)

        series.append({
            "batch_code": r["batch_code"],
            "inbound_wan": round(inbound / 10000, 2),
            "remain_pct": round(total_remain_pct, 1),
            "color": colors[idx % len(colors)],
            "data": data,
        })

    return {"labels": labels, "series": series}


# ================================================================
# 第五类：KPI 考核清单（页面 #/kpi-checklist）
#   K1-K3 核心考核、K4-K5 约束、K6-K9 结构分析、T1-T2 TOP
# ================================================================

def _status_for_rate(rate: float, target: float, direction: str = "up") -> str:
    """根据达成率与目标值判定指标状态（ok/warning/alert）。"""
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


def get_kpi_checklist() -> Dict[str, Any]:
    """KPI 考核清单（页面 #/kpi-checklist，完整版 K1-K9 + T1-T2）。

    四类指标：
      第一类 核心考核 K1-K3：
        K1 采购领用率（金额）   = 领用金额 / 入库金额 × 100%
        K2 当前库存金额         = Σ(current_quantity × unit_price) = v_total_price
        K3 长库龄库存金额占比   = 库龄≥365天金额 / 总库存
      第二类 约束 K4-K5：
        K4 未领用采购金额       = 入库金额 - 领用金额
        K5 项目未消耗库存       = Σ(owner_project_type='Q' 项目的 inventory_amount)
      第三类 结构分析 K6-K9：
        K6 库存结构（项目/采购人占比）
        K7 时间分析（平均库龄/未动用天数/库龄结构）
        K8 项目分析、K9 采购人分析
      第四类 TOP T1-T2（不考核）：
        T1 未领用库存 TOP10（金额）、T2 领用 TOP10（金额+数量）

    数据来源：v_project_inventory_wide + utils 数据获取层（批次去重 × project_ratio）
    涉及字段：original_quantity、unit_price、total_outbound_quantity、total_price、
             age_days、owner_project_code、owner_project_type、project_name、
             project_submitter、project_contact、purchaser_name、material_code
    """
    # ── Step 1: 拉取数据 ──
    agg = _get_wide_batch_aggregates(year=None)
    total_inbound_amt = agg["total_inbound_amount"]
    total_claimed_amt = agg["total_claimed_amount"]
    total_inventory_amt = agg["total_inventory_amount"]
    total_inbound_qty = agg["original_quantity"]
    total_outbound_qty = agg["total_outbound_quantity"]

    batch_rows = _get_batch_rows()
    inv_rows = _get_inventory_rows()
    structure_data = _get_wide_structure_aggregates()

    k8_projects = get_by_project()
    k5_projects = get_by_project(owner_project_type='Q')
    k9_purchasers = get_by_purchaser()

    # ── Step 2: 库龄结构 & 加权平均库龄 ──
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

    claim_rate_amt = round(total_claimed_amt / total_inbound_amt * 100, 2) if total_inbound_amt else 0.0
    claim_rate_qty = round(total_outbound_qty / total_inbound_qty * 100, 2) if total_inbound_qty else 0.0
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

    avg_age_days = round(age_weighted_sum / total_inventory_amt, 2) if total_inventory_amt else 0.0
    aged_ratio = round(aged_365_ratio, 4)

    # ── Step 3: 未动用天数 ──
    unused_weighted = 0.0
    unused_total_amt = 0.0
    total_inventory_qty = 0.0
    min_inbound_date = None
    max_inbound_date = None
    max_outbound_time = None

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
        ot = r.get("last_outbound_time")
        if ot is not None:
            if hasattr(ot, 'date'):
                ot = ot.date()
            if max_outbound_time is None or ot > max_outbound_time:
                max_outbound_time = ot
        total_inventory_qty += r["current_quantity"]
        if r["claimed_amount"] == 0 and r["current_quantity"] > 0:
            unused_weighted += inventory * age
            unused_total_amt += inventory

    unused_days = round(unused_weighted / unused_total_amt, 2) if unused_total_amt else 0.0

    # ── Step 4: 组装 KPI ──
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
                "note": "未领用金额 ≈ 当前库存金额（恒等式 inbound - claimed ≈ inventory）",
            },
        },
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
        "K3": {
            "key": "K3",
            "name": "长库龄库存金额占比（≥1年）",
            "formula": "库龄≥365天的库存金额 / 总库存金额 × 100%",
            "value": round(aged_ratio * 100, 2),
            "unit": "%",
            "target": "逐年下降",
            "target_value": None,
            "direction": "down",
            "status": "warning" if aged_ratio > 0.15 else "ok",
            "detail": {
                "aged_amount_1y_wan": round(sum(
                    age_amt[label] for label, lo, _ in AGE_BUCKETS if lo >= 365
                ) / 10000, 2),
                "avg_age_weighted_days": avg_age_days,
                "age_structure": age_structure,
                "note": "库龄 = CURRENT_DATE - COALESCE(inbound_date, create_date)",
            },
        },
    }

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
                "note": "未领用 = inbound - claimed，恒等式下 ≈ inventory",
            },
        },
        "K5": {
            "key": "K5",
            "name": "项目未消耗库存",
            "formula": "按项目汇总 inventory_amount（仅 owner_project_type='Q'）",
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
                "note": f"owner_project_type='Q' 项目共 {len(k5_projects)} 个",
            },
        },
    }

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
            "note": "金额来源于批次去重 × project_ratio",
        },
        "K7": {
            "key": "K7",
            "name": "时间分析",
            "description": "平均库龄、未动用天数、库龄结构",
            "avg_age_weighted_days": avg_age_days,
            "unused_days": unused_days,
            "age_structure": age_structure,
            "aged_ratio_1y": round(aged_ratio * 100, 2),
            "note": "未动用天数 = Σ(未动用库存金额×库龄)/Σ(未动用库存金额)，未动用=claimed=0且current_quantity>0",
        },
        "K8": {
            "key": "K8",
            "name": "项目分析",
            "description": "哪个项目带来库存 | 数据来源 get_by_project()",
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
            "key": "K9",
            "name": "采购人分析",
            "description": "采购人领用率、未消耗库存、库龄 | 数据来源 get_by_purchaser()",
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

    # ── Step 5: TOP 指标 T1-T2 ──
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
        if r["age_days"] > a["age_days"]:
            a["age_days"] = int(r["age_days"])
            a["project_code"] = r.get("project_code", "")
            a["project_name"] = r.get("project_name", "")
            a["purchaser_name"] = r.get("purchaser_name", "")

    sorted_by_inventory = sorted(mat_agg.values(), key=lambda x: x["inventory_amount"], reverse=True)
    t1_items = [
        {
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
        }
        for idx, r in enumerate(sorted_by_inventory[:10])
    ]

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

    # ── Step 6: Summary ──
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

    data_end = max_inbound_date
    if max_outbound_time is not None and (data_end is None or max_outbound_time > data_end):
        data_end = max_outbound_time

    summary = {
        "update_time": dt_date.today().strftime("%Y-%m-%d"),
        "data_start_date": min_inbound_date.strftime("%Y-%m-%d") if min_inbound_date else "",
        "data_end_date": data_end.strftime("%Y-%m-%d") if data_end else "",
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


# ================================================================
# 第六类：ERP 领用率（页面 #/kpi-checklist / #/indicator-overview / #/path1）
# ================================================================

def get_erp_claim_indicators() -> Dict:
    """ERP 版领用率指标（页面 #/kpi-checklist / #/indicator-overview / #/path1）。

    与 WMS 版（get_claim_indicators）的区别：
      ERP 统计所有历史凭证（含已消耗完批次）→ 领用率更真实；
      WMS 只统计当前有库存批次 → 领用率偏低。

    指标（当年 + 全部）：
      total_inbound_amount  101收货金额
      reversal_amount       102冲销金额
      net_inbound_amount    净入库（101+102）
      total_outbound_amount 出库金额（201/221/Z61）
      claim_rate_amount     领用率 = 出库 / 净入库 × 100%
      unclaimed_amount      未领用金额 = 净入库 - 出库
      erp_inventory         ERP当前库存（v_batch_lifecycle.best_inventory_amt）

    数据来源：erp_catalog_mb51（werks='2635'）+ v_batch_lifecycle
    涉及字段：bwart（移动类型）、row_json->>'DMBTR'（金额）、row_json->>'MENGE'（数量）、
             row_json->>'BLDAT'（凭证日期）、row_json->>'MATNR'（物料编码）、charg（批次）、
             best_inventory_amt（ERP当前库存）
    """
    current_year = dt_date.today().year
    sql = f"""
        SELECT
            COALESCE(SUM(CASE WHEN bwart = '101'
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0)     AS gross_inbound_all,
            COALESCE(SUM(CASE WHEN bwart = '102'
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0)    AS reversal_all,
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0)     AS net_inbound_all,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','Z61')
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0)    AS outbound_all,
            COALESCE(SUM(CASE WHEN bwart = '101'
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0)     AS gross_inbound_year,
            COALESCE(SUM(CASE WHEN bwart = '102'
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0)    AS reversal_year,
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0)     AS net_inbound_year,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','Z61')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0)    AS outbound_year,
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                THEN (row_json->>'MENGE')::numeric ELSE 0 END), 0)     AS inbound_qty_all,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','Z61')
                THEN -(row_json->>'MENGE')::numeric ELSE 0 END), 0)    AS outbound_qty_all,
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN (row_json->>'MENGE')::numeric ELSE 0 END), 0)     AS inbound_qty_year,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','Z61')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{current_year}'
                THEN -(row_json->>'MENGE')::numeric ELSE 0 END), 0)    AS outbound_qty_year
        FROM public.erp_catalog_mb51
        WHERE werks = '2635'
          AND row_json->>'MATNR' IS NOT NULL
          AND charg IS NOT NULL
    """
    rows = query(sql)
    agg = _rows_to_float(rows, *rows[0].keys())[0] if rows else {}

    inv_rows = query("""
        SELECT COALESCE(SUM(best_inventory_amt), 0) AS total
        FROM v_batch_lifecycle
    """)
    erp_inventory = round(_f(inv_rows[0]["total"]) / 10000, 2) if inv_rows else 0

    def _build(gross, reversal, net_inbound, outbound, inbound_qty, outbound_qty):
        unclaimed = net_inbound - outbound
        return {
            "total_inbound_amount": round(gross / 10000, 2),
            "reversal_amount": round(reversal / 10000, 2),
            "net_inbound_amount": round(net_inbound / 10000, 2),
            "total_outbound_amount": round(outbound / 10000, 2),
            "total_inbound_quantity": round(inbound_qty, 2),
            "total_outbound_quantity": round(outbound_qty, 2),
            "claim_rate_amount": round(outbound / net_inbound * 100, 2) if net_inbound > 0 else 0.0,
            "claim_rate_quantity": round(outbound_qty / inbound_qty * 100, 2) if inbound_qty > 0 else 0.0,
            "unclaimed_amount": round(unclaimed / 10000, 2),
            "unclaimed_amount_ratio": round(unclaimed / net_inbound * 100, 2) if net_inbound > 0 else 0.0,
        }

    return {
        "current_year": current_year,
        "year_start": f"{current_year}-01-01",
        "year_end": dt_date.today().isoformat(),
        "all": _build(
            agg.get("gross_inbound_all", 0), agg.get("reversal_all", 0),
            agg.get("net_inbound_all", 0), agg.get("outbound_all", 0),
            agg.get("inbound_qty_all", 0), agg.get("outbound_qty_all", 0),
        ),
        "year": _build(
            agg.get("gross_inbound_year", 0), agg.get("reversal_year", 0),
            agg.get("net_inbound_year", 0), agg.get("outbound_year", 0),
            agg.get("inbound_qty_year", 0), agg.get("outbound_qty_year", 0),
        ),
        "erp_inventory": erp_inventory,
        "note": "ERP数据(erp_catalog_mb51)，入库=101收货，出库=201+221+Z61",
    }


# ================================================================
# Flask 路由（对应五个页面的全部指标接口）
# ================================================================

app = Flask(__name__)


def ok(data):
    return jsonify({"code": 0, "data": data})


def _route(path, handler, **opts):
    app.add_url_rule(path, path.replace('/', '_').strip('_'), handler, methods=["GET"], **opts)


def _guard(fn):
    def wrapper(*a, **kw):
        try:
            return ok(fn(*a, **kw))
        except Exception as e:
            return jsonify({"code": -1, "msg": str(e)})
    wrapper.__name__ = fn.__name__
    return wrapper


# ── 核心汇总 ──
_route("/api/wms/indicators/summary", _guard(get_summary))
_route("/api/wms/indicators/claim", _guard(get_claim_indicators))
_route("/api/wms/indicators/structure", _guard(get_structure_indicators))
_route("/api/wms/indicators/time", _guard(get_time_indicators))

# ── 库龄分层 / 趋势 / 热力图 ──
def _age_layers():
    min_amount = request.args.get("min_amount", 0, type=float)
    min_age = request.args.get("min_age", 0, type=int)
    max_age = request.args.get("max_age", None, type=int)
    return get_age_layers(min_amount, min_age, max_age)
_route("/api/wms/indicators/age-layers", _guard(_age_layers))
_route("/api/wms/indicators/age/monthly", _guard(get_age_monthly))
_route("/api/wms/indicators/age/heatmap", _guard(get_age_heatmap))

# ── 维度 ──
_route("/api/wms/indicators/by-project", _guard(get_by_project))
_route("/api/wms/indicators/by-purchaser", _guard(get_by_purchaser))

# ── TOP ──
def _top_unclaimed_amount():
    return get_top_unclaimed_amount(request.args.get("limit", 10, type=int))
def _top_unclaimed_quantity():
    return get_top_unclaimed_quantity(request.args.get("limit", 10, type=int))
def _top_claimed_amount():
    return get_top_claimed_amount(request.args.get("limit", 10, type=int))
def _top_claimed_quantity():
    return get_top_claimed_quantity(request.args.get("limit", 10, type=int))
_route("/api/wms/indicators/top/unclaimed-amount", _guard(_top_unclaimed_amount))
_route("/api/wms/indicators/top/unclaimed-quantity", _guard(_top_unclaimed_quantity))
_route("/api/wms/indicators/top/claimed-amount", _guard(_top_claimed_amount))
_route("/api/wms/indicators/top/claimed-quantity", _guard(_top_claimed_quantity))

# ── 时序 & 专项 ──
def _claim_monthly():
    non_project = request.args.get("non_project", "0") == "1"
    return get_claim_monthly(non_project_only=non_project)
_route("/api/wms/indicators/claim/monthly", _guard(_claim_monthly))
_route("/api/wms/indicators/claim/yearly", _guard(get_claim_yearly))
_route("/api/wms/indicators/claim/daily", _guard(get_claim_daily))
_route("/api/wms/indicators/claim/weekly", _guard(get_claim_weekly))
_route("/api/wms/indicators/structure/by-category", _guard(get_structure_by_category))
_route("/api/wms/indicators/category/bubble", _guard(get_category_bubble))
_route("/api/wms/indicators/batch/digest", _guard(get_batch_digest))
def _anomaly_daily():
    return get_anomaly_daily(request.args.get("days", 30, type=int))
_route("/api/wms/indicators/anomaly/daily", _guard(_anomaly_daily))

# ── KPI 考核清单 ──
_route("/api/wms/indicators/kpi-checklist", _guard(get_kpi_checklist))

# ── ERP 领用率 ──
_route("/api/wms/indicators/erp-claim", _guard(get_erp_claim_indicators))


if __name__ == "__main__":
    print("=== BI 指标服务启动（五页面统一版）===")
    print("Address: http://0.0.0.0:5001")
    app.run(debug=True, host="0.0.0.0", port=5001, use_reloader=False)
