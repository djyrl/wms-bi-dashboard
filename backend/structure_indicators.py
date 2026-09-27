"""
采购库存 BI — 库存结构指标模块
===============================
计算库存结构相关指标：
  - 当前库存金额（全部 / 当年）
  - 当前库存数量
  - 项目库存占比 TOP 10
  - 采购人库存占比 TOP 10
  - 按物料编码的安全库存偏离度
  - 库存来源结构（按项目）

数据来源：v_project_inventory_wide。
金额统一来源：utils._BATCH_AMOUNTS_SQL（批次去重）+ _PROJECT_RATIO_SQL（项目分配）。

⚠️ 重要：严禁在 v_project_inventory_wide 上直接 SUM(total_price)，
         视图行数 = 批次 × 项目，必须先去重再聚合。
"""

import json
from datetime import date
from typing import Any, Dict

from utils import (
    query, query_one, _f, _rows_to_float,
    _BATCH_AMOUNTS_SQL, _PROJECT_RATIO_SQL,
    _get_wide_batch_aggregates, _get_inventory_rows,
)


def _get_year_claim_flow(current_year: int) -> Dict:
    """
    2026 全年领用流量（含领老批次，区别于「当年入库批次的领用」）。

    因 WMS 于 2026-06-25 上线，全年领用需跨系统分两段拼接：
      - 上半年（01-01 ~ 06-24）：ERP MB51 项目出库，凭证金额 DMBTR
      - 下半年（06-25 起）：WMS 台账领料出库（REQUISITION_ORDER），数量 × 台账单价

    ⚠️ 两段金额口径不同（ERP 凭证价 vs 台账单价，约 4 倍差异），
       合计仅为量级参考，不参与「入库 − 领用」的净剩计算。
    """
    # 上半年 ERP 项目领用（真领用 direction='out'，冲销 102 与厂内转移不计入）
    h1 = query_one(f"""
        SELECT COALESCE(SUM(ABS(amount)), 0) AS amt
        FROM v_mb51_ledger_2026
        WHERE biz_date < '{current_year}-06-25'
          AND direction = 'out'
          AND (wbs_code IS NOT NULL OR project_code IS NOT NULL)
    """)
    # 下半年 WMS 台账领料（真领用 REQUISITION_ORDER，剔除收货冲销/采购退货）
    h2 = query_one(f"""
        SELECT COALESCE(SUM(log.change_quantity * inv.unit_price), 0) AS amt
        FROM wms_inventory_log log
        JOIN wms_inventory inv ON inv.id = log.inventory_id
        WHERE log.del_flag = '0'
          AND log.change_type = 31
          AND log.business_type = 'REQUISITION_ORDER'
          AND log.operation_time >= '{current_year}-06-25'
    """)
    h1_amt = _f(h1["amt"])
    h2_amt = _f(h2["amt"])
    return {
        "h1_amount": round(h1_amt / 10000, 2),       # 上半年领用（ERP 凭证金额）
        "h2_amount": round(h2_amt / 10000, 2),       # 下半年领用（WMS 台账）
        "total_amount": round((h1_amt + h2_amt) / 10000, 2),  # 全年领用合计
    }


