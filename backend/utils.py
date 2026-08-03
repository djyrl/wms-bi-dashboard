"""
采购库存 BI — 公共工具模块
===========================
提供数据库连接、查询辅助、批次级金额计算、项目分配等核心功能。

═══════════════════════════════════════════════════════════════════════════
金额计算标准（写入此模块文档，所有指标模块统一遵循）
═══════════════════════════════════════════════════════════════════════════

数据基础：v_project_inventory_wide 视图（基于 01_v_project_inventory_wide_optimized.sql）

视图核心聚合（inv_agg CTE）：
  v_total_price = SUM(current_quantity × unit_price)     — 当前库存真实价值
  v_unit_price  = SUM(current_quantity×unit_price) / SUM(current_quantity)
                  (当 current_quantity > 0 时，否则取 MAX(unit_price))
                  含义：按当前库存数量加权的平均单价

三个核心金额定义：
  入库金额    inbound_amount  = original_quantity × v_unit_price
                              含义：以当前加权均价重估原始入库数量
  领用金额    claimed_amount  = total_outbound_quantity × v_unit_price
                              含义：以当前加权均价重估累计出库数量
  库存金额    inventory_amount = v_total_price = SUM(current_quantity × unit_price)
                              含义：当前库存真实价值（视图直接给出）

会计恒等式：
  ✅ inbound ≈ claimed + inventory

  推导：
    inbound   = original_quantity × v_unit_price
              ≈ (current_quantity + total_outbound_quantity) × v_unit_price
              = current_quantity × v_unit_price + total_outbound_quantity × v_unit_price
              = inventory + claimed

  前提：original_quantity ≈ current_quantity + total_outbound_quantity
  验证依据：dim_outbound_log_cache 通过 wms_inventory_log 从 wms_inventory 关联填充，
           三者（原始量、当前量、出库量）共享同一数据源头 wms_inventory。
           实际可能存在微小偏差（变更类型覆盖不全、精度舍入等），偏差应在 1% 以内。

综合领用率：
  claim_rate = claimed_amount / inbound_amount × 100%
  含义：已领用金额占入库金额的比例。在恒等式成立时，等效于：
        total_outbound_quantity / original_quantity × 100%（金额比 ≈ 数量比）

项目级金额分配：
  批次金额 × project_ratio → 分配到各项目
  project_ratio 保证同一批次所有项目分配之和 = 1.0
  因此 Σ项目金额 = Σ批次金额（项目级汇总 = 批次级汇总）

库龄计算：
  age_days = CURRENT_DATE - COALESCE(inbound_date, create_date)
  来源：视图中的 age_days 字段，在 inv_agg 中使用 MIN(inbound_date) 取批次最早入库日期
  加权平均库龄 = SUM(inventory_amount × age_days) / SUM(inventory_amount)
  长库龄占比(≥1年) = SUM(inventory_amount WHERE age_days >= 365) / SUM(inventory_amount)

出库类型（来自 dim_outbound_log_cache，枚举值定义在 03_dim_cache_tables.sql）：
  change_type = 31 → pick_quantity      — 拣货出库
  change_type = 34 → repair_quantity    — 维修出库
  change_type = 35 → scrap_quantity     — 报废出库
  change_type = 36 → repaired_quantity  — 返修出库
  total_outbound_quantity = pick + repair + scrap + repaired

═══════════════════════════════════════════════════════════════════════════
视图膨胀问题 & 去重策略
═══════════════════════════════════════════════════════════════════════════

v_project_inventory_wide 的行膨胀路径：
  inv_agg（1行/批次，已按货位聚合）
    → LEFT JOIN wms_project_inventory (N行/批次，一个批次可能属于多个项目)
    → 视图最终有 N 行/批次（膨胀 N 倍）

所有聚合级别金额计算必须：
  1. 批次级：DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory) 去重
  2. 项目级：先批次去重得到批次金额，再 × project_ratio 分配到各项目
  3. 严禁直接在视图上 SUM(total_price)（会被膨胀行数放大） ⚠️
"""

