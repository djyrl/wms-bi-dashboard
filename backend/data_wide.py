"""
===============================================================================
采购库存 BI — 明细宽表（WMS × ERP 批次级联）数据模块
===============================================================================
本模块实现「方案 B」：把 WMS 批次明细与 ERP 批次级出入库数据在批次维度对齐，
输出一张「一行一个（批次 × 项目）」的宽表，供 `#/data-table` 明细追溯使用。

数据来源（两个系统，在批次维度对齐）：
  1. WMS 侧 —— v_project_inventory_wide（基于 01_v_project_inventory_wide_optimized.sql）
     · 物理库存（wms_inventory）、项目台账（wms_project_inventory）、
       物料维度（dim_material_cache）、项目维度（dim_project_cache）、
       出库日志（dim_outbound_log_cache）
     · 提供：当前加权均价、入库/领用/库存金额、库龄、项目分摊因子、数量等
  2. ERP 侧 —— public.erp_catalog_mb51（ERP 物料凭证，plant=2635，2021-05 至今）
     · JSONB 字段 row_json：DMBTR=金额(元，带正负号)、MENGE=数量、BLDAT=凭证日期、MATNR=物料编码
     · 批次列：charg（ERP 批次）↔ WMS batch_code
     · 移动类型 bwart：
         101            = 收货（入库，正）
         102            = 冲销（收货的冲销，负）
         201/221/Z61 = 出库（负）
  3. v_batch_lifecycle —— 批次生命周期视图（一个批次一行）
     · best_inventory_amt = 最佳估计库存金额（WMS 优先，其次 ERP 账面，不为负）

匹配键：ERP charg ↔ WMS batch_code（再加 material_code 双字段，与 v_batch_lifecycle 一致）

关键口径约定：
  · 本模块所有金额统一为「元」（与 inventory-report 一致，不做 ÷10000）
  · ERP 收货/冲销/净入库/出库 均为「批次级」（同一批次的多项目行会重复同一值），
    项目级 = 批次级 × project_ratio（由调用方按需相乘）
  · 净入库 = 101 + 102（102 天然为负，直接相加即得净额）
  · 出库 = 201/221/Z61（DMBTR 为负，取 -DMBTR 转成正数）
  · 当年 = BLDAT 前 4 位 = 目标年份
===============================================================================
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

# 复用公共工具：数据库查询、金额转换、批次金额 CTE、项目分摊因子 SQL
from utils import query, _f, _rows_to_float, _BATCH_AMOUNTS_SQL, _PROJECT_RATIO_SQL


# ================================================================
#  基础工具（本地实现 query_one，避免额外 import）
# ================================================================

def query_one(sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    """执行 SELECT 并返回第一行，无结果返回 None。"""
    rows = query(sql, params)
    return rows[0] if rows else None


# ================================================================
#  ERP 批次级出入库金额 CTE（全部历史 + 当年）
# ================================================================
#  作用：把 erp_catalog_mb51 按 (material_code, charg) 聚合成「一个批次一行」，
#       一次性算出 收货 / 冲销 / 净入库 / 出库 的「全部历史」和「当年」共 8 个金额。
#
#  与 erp_inventory.py 的 _query_erp_claim_aggregates 口径一致，
#  区别是：那里是「全库汇总」（无 GROUP BY 批次），这里是「按批次 GROUP BY」。
# ================================================================

def _erp_batch_wide_cte(year: int) -> str:
    """返回 erp_batch_wide CTE 片段（含 'erp_batch_wide AS (...)'）。"""
    return f"""
    erp_batch_wide AS (
        SELECT
            row_json->>'MATNR' AS material_code,   -- 物料编码
            charg              AS batch_code,      -- 批次（对应 WMS batch_code）

            -- —— 全部历史（不按年过滤）——
            -- 收货金额：移动类型 101，DMBTR 为正，直接 SUM
            COALESCE(SUM(CASE WHEN bwart = '101'
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS recv_all,
            -- 冲销金额：移动类型 102，DMBTR 为负，取 -DMBTR 转成正数（绝对值）
            COALESCE(SUM(CASE WHEN bwart = '102'
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS reversal_all,
            -- 净入库金额：101 + 102（102 天然为负，直接相加即净额）
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS net_in_all,
            -- 出库金额：201/221/Z61，DMBTR 为负，取 -DMBTR 转成正数
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','Z61')
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS out_all,

            -- —— 当年（BLDAT 前 4 位 = 目标年份）——
            COALESCE(SUM(CASE WHEN bwart = '101'
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{year}'
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS recv_year,
            COALESCE(SUM(CASE WHEN bwart = '102'
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{year}'
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS reversal_year,
            COALESCE(SUM(CASE WHEN bwart IN ('101','102')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{year}'
                THEN (row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS net_in_year,
            COALESCE(SUM(CASE WHEN bwart IN ('201','221','Z61')
                    AND SUBSTRING(row_json->>'BLDAT', 1, 4) = '{year}'
                THEN -(row_json->>'DMBTR')::numeric ELSE 0 END), 0) AS out_year
        FROM public.erp_catalog_mb51
        WHERE werks = '2635'
          AND row_json->>'MATNR' IS NOT NULL
          AND charg IS NOT NULL
        GROUP BY row_json->>'MATNR', charg
    )
    """


# ================================================================
#  排序 / 筛选 白名单
# ================================================================

# 允许用于排序的列（SELECT 输出别名 → 实际排序列），防注入
ALLOWED_SORT_COLUMNS = {
    "claim_rate": "claim_rate",
    "age_days": "age_days",
    "inventory_amount": "inventory_amount",
    "inbound_amount": "inbound_amount",
    "inbound_date": "inbound_date",
    # 新增 ERP 金额 / 最佳估计库存 可排序
    "erp_recv_all": "erp_recv_all",
    "erp_net_in_all": "erp_net_in_all",
    "erp_out_all": "erp_out_all",
    "erp_recv_year": "erp_recv_year",
    "erp_net_in_year": "erp_net_in_year",
    "erp_out_year": "erp_out_year",
    "best_inventory_amt": "best_inventory_amt",
}

# 允许用于 ILIKE 子串筛选的列（文本类为主，防注入）
FILTERABLE_COLUMNS = {
    "purchase_batch", "material_name", "material_code", "project_code",
    "project_name", "purchaser_name", "submitter_name", "contact_name",
    "project_type", "owner_project_type", "material_group_code",
    "inbound_date", "putaway_date", "batch_code",
    "unit", "supplier_code",
}


def _build_wide_report_where(filters: Optional[Dict[str, str]]) -> Tuple[str, List[str]]:
    """
    根据 filters 生成 WHERE 子句与参数列表。
    对 base 别名 b 的列做 `::text ILIKE '%value%'` 子串匹配（忽略大小写）。
    非法列名直接忽略，防止 SQL 注入。
    """
    if not filters:
        return "", []
    parts: List[str] = []
    params: List[str] = []
    for key, val in filters.items():
        if val is None:
            continue
        val = str(val).strip()
        if not val:
            continue
        if key not in FILTERABLE_COLUMNS:
            continue
        parts.append(f'b."{key}"::text ILIKE %s')
        params.append(f"%{val}%")
    where = " WHERE " + " AND ".join(parts) if parts else ""
    return where, params


# ================================================================
#  明细宽表主查询（共用 CTE，避免主查询与 count 查询各写一遍）
# ================================================================
#  CTE 结构：
#    batch_amounts   —— WMS 批次级去重 + 三个核心金额（来自 utils._BATCH_AMOUNTS_SQL）
#    erp_batch_wide  —— ERP 批次级出入库（收货/冲销/净入库/出库，全部+当年）
#    wide_with_ratio —— 把 batch_amounts、erp_batch_wide、v_batch_lifecycle
#                       JOIN 回 v_project_inventory_wide 的项目行，
#                       并计算 project_ratio（项目分摊因子）
#    base            —— 对外暴露的最终列（排序/过滤都作用在 base 别名 b 上）
# ================================================================

def _build_wide_sql(year: int) -> Tuple[str, str]:
    """
    生成明细查询与 count 查询共用的两个片段：
      1. `common`：WITH CTE + base 定义（含 SELECT 列清单）
      2. 通过 base 别名 b 做 WHERE/ORDER/LIMIT/OFFSET

    返回 (common_sql, 无) —— 实际返回两个字符串：cte_with_base 与 base_select 已合并。
    为便于组装，这里直接返回一段「WITH ... base AS (...)」公共前缀。
    """
    # —— ERP 批次 CTE ——
    erp_cte = _erp_batch_wide_cte(year)

    # —— base 列清单（最终对外字段，含中文注释）——
    base_select = """
        SELECT
            -- ==================== WMS 标识 / 维度 ====================
            r.project_inventory_id                  AS id,                 -- 项目台账ID
            r.batch_code                            AS purchase_batch,     -- 采购批次（=批次编码）
            r.material_name,                                                 -- 物料名称
            r.material_code,                                                 -- 物料编码
            r.material_group_code,                                           -- 物料类别编码（类别气泡图/库龄热力图）
            r.owner_project_code                    AS project_code,        -- 项目编码
            r.project_name,                                                  -- 项目名称
            r.plan_category                         AS project_type,        -- 项目类型（计划类别）
            r.owner_project_type,                                            -- 项目类型（台账口径，K5 Q类项目筛选用）
            r.purchaser_name,                                                -- 采购人（采购员）
            r.project_submitter                     AS submitter_name,      -- 提报人（提交人）
            r.project_contact                       AS contact_name,        -- 联系人（项目负责人）
            r.inbound_date::date                    AS inbound_date,        -- 入库日期（批次最早）
            r.putaway_date::date                    AS putaway_date,        -- 上架日期（批次最晚）
            r.batch_code,                                                    -- 批次编码

            -- ==================== 数量字段 ====================
            r.original_quantity,                                             -- 原始入库数量（批次级）
            r.pi_current_quantity                   AS current_quantity,     -- 项目当前库存数量
            -- 分项出库数量 = 视图各类出库量 × project_ratio（项目级）
            --   31=拣货 34=维修 35=报废 36=返修，total_outbound = 四者之和
            ROUND((r.total_outbound_quantity
                   * r.project_ratio)::numeric, 4)  AS used_quantity,       -- 已出库数量合计
            ROUND((r.pick_quantity
                   * r.project_ratio)::numeric, 4)  AS pick_quantity,       -- 领用（拣货）数量
            ROUND((r.repair_quantity
                   * r.project_ratio)::numeric, 4)  AS repair_quantity,     -- 维修出库数量
            ROUND((r.scrap_quantity
                   * r.project_ratio)::numeric, 4)  AS scrap_quantity,      -- 报废出库数量
            ROUND((r.repaired_quantity
                   * r.project_ratio)::numeric, 4)  AS repaired_quantity,   -- 返修出库数量

            -- ==================== 单价 / 单位 / 供应商 ====================
            r.batch_unit_price                      AS unit_price,          -- 当前加权均价（Σqty×price/Σqty）
            r.material_unit                         AS unit,                -- 物料单位
            r.supplier_code,                                                 -- 供应商编码

            -- ==================== WMS 金额（项目分摊后） ====================
            -- 项目级金额 = 批次金额 × project_ratio，Σ(所有项目) = 批次金额
            ROUND((r.batch_inbound
                   * r.project_ratio)::numeric, 2)  AS inbound_amount,      -- 入库金额
            ROUND((r.batch_claimed
                   * r.project_ratio)::numeric, 2)  AS claimed_amount,      -- 领用金额（出库口径）
            ROUND((r.batch_inventory
                   * r.project_ratio)::numeric, 2)  AS inventory_amount,    -- 库存金额
            ROUND(r.project_ratio::numeric, 6)      AS project_ratio,       -- 项目分摊因子（每批次和=1.0）

            -- ==================== 领用率 / 库龄 ====================
            -- 领用率（数量口径，批次级）：出库量 / 原始量 × 100，上限 100
            CASE WHEN r.batch_orig_qty > 0
                 THEN LEAST(ROUND(r.batch_outbound_qty::numeric
                          / r.batch_orig_qty * 100, 2), 100.00)
                 ELSE 0
            END                                     AS claim_rate,
            r.batch_age_days                        AS age_days,            -- 库龄（天）

            -- ==================== ERP 金额（批次级，元） ====================
            -- 注意：以下 8 个字段是「批次级」，同一批次多项目行会重复同一值。
            --   项目级 = 批次级 × project_ratio（由调用方按需相乘）。
            COALESCE(r.recv_all, 0)                 AS erp_recv_all,        -- 全部历史收货金额(101)
            COALESCE(r.reversal_all, 0)             AS erp_reversal_all,    -- 全部历史冲销金额(102,取绝对值)
            COALESCE(r.net_in_all, 0)               AS erp_net_in_all,      -- 全部历史净入库金额(101+102)
            COALESCE(r.out_all, 0)                  AS erp_out_all,         -- 全部历史出库金额(201/221/Z61)
            COALESCE(r.recv_year, 0)                AS erp_recv_year,       -- 当年收货金额(101)
            COALESCE(r.reversal_year, 0)            AS erp_reversal_year,   -- 当年冲销金额(102,取绝对值)
            COALESCE(r.net_in_year, 0)              AS erp_net_in_year,     -- 当年净入库金额(101+102)
            COALESCE(r.out_year, 0)                 AS erp_out_year,        -- 当年出库金额(201/221/Z61)

            -- ==================== 最佳估计库存 ====================
            -- 来自 v_batch_lifecycle：WMS 有实物库存取 WMS，否则取 ERP 账面（且不为负）
            COALESCE(r.best_inventory_amt, 0)       AS best_inventory_amt   -- 最佳估计库存金额(元)
        FROM wide_with_ratio r
    """

    common = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        {erp_cte},
        wide_with_ratio AS (
            SELECT
                w.*,
                -- WMS 批次级金额（来自去重后的 batch_amounts）
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
                -- 项目分摊因子（按 pi_current_quantity 占比）
                {_PROJECT_RATIO_SQL} AS project_ratio,
                -- ERP 批次级金额（LEFT JOIN，无 ERP 记录时为 NULL → COALESCE 0）
                e.recv_all,
                e.reversal_all,
                e.net_in_all,
                e.out_all,
                e.recv_year,
                e.reversal_year,
                e.net_in_year,
                e.out_year,
                -- 最佳估计库存（批次级）
                bl.best_inventory_amt
            FROM v_project_inventory_wide w
            JOIN batch_amounts ba ON
                ba.tenant_id = w.tenant_id
                AND ba.material_code = w.material_code
                AND ba.batch_code IS NOT DISTINCT FROM w.batch_code
            LEFT JOIN erp_batch_wide e ON
                e.material_code = w.material_code
                AND e.batch_code = w.batch_code
            LEFT JOIN v_batch_lifecycle bl ON
                bl.material_code = w.material_code
                AND bl.batch_code = w.batch_code
        ),
        base AS ({base_select})
    """
    return common


# ================================================================
#  明细宽表主入口
# ================================================================

def get_inventory_wide_report(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
    limit: int = 500,
    offset: int = 0,
    filters: Optional[Dict[str, str]] = None,
    year: Optional[int] = None,
) -> Dict:
    """
    采购批次明细宽表（WMS × ERP 批次级联）。

    返回「一行一个（批次 × 项目）」的宽表，每个字段含义见 _build_wide_sql 中的注释。

    Args:
        sort_by:    排序字段（见 ALLOWED_SORT_COLUMNS），默认 inventory_amount
        sort_order: 排序方向 asc/desc，默认 desc
        limit:      返回条数，默认 500
        offset:     偏移量，默认 0
        filters:    {列别名: 子串}，对文本列做 ILIKE 匹配，AND 组合
        year:       用于「当年」ERP 金额的年份，默认当前自然年

    Returns:
        {
            "total": 总行数,
            "limit": 分页大小,
            "offset": 偏移量,
            "current_year": 当年年份,
            "summary": {
                # WMS 汇总（元）
                "total_inbound": ..., "total_claimed": ..., "total_inventory": ...,
                # ERP 汇总（元）
                "erp_recv_all": ..., "erp_reversal_all": ..., "erp_net_in_all": ..., "erp_out_all": ...,
                "erp_recv_year": ..., "erp_reversal_year": ..., "erp_net_in_year": ..., "erp_out_year": ...,
                # 最佳估计库存总额（元）
                "best_inventory_total": ...
            },
            "rows": [ { 33 个字段 }, ... ]
        }
    """
    current_year = year or date.today().year

    # 安全校验排序字段
    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, "inventory_amount")
    order_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

    # 生成筛选 WHERE（作用于 base 别名 b）
    where_sql, where_params = _build_wide_report_where(filters)

    common = _build_wide_sql(current_year)

    # —— 汇总金额（WMS + ERP + 最佳估计库存，一次查询拿到全部）——
    erp_cte = _erp_batch_wide_cte(current_year)
    summary_row = query_one(f"""
        WITH {_BATCH_AMOUNTS_SQL},
        {erp_cte}
        SELECT
            -- WMS 三个核心汇总（元）
            COALESCE((SELECT SUM(batch_inbound) FROM batch_amounts), 0)   AS total_inbound,
            COALESCE((SELECT SUM(batch_claimed) FROM batch_amounts), 0)   AS total_claimed,
            COALESCE((SELECT SUM(batch_inventory) FROM batch_amounts), 0) AS total_inventory,
            -- ERP 汇总（元）
            COALESCE((SELECT SUM(recv_all) FROM erp_batch_wide), 0)       AS erp_recv_all,
            COALESCE((SELECT SUM(reversal_all) FROM erp_batch_wide), 0)   AS erp_reversal_all,
            COALESCE((SELECT SUM(net_in_all) FROM erp_batch_wide), 0)     AS erp_net_in_all,
            COALESCE((SELECT SUM(out_all) FROM erp_batch_wide), 0)        AS erp_out_all,
            COALESCE((SELECT SUM(recv_year) FROM erp_batch_wide), 0)      AS erp_recv_year,
            COALESCE((SELECT SUM(reversal_year) FROM erp_batch_wide), 0)  AS erp_reversal_year,
            COALESCE((SELECT SUM(net_in_year) FROM erp_batch_wide), 0)    AS erp_net_in_year,
            COALESCE((SELECT SUM(out_year) FROM erp_batch_wide), 0)       AS erp_out_year,
            -- 最佳估计库存总额（元）
            COALESCE((SELECT SUM(best_inventory_amt) FROM v_batch_lifecycle), 0) AS best_inventory_total
    """)

    # —— 明细数据 ——
    sql = f"""
        {common}
        SELECT *
        FROM base b
        {where_sql}
        ORDER BY {sort_col} {order_dir} NULLS LAST
        LIMIT %s OFFSET %s
    """
    rows = query(sql, (*where_params, limit, offset))

    # —— 总行数（与数据查询同 JOIN + 筛选，保证分页 total 一致）——
    count_sql = f"""
        {common}
        SELECT COUNT(*) AS total
        FROM base b
        {where_sql}
    """
    total_row = query_one(count_sql, tuple(where_params))
    total = int(total_row["total"]) if total_row else 0

    # 数值字段统一转 float
    rows = _rows_to_float(rows,
        "original_quantity", "current_quantity", "used_quantity",
        "pick_quantity", "repair_quantity", "scrap_quantity", "repaired_quantity",
        "unit_price", "inbound_amount", "claimed_amount", "inventory_amount",
        "project_ratio", "claim_rate", "age_days",
        "erp_recv_all", "erp_reversal_all", "erp_net_in_all", "erp_out_all",
        "erp_recv_year", "erp_reversal_year", "erp_net_in_year", "erp_out_year",
        "best_inventory_amt")

    # 汇总字段统一转 float
    summary_float = _rows_to_float([summary_row], *summary_row.keys())[0] if summary_row else {}

    def _round(v, n):
        return round(_f(v), n)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "current_year": current_year,
        "summary": {
            # WMS 汇总（元）
            "total_inbound": _round(summary_float.get("total_inbound"), 2),       # 入库金额合计
            "total_claimed": _round(summary_float.get("total_claimed"), 2),       # 领用金额合计
            "total_inventory": _round(summary_float.get("total_inventory"), 2),   # 库存金额合计
            # ERP 汇总（元）
            "erp_recv_all": _round(summary_float.get("erp_recv_all"), 2),         # 全部收货
            "erp_reversal_all": _round(summary_float.get("erp_reversal_all"), 2), # 全部冲销
            "erp_net_in_all": _round(summary_float.get("erp_net_in_all"), 2),     # 全部净入库
            "erp_out_all": _round(summary_float.get("erp_out_all"), 2),           # 全部出库
            "erp_recv_year": _round(summary_float.get("erp_recv_year"), 2),       # 当年收货
            "erp_reversal_year": _round(summary_float.get("erp_reversal_year"), 2),  # 当年冲销
            "erp_net_in_year": _round(summary_float.get("erp_net_in_year"), 2),   # 当年净入库
            "erp_out_year": _round(summary_float.get("erp_out_year"), 2),         # 当年出库
            # 最佳估计库存总额（元）
            "best_inventory_total": _round(summary_float.get("best_inventory_total"), 2),
        },
        "rows": [
            {
                # ==================== WMS 标识 / 维度 ====================
                "id": r["id"],
                "purchase_batch": r["purchase_batch"] or "",
                "material_name": r["material_name"] or "",
                "material_code": r["material_code"] or "",
                "project_code": r["project_code"] or "",
                "project_name": r["project_name"] or "",
                "project_type": r["project_type"] or "",
                "owner_project_type": r.get("owner_project_type") or "",   # 项目类型（台账口径）
                "material_group_code": r.get("material_group_code") or "", # 物料类别编码
                "purchaser_name": r["purchaser_name"] or "",          # 采购人（采购员）
                "submitter_name": r["submitter_name"] or "",          # 提报人（提交人）
                "contact_name": r["contact_name"] or "",              # 联系人（项目负责人）
                "inbound_date": str(r["inbound_date"]) if r["inbound_date"] else "",
                "putaway_date": str(r["putaway_date"]) if r.get("putaway_date") else "",
                "batch_code": r["batch_code"] or "",

                # ==================== 数量 ====================
                "original_quantity": _round(r["original_quantity"], 4),
                "current_quantity": _round(r["current_quantity"], 4),
                "used_quantity": _round(r["used_quantity"], 4),
                "pick_quantity": _round(r.get("pick_quantity", 0), 4),
                "repair_quantity": _round(r.get("repair_quantity", 0), 4),
                "scrap_quantity": _round(r.get("scrap_quantity", 0), 4),
                "repaired_quantity": _round(r.get("repaired_quantity", 0), 4),

                # ==================== 单价 / 单位 / 供应商 ====================
                "unit_price": _round(r["unit_price"], 4),             # 当前加权均价
                "unit": r.get("unit") or "",
                "supplier_code": r.get("supplier_code") or "",

                # ==================== WMS 金额（项目分摊后） ====================
                "inbound_amount": _round(r["inbound_amount"], 2),
                "claimed_amount": _round(r["claimed_amount"], 2),
                "inventory_amount": _round(r["inventory_amount"], 2),
                "project_ratio": _round(r["project_ratio"], 6),       # 项目分摊因子

                # ==================== 领用率 / 库龄 ====================
                "claim_rate": _round(r["claim_rate"], 2),
                "age_days": r["age_days"] or 0,

                # ==================== ERP 金额（批次级，元） ====================
                "erp_recv_all": _round(r["erp_recv_all"], 2),
                "erp_reversal_all": _round(r["erp_reversal_all"], 2),
                "erp_net_in_all": _round(r["erp_net_in_all"], 2),
                "erp_out_all": _round(r["erp_out_all"], 2),
                "erp_recv_year": _round(r["erp_recv_year"], 2),
                "erp_reversal_year": _round(r["erp_reversal_year"], 2),
                "erp_net_in_year": _round(r["erp_net_in_year"], 2),
                "erp_out_year": _round(r["erp_out_year"], 2),

                # ==================== 最佳估计库存 ====================
                "best_inventory_amt": _round(r["best_inventory_amt"], 2),
            }
            for r in rows
        ],
    }


# ================================================================
#  自检（直接 `python data_wide.py` 即可跑通，无需启动 Flask）
# ================================================================

if __name__ == "__main__":
    import json
    result = get_inventory_wide_report(limit=3, sort_by="inventory_amount", sort_order="desc")
    print("=== 汇总（元） ===")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"=== 总行数 {result['total']}，返回 {len(result['rows'])} 行 ===")
    if result["rows"]:
        print("=== 第一行示例 ===")
        print(json.dumps(result["rows"][0], ensure_ascii=False, indent=2))