def get_structure_indicators() -> Dict:
    """
    获取库存结构指标。

    一次 SQL 查询完成四个聚合：
      1. 全部库存总额（批次去重）
      2. 当年库存总额（批次去重，按 inbound_date 年份筛选）
      3. 项目库存占比（批次去重 → project_ratio 分配 → 按项目聚合）
      4. 采购人库存占比（批次去重 → project_ratio 分配 → 按采购人聚合）

    返回字段：
      - current_year:                    当前年份
      - current_inventory_amount:        当前库存金额（万元）
      - current_year_inventory_amount:   当年入库库存金额（万元）
      - current_inventory_quantity:      当前库存总数量
      - project_ratios:                  [{project_code, project_name, inventory_amount, ratio}, ...]
      - purchaser_ratios:                [{purchaser_id, purchaser_name, inventory_amount, ratio}, ...]

    Returns:
        Dict: 库存结构指标
    """
    current_year = date.today().year

    sql = f"""
        WITH {_BATCH_AMOUNTS_SQL},
        -- 全部汇总（批次级）
        all_totals AS (
            SELECT
                COALESCE(SUM(batch_inventory), 0) AS total_inventory,
                COALESCE(SUM(batch_inbound), 0)   AS total_inbound,
                COALESCE(SUM(batch_orig_qty), 0)  AS total_qty,
                -- 当年入库批次的库存金额（存量：今年进的货还剩多少）
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                             THEN batch_inventory ELSE 0 END), 0) AS year_inventory,
                -- 当年入库批次的入库金额（流量：今年累计进了多少）
                COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM inbound_date) = {current_year}
                             THEN batch_inbound ELSE 0 END), 0) AS year_inbound
            FROM batch_amounts
        ),
        -- 项目分配：批次金额 × project_ratio
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
        ),
        -- 按项目聚合
        project_agg AS (
            SELECT
                owner_project_code,
                MAX(project_name) AS project_name,
                SUM(batch_inventory * project_ratio) AS inventory_amount
            FROM wide_with_ratio
            GROUP BY owner_project_code
        ),
        -- 按采购人（purchaser_name = 申请人）聚合
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
            (SELECT year_inbound FROM all_totals)    AS year_inbound_amt,
            -- 使用 json_agg 将聚合结果打包为 JSON，减少网络传输的往返
            (SELECT json_agg(row_to_json(project_agg.*)
             ORDER BY project_agg.inventory_amount DESC) FROM project_agg) AS project_json,
            (SELECT json_agg(row_to_json(purchaser_agg.*)
             ORDER BY purchaser_agg.inventory_amount DESC) FROM purchaser_agg) AS purchaser_json
    """
    row = query_one(sql)
    if not row:
        # 无数据时返回空结构
        return {
            "current_year": current_year,
            "year_start": f"{current_year}-01-01",
            "year_end": f"{current_year}-12-31",
            "current_inventory_amount": 0,
            "current_year_inventory_amount": 0,
            "current_year_inbound_amount": 0,
            "current_year_claimed_amount": 0,
            "year_claim_flow": {"h1_amount": 0, "h2_amount": 0, "total_amount": 0},
            "current_inventory_quantity": 0,
            "project_ratios": [],
            "purchaser_ratios": [],
        }

    # 提取汇总值
    total_inventory_amt = _f(row["total_inventory_amt"])    # 库存总额（元）
    total_inventory_qty = _f(row["total_inventory_qty"])     # 库存总数量
    year_inventory_amt = _f(row["year_inventory_amt"])       # 当年库存额（元）
    year_inbound_amt = _f(row["year_inbound_amt"])           # 当年入库额（元）
    year_claim_flow = _get_year_claim_flow(current_year)     # 全年领用流量（跨系统）

    def _parse_json(val):
        """解析 pg json_agg 结果（可能是字符串或已解析的 list）。"""
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return json.loads(val)

    project_rows = _parse_json(row["project_json"])
    purchaser_rows = _parse_json(row["purchaser_json"])

    # ── 构建项目占比 ──
    project_ratios = []
    for r in project_rows:
        pa = _f(r.get("inventory_amount", 0))          # 该项目库存金额
        code = r.get("owner_project_code") or ""       # 项目编码
        project_ratios.append({
            "project_code": code,
            "project_name": r.get("project_name") or code,
            "inventory_amount": round(pa, 2),
            # 占比 = 项目库存 / 总库存
            "ratio": round(pa / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    # ── 构建采购人占比 ──
    purchaser_ratios = []
    for r in purchaser_rows:
        pa = _f(r.get("inventory_amount", 0))          # 该采购人名下库存金额
        name = r.get("purchaser_name") or "未知"
        purchaser_ratios.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inventory_amount": round(pa, 2),
            # 占比 = 采购人库存 / 总库存
            "ratio": round(pa / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    return {
        "current_year": current_year,
        "year_start": f"{current_year}-01-01",
        "year_end": f"{current_year}-12-31",
        # 汇总金额（万元）
        "current_inventory_amount": round(total_inventory_amt / 10000, 2),
        # 当年入库结存（存量）= 今年进的货还剩多少
        "current_year_inventory_amount": round(year_inventory_amt / 10000, 2),
        # 当年入库金额（流量）
        "current_year_inbound_amount": round(year_inbound_amt / 10000, 2),
        # 当年领用金额（流量）= 入库 − 结存（含 06-25 前的历史出库，wms_inventory_log 未覆盖）
        "current_year_claimed_amount": round((year_inbound_amt - year_inventory_amt) / 10000, 2),
        # 全年领用流量（含领老批次，跨 ERP + WMS 拼接，合计为量级参考）
        "year_claim_flow": year_claim_flow,
        "current_inventory_quantity": round(total_inventory_qty, 2),
        # 占比
        "project_ratios": project_ratios,
        "purchaser_ratios": purchaser_ratios,
    }


def get_structure_by_category() -> Dict:
    """
    按物料编码统计库存金额，含安全库存上下限（TOP 10 + 其他）。

    ⚠️ BUG FIX：之前直接在 v_project_inventory_wide 上 SUM(total_price)，
              视图有 N 行/批次（多项目），金额被放大 N 倍。
              现在使用批次去重 CTE（_BATCH_AMOUNTS_SQL）修复。

    安全上下限计算逻辑：
      - safe_min = mean_amt × 0.5
      - safe_max = mean_amt × 1.5
      其中 mean_amt 为 TOP 10 物料的平均库存金额（简单均值，非加权）。

    用于「在库水位 · 安全库存偏离度」分析。

    Returns:
        {"data": [{material_code, category, current, safe_max, safe_min, record_count}, ...]}
    """
    rows = query(f"""
        WITH {_BATCH_AMOUNTS_SQL}
        SELECT
            ba.material_code,
            -- 物料名称从 batch_amounts 没有，从视图取第一个非空值
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
    # 剩余的归为「其他」
    rest_amount = sum(r["inventory_amount"] for r in rows[top_n:])
    rest_record = sum(int(r["record_count"]) if r["record_count"] else 0 for r in rows[top_n:])

    # 计算 TOP 10 的平均库存金额，作为安全库存基准
    amounts = [r["inventory_amount"] for r in top_rows]
    mean_amt = sum(amounts) / len(amounts) if amounts else 0

    data = []
    for r in top_rows:
        amt = r["inventory_amount"]
        data.append({
            "material_code": r["material_code"],
            "category": r["category"],
            "current": round(amt, 2),
            # 安全上限：均值的 1.5 倍（当前超过此值表示积压）
            "safe_max": round(mean_amt * 1.5, 2),
            # 安全下限：均值的 0.5 倍（当前低于此值表示不足）
            "safe_min": round(mean_amt * 0.5, 2),
            "record_count": int(r["record_count"]) if r["record_count"] else 0,
        })

    # 将 TOP 10 之外的归为「其他」
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


def get_source_structure() -> Dict:
    """
    按项目统计库存金额及其占比（库存来源构成）。

    金额来源于 _get_inventory_rows()（批次去重 × project_ratio），
    按项目名称聚合 project_ratio 分配后的 inventory_amount。

    返回：
      - total_amount: 总库存金额（批次去重，与 summary 一致）
      - rows: [{source_name, inventory_amount, ratio}, ...]

    Returns:
        Dict: 来源结构数据
    """
    # 获取项目级明细（inventory_amount 已是 project_ratio 分配后的值）
    rows = _get_inventory_rows()

    # ── 按项目名称聚合库存金额 ──
    proj_data: Dict[str, Dict] = {}
    for r in rows:
        code = r.get("project_code") or ""
        name = r.get("project_name") or ""
        # 优先用项目名，无则用编码，都无则标记为未归属
        label = name if name else code if code else "(未归属项目)"
        if label not in proj_data:
            proj_data[label] = {"amt": 0.0}
        proj_data[label]["amt"] += r["inventory_amount"]

    # 按金额降序排列
    result_rows = [
        {"source_name": label, "inventory_amount": round(s["amt"], 2)}
        for label, s in proj_data.items()
    ]
    result_rows.sort(key=lambda x: x["inventory_amount"], reverse=True)

    # 使用批次去重总额作为分母，与 summary 口径统一
    agg = _get_wide_batch_aggregates(year=None)
    total_amt = agg.get("total_inventory_amount", 0.0)

    return {
        "total_amount": round(total_amt, 2),
        "rows": [
            {
                "source_name": r["source_name"],
                "inventory_amount": r["inventory_amount"],
                "ratio": round(r["inventory_amount"] / total_amt * 100, 2)
                if total_amt > 0 else 0,
            }
            for r in result_rows
        ],
    }