import psycopg2
import psycopg2.extras
from typing import Any, Dict, List, Optional

from db_config import DB_CONFIG


# ================================================================
#  基础工具函数
# ================================================================

def _f(v) -> float:
    """
    安全转换为 float。
    如果值为 None，返回 0.0。

    Args:
        v: 输入值（可能是 None, Decimal, str, 或其他数字类型）

    Returns:
        float: 转换后的浮点数
    """
    if v is None:
        return 0.0
    return float(v)


def _rows_to_float(rows: List[Dict], *fields: str) -> List[Dict]:
    """
    将查询结果中指定的字段转换为 float 类型（原地修改）。
    用于处理 psycopg2 返回的 Decimal 等类型，确保后续计算的一致性。

    Args:
        rows:   查询结果列表，每项为 dict
        *fields: 需要转换的字段名（可以传多个）

    Returns:
        List[Dict]: 原地修改后的同一列表
    """
    for r in rows:
        for f in fields:
            if f in r:
                r[f] = _f(r[f])
    return rows


def get_db():
    """
    获取数据库连接。
    连接参数来自 db_config.DB_CONFIG。
    设置 autocommit = True，避免手动事务管理。

    Returns:
        psycopg2 connection 对象
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """
    执行 SELECT 查询，返回字典列表。
    使用 RealDictCursor 确保列名可读。
    每次调用独立获取和释放连接（连接用完即关）。

    Args:
        sql:    SQL 查询语句（支持 %s 占位符）
        params: 查询参数元组（可选）

    Returns:
        List[Dict]: 查询结果，每行为一个 dict（key 为列名）
    """
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
    """
    执行 SELECT 查询，只返回第一行。
    当确认结果只有一行时使用此方法。

    Args:
        sql:    SQL 查询语句
        params: 查询参数元组（可选）

    Returns:
        Dict or None: 第一行结果，无结果时返回 None
    """
    rows = query(sql, params)
    return rows[0] if rows else None


# ================================================================
#  批次级金额计算 CTE（所有金额聚合的统一来源）
#  ================================================================
#  作用：
#    1. 对 v_project_inventory_wide 按物理批次去重
#       DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
#    2. 计算三个核心金额：batch_inbound / batch_claimed / batch_inventory
#    3. 同时计算分项出库金额（pick / repair / scrap / repaired）
#    4. 提取库龄、日期、类别等维度字段
#
#  使用方式：
#    WITH _BATCH_AMOUNTS_SQL
#    后续在 batch_amounts 上做聚合或 JOIN 回视图做项目分配
# ================================================================

_BATCH_AMOUNTS_SQL = """
    batch_amounts AS (
        SELECT DISTINCT ON (tenant_id, material_code, batch_code, erp_inventory)
            -- 主键
            tenant_id,
            material_code,
            batch_code,
            erp_inventory                       AS inv_code,

            -- ★ 三个核心金额 —
            --   batch_inbound:  入库金额 = 原始数量 × 当前加权均价
            --   batch_claimed:  领用金额 = 总出库数量 × 当前加权均价
            --   batch_inventory: 库存金额 = total_price（视图 v_total_price）
            original_quantity * unit_price       AS batch_inbound,
            total_outbound_quantity * unit_price AS batch_claimed,
            total_price                         AS batch_inventory,

            -- ★ 分项出库金额（按出库类型拆分的领用金额）—
            --   四种出库类型：31=拣货, 34=维修, 35=报废, 36=返修
            --   金额 = 各项出库数量 × 当前加权均价
            --   恒等关系：batch_pick + batch_repair + batch_scrap + batch_repaired = batch_claimed
            pick_quantity * unit_price           AS batch_pick,
            repair_quantity * unit_price         AS batch_repair,
            scrap_quantity * unit_price          AS batch_scrap,
            repaired_quantity * unit_price       AS batch_repaired,

            -- 数量字段（用于数量级计算和校验）
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


# ================================================================
#  project_ratio — 项目金额分配因子
#  ================================================================
#  作用：将批次金额按比例分配到关联的各个项目
#
#  分配逻辑（按优先级）：
#    1. 批次没有项目台账行 → 100% 归属当前行（通常不会出现这种场景）
#    2. 有项目台账但所有项目数量为 0 → 项目间平均分配
#    3. 正常情况 → 按各项目的 pi_current_quantity 占该批次所有项目的总 pi_current_quantity 比例分配
#
#  核心性质：对同一个批次，所有 project_ratio 之和 = 1.0
#  因此：Σ(批次金额 × project_ratio) 对所有项目行 = 批次金额
# ================================================================

_PROJECT_RATIO_SQL = """
    CASE
        -- 该批次在项目台账中没有关联行 → 100%% 归属当前行
        WHEN COUNT(w.pi_current_quantity) OVER (
            PARTITION BY w.tenant_id, w.material_code, w.batch_code, w.erp_inventory
        ) = 0 THEN 1.0
        -- 有项目台账，但所有行的 pi_current_quantity 均为 0 → 平均分配
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


# ================================================================
#  数据获取函数
# ================================================================

def _date_filter_sql(start_date=None, end_date=None, table_alias="ba"):
    """
    生成日期区间过滤 SQL 片段（用于 WHERE 子句）。
    使用字符串插值（日期来自前端校验，安全），避免 psycopg2 的 % 转义问题。
    返回 SQL 片段字符串，无过滤时返回 ""。
    """
    col_prefix = f"{table_alias}." if table_alias else ""
    parts = []
    if start_date:
        parts.append(f"{col_prefix}inbound_date >= '{start_date}'::date")
    if end_date:
        parts.append(f"{col_prefix}inbound_date <= '{end_date}'::date")
    if not parts:
        return ""
    return " AND " + " AND ".join(parts)


def _get_inventory_rows(start_date=None, end_date=None) -> List[Dict]:
    """
    从 v_project_inventory_wide 获取库存明细（按项目展开）。

    金额计算流程（两步）：
      1. batch_amounts CTE — 按物理批次去重，计算批次级金额
         （inbound / claimed / inventory + 分项出库金额）
      2. JOIN 回视图的项目行，用 project_ratio 将批次金额分配到各项目

    返回列说明：
      - id:                   项目台账ID（project_inventory_id）
      - purchase_batch:       采购批次号（batch_code）
      - material_name / material_code: 物料信息
      - project_code / project_name:   项目信息
      - purchaser_name:       提报人（对应 project_submitter）
      - applicant_name:       申请人（对应 purchaser_name）
      - contact_name:         联系人（对应 project_contact）
      - project_type:         项目计划类别
      - inbound_date:         入库日期
      - batch_code:           批次号
      - original_quantity:    原始入库数量
      - current_quantity:     项目当前库存数量（pi_current_quantity）
      - used_quantity:        已领用数量（total_outbound × project_ratio）
      - pick_quantity:        拣货出库数量（× project_ratio）
      - repair_quantity:      维修出库数量（× project_ratio）
      - scrap_quantity:       报废出库数量（× project_ratio）
      - repaired_quantity:    返修出库数量（× project_ratio）
      - unit_price:           当前加权均价
      - unit:                 物料单位
      - supplier_code:        供应商编码
      - inbound_amount:       项目级入库金额 = 批次入库金额 × project_ratio
      - claimed_amount:       项目级领用金额 = 批次领用金额 × project_ratio
      - inventory_amount:     项目级库存金额 = 批次库存金额 × project_ratio
      - claim_rate:           领用率 = total_outbound / original × 100%（批次级，非项目级）
      - age_days:             库龄天数

    Returns:
        List[Dict]: 按项目展开的库存明细行列表（所有金额、数量已转为 float）
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        -- Step 2: 将批次金额 JOIN 回视图的项目行，计算 project_ratio
        wide_with_ratio AS (
            SELECT
                w.*,
                -- 批次级金额（来自去重后的 batch_amounts）
                ba.batch_inbound,
                ba.batch_claimed,
                ba.batch_inventory,
                ba.batch_orig_qty,
                ba.batch_outbound_qty,
                ba.batch_unit_price,
                ba.batch_age_days,
                -- 分项出库金额
                ba.batch_pick,
                ba.batch_repair,
                ba.batch_scrap,
                ba.batch_repaired,
                -- 项目分配因子（按 pi_current_quantity 占比）
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
            -- 基本信息
            r.project_inventory_id                  AS id,
            r.batch_code                            AS purchase_batch,
            r.material_name,
            r.material_code,
            r.owner_project_code                    AS project_code,
            r.project_name,
            r.project_submitter                     AS purchaser_name,  -- 提报人（采购归属）
            r.purchaser_name                        AS applicant_name,   -- 申请人
            r.project_contact                       AS contact_name,     -- 联系人
            r.plan_category                         AS project_type,
            r.inbound_date::date                    AS inbound_date,
            r.putaway_date::date                    AS putaway_date,
            r.batch_code,

            -- 数量字段
            r.original_quantity,
            r.pi_current_quantity                   AS current_quantity,

            -- ★ 分项出库数量 = 视图中的各类型出库量 × project_ratio —
            --   各类型独立计算，不再全部填 total_outbound_quantity
            --   四种出库类型：31=拣货(pick), 34=维修(repair), 35=报废(scrap), 36=返修(repaired)
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

            -- 单价 & 物料单位
            r.batch_unit_price                      AS unit_price,
            r.material_unit                         AS unit,
            r.supplier_code,

            -- ★ 项目级金额 = 批次金额 × 项目占比 —
            --   恒等式：∑(所有项目) = 批次金额
            ROUND((r.batch_inbound
                   * r.project_ratio)::numeric, 2)  AS inbound_amount,
            ROUND((r.batch_claimed
                   * r.project_ratio)::numeric, 2)  AS claimed_amount,
            ROUND((r.batch_inventory
                   * r.project_ratio)::numeric, 2)  AS inventory_amount,

            -- 领用率（批次级指标，同一个批次的每个项目行返回相同值）
            --   公式：total_outbound / original × 100，上限 100%
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

            -- 库龄（批次级，视图中的 age_days）
            r.batch_age_days                        AS age_days
        FROM wide_with_ratio r
    """)
    return _rows_to_float(rows,
        "original_quantity", "current_quantity", "used_quantity",
        "pick_quantity", "repair_quantity", "scrap_quantity", "repaired_quantity",
        "unit_price", "inbound_amount", "claimed_amount",
        "inventory_amount", "claim_rate", "age_days")


def _get_batch_rows(start_date=None, end_date=None) -> List[Dict]:
    """
    获取批次级明细（物理去重后，不做项目分配）。
    用于需要逐批次迭代的场景（如 age_structure、summary 聚合）。

    返回的每一行对应一个独立的物理批次（tenant_id + material_code + batch_code + erp_inventory）。

    返回列说明：
      - inbound_amount:    批次入库金额
      - claimed_amount:    批次领用金额（total_outbound × unit_price）
      - inventory_amount:  批次库存金额（total_price = v_total_price）
      - original_quantity: 原始入库数量
      - used_quantity:     总出库数量
      - pick_quantity:     拣货出库数量
      - repair_quantity:   维修出库数量
      - scrap_quantity:    报废出库数量
      - repaired_quantity: 返修出库数量
      - unit_price:        当前加权均价
      - age_days:          库龄天数
      - inbound_date:      入库日期
      - material_group_code: 物料组类别编码

    Returns:
        List[Dict]: 批次级明细行列表（所有金额、数量已转为 float）
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            -- 三个核心金额
            batch_inbound   AS inbound_amount,
            batch_claimed   AS claimed_amount,
            batch_inventory AS inventory_amount,

            -- 数量字段
            batch_orig_qty      AS original_quantity,
            batch_outbound_qty  AS used_quantity,
            batch_current_qty   AS current_quantity,

            -- ★ 分项出库数量 —
            --   直接从 batch_amounts 获取，未经 project_ratio 分配
            batch_pick          AS pick_quantity,
            batch_repair        AS repair_quantity,
            batch_scrap         AS scrap_quantity,
            batch_repaired      AS repaired_quantity,

            -- 单价 & 库龄 & 日期 & 类别
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
    """
    按物理批次去重聚合，返回核心金额汇总。

    不区分项目归属，返回的是所有批次的绝对总额。
    若指定 year，只统计 inbound_date 在该自然年的批次。
    若指定 start_date / end_date，只统计该区间内入库的批次。

    Args:
        year:       可选，只统计该自然年入库的批次。None 表示全部批次。
        start_date: 可选，入库日期下限（'YYYY-MM-DD'）
        end_date:   可选，入库日期上限（'YYYY-MM-DD'）

    Returns:
        Dict 包含以下键：
          - total_inbound_amount:    入库总额（元）
          - total_claimed_amount:    领用总额（元）
          - total_inventory_amount:  库存总额（元）
          - original_quantity:       原始总数量
          - total_outbound_quantity: 总出库数量
          - total_pick_amount:       拣货领用额（元）
          - total_repair_amount:     维修领用额（元）
          - total_scrap_amount:      报废领用额（元）
          - total_repaired_amount:   返修领用额（元）
    """
    date_clause = _date_filter_sql(start_date, end_date, table_alias="")
    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            -- 三个核心汇总
            COALESCE(SUM(batch_inbound), 0)   AS total_inbound_amount,
            COALESCE(SUM(batch_claimed), 0)   AS total_claimed_amount,
            COALESCE(SUM(batch_inventory), 0) AS total_inventory_amount,
            -- 数量汇总
            COALESCE(SUM(batch_orig_qty), 0)      AS original_quantity,
            COALESCE(SUM(batch_outbound_qty), 0)  AS total_outbound_quantity,
            COALESCE(SUM(batch_current_qty), 0)   AS total_current_quantity,
            -- ★ 分项出库金额汇总 —
            COALESCE(SUM(batch_pick), 0)       AS total_pick_amount,
            COALESCE(SUM(batch_repair), 0)     AS total_repair_amount,
            COALESCE(SUM(batch_scrap), 0)      AS total_scrap_amount,
            COALESCE(SUM(batch_repaired), 0)   AS total_repaired_amount
        FROM batch_amounts
        WHERE (%s IS NULL OR EXTRACT(YEAR FROM inbound_date) = %s){date_clause}
    """
    rows = query(sql, (year, year))
    if not rows:
        # 无数据时返回全 0
        return {
            "total_inbound_amount": 0.0,
            "total_claimed_amount": 0.0,
            "total_inventory_amount": 0.0,
            "original_quantity": 0.0,
            "total_outbound_quantity": 0.0,
            "total_current_quantity": 0.0,
            "total_pick_amount": 0.0,
            "total_repair_amount": 0.0,
            "total_scrap_amount": 0.0,
            "total_repaired_amount": 0.0,
        }
    return _rows_to_float(rows, *rows[0].keys())[0]


def _get_wide_structure_aggregates(start_date=None, end_date=None) -> Dict[str, List[Dict]]:
    """
    按项目和采购人聚合库存金额（项目分摊后）。

    金额来源：批次去重 × project_ratio 分配。
    此方法用于库存结构分析：回答「哪些项目/采购人贡献了库存」。

    Args:
        start_date: 可选，入库日期下限（'YYYY-MM-DD'）
        end_date:   可选，入库日期上限（'YYYY-MM-DD'）

    Returns:
        Dict 包含两个键：
          - project_rows:   [{owner_project_code, project_name, inventory_amount}, ...]
                            按 inventory_amount 降序排列
          - purchaser_rows: [{purchaser_name, inventory_amount}, ...]
                            按 inventory_amount 降序排列
                            注意：此处的 purchaser_name 对应 project_submitter（提报人）
    """
    date_clause = _date_filter_sql(start_date, end_date)
    # ── 按项目聚合库存金额 ──
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

    # ── 按联系人聚合库存金额 ──
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
