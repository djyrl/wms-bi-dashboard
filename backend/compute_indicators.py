"""
采购库存 BI 指标计算模块
========================
基于 4 张 WMS 表（wms_inventory / wms_project_inventory / wms_material / wms_inbound_order）
计算 22 个库存分析指标。
"""

import psycopg2
import psycopg2.extras
from datetime import date
from typing import Any, Dict, List, Optional, Set

DB_CONFIG = {
    "host": "122.51.39.235",
    "port": 54321,
    "dbname": "garden_wms",
    "user": "kingbase",
    "password": "123456",
}

TODAY = date.today()


def _f(v) -> float:
    """将数据库返回的 Decimal / int / float 统一转为 float，避免 Python Decimal 与 float 混算异常。"""
    if v is None:
        return 0.0
    return float(v)


def _rows_to_float(rows: List[Dict], *fields: str) -> List[Dict]:
    """将查询结果中的指定 Decimal 字段转为 float。"""
    for r in rows:
        for f in fields:
            if f in r:
                r[f] = _f(r[f])
    return rows


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """执行查询，返回字典列表。"""
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
    rows = query(sql, params)
    return rows[0] if rows else None


# ================================================================
# 基础查询：库存事实表
# ================================================================

_INVENTORY_BASE = """
    SELECT
        i.id,
        i.material_code,
        COALESCE(NULLIF(m.name, ''), i.material_code) AS material_name,
        COALESCE(m.unit, '') AS unit,
        i.batch_code,
        i.supplier_code,
        i.business_id,
        i.original_quantity,
        i.current_quantity,
        i.used_quantity,
        i.unit_price,
        i.total_price,
        i.inbound_date::date AS inbound_date,
        i.putaway_date::date AS putaway_date,
        EXTRACT(DAY FROM (CURRENT_DATE - i.inbound_date::timestamp))::int AS age_days,
        (i.original_quantity * i.unit_price) AS inbound_amount,
        COALESCE(guide.total_picked, 0) * i.unit_price AS claimed_amount,
        (i.current_quantity * i.unit_price) AS inventory_amount
    FROM wms_inventory i
    LEFT JOIN wms_material m ON i.material_code = m.code
    LEFT JOIN (
        SELECT
            inventory_id,
            SUM(picked_quantity) AS total_picked
        FROM wms_outbound_order_item_guide
        WHERE del_flag = '0'
        GROUP BY inventory_id
    ) guide ON guide.inventory_id = i.id
    WHERE i.del_flag = '0'
"""


def _get_inventory_rows() -> List[Dict]:
    rows = query(_INVENTORY_BASE)
    return _rows_to_float(rows,
        "original_quantity", "current_quantity", "used_quantity",
        "unit_price", "total_price", "inbound_amount", "claimed_amount",
        "inventory_amount", "age_days")


# ================================================================
# 0. Summary（总览 KPI）
# ================================================================

def get_summary() -> Dict:
    """汇总统计：入库总额、领用总额、当前库存、记录数"""
    rows = _get_inventory_rows()
    total_inbound = sum(r["inbound_amount"] for r in rows)
    total_claimed = sum(r["claimed_amount"] for r in rows)
    total_inventory = sum(r["inventory_amount"] for r in rows)
    total_qty = sum(r["current_quantity"] for r in rows)
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


# ================================================================
# I. 库存领用指标（指标 1-4）
# ================================================================

def get_claim_indicators() -> Dict:
    """
    1. 采购领用率（金额）
    2. 采购领用率（数量）
    3. 未领用采购金额
    4. 未领用采购占比
    """
    rows = _get_inventory_rows()
    total_inbound_amt = sum(r["inbound_amount"] for r in rows)
    total_claimed_amt = sum(r["claimed_amount"] for r in rows)
    total_inbound_qty = sum(r["original_quantity"] for r in rows)
    total_claimed_qty = sum(r["used_quantity"] for r in rows)
    unclaimed_amt = total_inbound_amt - total_claimed_amt

    return {
        "claim_rate_amount": round(total_claimed_amt / total_inbound_amt * 100, 2) if total_inbound_amt else 0,
        "claim_rate_quantity": round(total_claimed_qty / total_inbound_qty * 100, 2) if total_inbound_qty else 0,
        "unclaimed_amount": round(unclaimed_amt / 10000, 2),
        "unclaimed_amount_ratio": round(unclaimed_amt / total_inbound_amt * 100, 2) if total_inbound_amt else 0,
        "total_inbound_amount": round(total_inbound_amt / 10000, 2),
        "total_claimed_amount": round(total_claimed_amt / 10000, 2),
    }


# ================================================================
# II. 库存结构指标（指标 5-8）
# ================================================================

def get_structure_indicators() -> Dict:
    """
    5. 当前库存金额
    6. 当前库存数量
    7. 项目库存占比
    8. 采购人库存占比
    """
    rows = _get_inventory_rows()
    total_inventory_amt = sum(r["inventory_amount"] for r in rows)
    total_inventory_qty = sum(r["current_quantity"] for r in rows)

    # 构建 project_code → project_name 映射（从 wms_zmmrp048_parsed 表取中文项目名称）
    project_name_rows = query("""
        SELECT posid, zpost1
        FROM public.wms_zmmrp048_parsed
        WHERE posid IS NOT NULL
          AND zpost1 IS NOT NULL
        GROUP BY posid, zpost1
    """)
    project_name_map: Dict[str, str] = {}
    for r in project_name_rows:
        code = r["posid"]
        name = r["zpost1"]
        if code and name and code not in project_name_map:
            project_name_map[code] = name

    # 7. 项目库存占比 — 关联 wms_project_inventory
    project_rows = query("""
        SELECT
            pi.owner_project_code,
            SUM(pi.current_quantity * i.unit_price) AS project_amount
        FROM wms_project_inventory pi
        JOIN wms_inventory i ON i.material_code = pi.material_code
            AND i.del_flag = '0'
        WHERE pi.del_flag = '0'
        GROUP BY pi.owner_project_code
        ORDER BY project_amount DESC
    """)
    project_ratios = []
    for r in project_rows:
        pa = _f(r["project_amount"])
        code = r["owner_project_code"] or ""
        project_ratios.append({
            "project_code": code,
            "project_name": project_name_map.get(code, code),
            "inventory_amount": round(pa, 2),
            "ratio": round(pa / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    # 8. 采购人库存占比 — wbs_zmmrp048_parsed.z_user（采购负责人）
    # 关联链: wms_inventory(material_code) → wms_project_inventory(owner_project_code+material_code) → wbs_zmmrp048_parsed(posid+matnr)
    purchaser_rows = query("""
        SELECT
            z.z_user AS purchaser_name,
            SUM(i.current_quantity * i.unit_price) AS purchaser_amount
        FROM wms_inventory i
        JOIN wms_project_inventory pi ON pi.material_code = i.material_code
            AND pi.del_flag = '0'
        JOIN wbs_zmmrp048_parsed z ON z.posid = pi.owner_project_code
            AND z.matnr = i.material_code
        WHERE i.del_flag = '0'
          AND z.z_user IS NOT NULL
        GROUP BY z.z_user
        ORDER BY purchaser_amount DESC
    """)
    purchaser_ratios = []
    for r in purchaser_rows:
        pa = _f(r["purchaser_amount"])
        name = r["purchaser_name"] or "未知"
        purchaser_ratios.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inventory_amount": round(pa, 2),
            "ratio": round(pa / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    return {
        "current_inventory_amount": round(total_inventory_amt / 10000, 2),
        "current_inventory_quantity": round(total_inventory_qty, 2),
        "project_ratios": project_ratios,
        "purchaser_ratios": purchaser_ratios,
    }


# ================================================================
# III. 库存时间指标（指标 9-12）
# ================================================================

def get_time_indicators(age_ranges: List[tuple] = None) -> Dict:
    """
    9. 长库龄库存金额占比（≥1年）
    10. 库龄结构占比
    11. 平均库龄（金额加权）
    12. 库龄分层统计
    """
    if age_ranges is None:
        age_ranges = [
            (0, 365, "≤1年"),
            (365, 1095, "1~3年"),
            (1095, 1825, "3~5年"),
            (1825, 99999, "≥5年"),
        ]

    rows = _get_inventory_rows()
    total_inventory = sum(r["inventory_amount"] for r in rows)

    # 加权平均库龄
    weighted_age_sum = sum(r["inventory_amount"] * r["age_days"] for r in rows)
    avg_age = weighted_age_sum / total_inventory if total_inventory else 0

    # 长库龄占比
    aged_amount = sum(r["inventory_amount"] for r in rows if r["age_days"] >= 365)

    # 库龄结构
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
        "aged_ratio_1y": round(aged_amount / total_inventory, 4) if total_inventory else 0,
        "aged_amount_1y": round(aged_amount, 2),
        "age_structure": structure,
        "avg_age_weighted_days": round(avg_age, 2),
    }


def get_age_layers(min_amount: float = 0, min_age: int = 0, max_age: int = None) -> List[Dict]:
    """
    12. 库龄分层统计 — 筛选库存金额>min_amount 且 库龄>min_age 的明细
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
                    "batch_code": r["batch_code"],
                    "inventory_amount": round(amt, 2),
                    "current_quantity": r["current_quantity"],
                    "age_days": int(age),
                    "inbound_date": str(r["inbound_date"]),
                    "unit_price": r["unit_price"],
                    "supplier_code": r["supplier_code"],
                })

    result.sort(key=lambda x: x["inventory_amount"], reverse=True)
    return result


# ================================================================
# IV & V. 维度指标（指标 13-18）
# ================================================================

def get_by_project() -> List[Dict]:
    """
    13. 项目采购领用率
    14. 项目未消耗库存金额
    15. 项目平均库龄
    """
    total_rows = _get_inventory_rows()

    # 构建 project_code → project_name 映射（从 wms_zmmrp048_parsed 表取中文项目名称）
    project_name_rows = query("""
        SELECT "POSID", "ZPOST1"
        FROM public.wms_zmmrp048_parsed
        WHERE "POSID" IS NOT NULL
          AND "ZPOST1" IS NOT NULL
        GROUP BY "POSID", "ZPOST1"
    """)
    project_name_map: Dict[str, str] = {}
    for r in project_name_rows:
        code = r["POSID"]
        name = r["ZPOST1"]
        if code and name and code not in project_name_map:
            project_name_map[code] = name

    # 汇总每个物料的项目归属
    pi_rows = query("""
        SELECT owner_project_code, material_code, SUM(current_quantity) AS pi_qty
        FROM wms_project_inventory
        WHERE del_flag = '0'
        GROUP BY owner_project_code, material_code
    """)

    # 构建项目-物料映射
    proj_mat_qty: Dict[str, Dict[str, float]] = {}
    for r in pi_rows:
        proj = r["owner_project_code"]
        mat = r["material_code"]
        if proj not in proj_mat_qty:
            proj_mat_qty[proj] = {}
        proj_mat_qty[proj][mat] = _f(r["pi_qty"])

    # 汇总每个项目下关联的库存
    proj_stats: Dict[str, Dict] = {}
    for r in total_rows:
        mat = r["material_code"]
        cur_qty = r["current_quantity"]
        for proj, mats in proj_mat_qty.items():
            if mat in mats:
                if proj not in proj_stats:
                    proj_stats[proj] = {"inbound_amt": 0, "claimed_amt": 0, "inventory_amt": 0, "age_weighted": 0, "over90_amt": 0, "count": 0}
                factor = mats[mat] / cur_qty if cur_qty > 0 else 0
                proj_stats[proj]["inbound_amt"] += r["inbound_amount"] * factor
                proj_stats[proj]["claimed_amt"] += r["claimed_amount"] * factor
                proj_stats[proj]["inventory_amt"] += r["inventory_amount"] * factor
                proj_stats[proj]["age_weighted"] += r["inventory_amount"] * r["age_days"] * factor
                if r["age_days"] >= 90:
                    proj_stats[proj]["over90_amt"] += r["inventory_amount"] * factor
                proj_stats[proj]["count"] += 1
                break

    result = []
    for proj, s in proj_stats.items():
        code = proj or ""
        result.append({
            "project_code": code,
            "project_name": project_name_map.get(code, code),
            "inbound_amount": round(s["inbound_amt"], 2),
            "claimed_amount": round(s["claimed_amt"], 2),
            "unclaimed_amount": round(s["inventory_amt"], 2),
            "claim_rate": round(s["claimed_amt"] / s["inbound_amt"] * 100, 2) if s["inbound_amt"] else 0,
            "avg_age_days": round(s["age_weighted"] / s["inventory_amt"], 2) if s["inventory_amt"] else 0,
            "over90_ratio": round(s["over90_amt"] / s["inventory_amt"] * 100, 1) if s["inventory_amt"] else 0,
            "record_count": s["count"],
        })

    result.sort(key=lambda x: x["unclaimed_amount"], reverse=True)
    return result


def get_by_purchaser() -> List[Dict]:
    """
    16. 采购人领用率
    17. 采购人未消耗库存金额
    18. 采购人库存库龄

    使用 wbs_zmmrp048_parsed.z_user（采购负责人）作为采购人维度。
    关联链: wms_inventory(material_code) → wms_project_inventory(owner_project_code+material_code) → wbs_zmmrp048_parsed(posid+matnr)
    """
    rows = query("""
        SELECT
            z.z_user AS purchaser_name,
            SUM(i.original_quantity * i.unit_price) AS inbound_amt,
            SUM(i.used_quantity * i.unit_price) AS claimed_amt,
            SUM(i.current_quantity * i.unit_price) AS inventory_amt,
            SUM(i.current_quantity * i.unit_price * EXTRACT(DAY FROM (CURRENT_DATE - i.inbound_date::timestamp))) AS age_weighted,
            COUNT(DISTINCT i.id) AS record_count
        FROM wms_inventory i
        JOIN wms_project_inventory pi ON pi.material_code = i.material_code
            AND pi.del_flag = '0'
        JOIN wbs_zmmrp048_parsed z ON z.posid = pi.owner_project_code
            AND z.matnr = i.material_code
        WHERE i.del_flag = '0'
          AND z.z_user IS NOT NULL
        GROUP BY z.z_user
        ORDER BY inventory_amt DESC
    """)

    result = []
    for r in rows:
        inv_amt = _f(r["inventory_amt"])
        inb_amt = _f(r["inbound_amt"])
        clm_amt = _f(r["claimed_amt"])
        age_w = _f(r["age_weighted"])
        name = r["purchaser_name"] or "未知"
        result.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inbound_amount": round(inb_amt, 2),
            "claimed_amount": round(clm_amt, 2),
            "unclaimed_amount": round(inv_amt, 2),
            "claim_rate": round(clm_amt / inb_amt * 100, 2) if inb_amt else 0,
            "avg_age_days": round(age_w / inv_amt, 2) if inv_amt else 0,
            "record_count": int(r["record_count"]) if r["record_count"] else 0,
        })

    return result


# ================================================================
# VI. TOP 排行（指标 19-22）
# ================================================================

def get_top_unclaimed_amount(limit: int = 10) -> List[Dict]:
    """19. 未领用库存 TOP（金额），附带项目归属和采购人"""
    rows = _get_inventory_rows()
    rows.sort(key=lambda r: r["inventory_amount"], reverse=True)
    top_rows = rows[:limit]

    # ---- 查询项目和采购人信息 ----
    material_codes = [r["material_code"] for r in top_rows]
    project_map: Dict[str, str] = {}
    project_name_map: Dict[str, str] = {}
    purchaser_map: Dict[str, str] = {}

    if material_codes:
        placeholders = ','.join(['%s'] * len(material_codes))

        # 取每个物料归属的项目（按 current_quantity 最大的项目作为主项目）
        project_rows = query(f"""
            SELECT DISTINCT ON (material_code)
                material_code,
                owner_project_code
            FROM wms_project_inventory
            WHERE del_flag = '0'
              AND material_code IN ({placeholders})
            ORDER BY material_code, current_quantity DESC
        """, tuple(material_codes))
        project_map = {r["material_code"]: r["owner_project_code"] or "" for r in project_rows}

        # 查项目编码对应的中文项目名称（wms_zmmrp048_parsed.posid → zpost1）
        project_codes = [v for v in project_map.values() if v]
        if project_codes:
            pc_placeholders = ','.join(['%s'] * len(project_codes))
            pn_rows = query(f"""
                SELECT posid, zpost1
                FROM public.wms_zmmrp048_parsed
                WHERE posid IN ({pc_placeholders})
                  AND zpost1 IS NOT NULL
                GROUP BY posid, zpost1
            """, tuple(project_codes))
            project_name_map = {r["posid"]: r["zpost1"] for r in pn_rows}

        # 取采购人（通过 wbs_zmmrp048_parsed 的 z_user）
        purchaser_rows = query(f"""
            SELECT DISTINCT ON (z.matnr)
                z.matnr AS material_code,
                z.z_user AS purchaser_name
            FROM wbs_zmmrp048_parsed z
            WHERE z.matnr IN ({placeholders})
              AND z.z_user IS NOT NULL
        """, tuple(material_codes))
        purchaser_map = {r["material_code"]: r["purchaser_name"] or "" for r in purchaser_rows}

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
            "owner_project_code": project_map.get(r["material_code"], ""),
            "owner_project_name": project_name_map.get(project_map.get(r["material_code"], ""), ""),
            "purchaser_name": purchaser_map.get(r["material_code"], ""),
        }
        for r in top_rows
    ]


def get_optimize_suggest(limit: int = 8, safety_days: int = 60) -> List[Dict]:
    """智能备货优化建议：按物料汇总，基于日均消耗推荐安全库存上限"""
    rows = _get_inventory_rows()

    # ---- 按物料编码汇总 ----
    mat_stats: Dict[str, Dict] = {}
    for r in rows:
        code = r["material_code"]
        if code not in mat_stats:
            mat_stats[code] = {
                "name": r["material_name"],
                "current": 0.0,        # 当前库存金额
                "claimed": 0.0,        # 已领用金额
                "age_weighted": 0.0,   # 金额加权库龄
                "inv_total": 0.0,      # 库存金额合计（用于加权）
            }
        s = mat_stats[code]
        s["current"] += r["inventory_amount"]
        s["claimed"] += r["claimed_amount"]
        s["age_weighted"] += r["inventory_amount"] * r["age_days"]
        s["inv_total"] += r["inventory_amount"]

    # ---- 计算日均消耗 & 建议上限 ----
    result = []
    for code, s in mat_stats.items():
        current_wan = s["current"] / 10000
        if current_wan <= 0:
            continue

        # 金额加权平均库龄
        avg_age = s["age_weighted"] / s["inv_total"] if s["inv_total"] > 0 else 0
        if avg_age <= 0:
            continue

        # 日均消耗（万元/天）= 已领用金额 / 平均库龄
        daily_use = (s["claimed"] / avg_age) / 10000

        # 建议上限 = 日均消耗 × 安全库存天数
        max_stock = daily_use * safety_days

        # 只保留当前库存超标的物料
        if current_wan > max_stock and daily_use > 0:
            result.append({
                "name": s["name"],
                "current": round(current_wan, 2),
                "dailyUse": round(daily_use, 2),
                "maxStock": round(max_stock, 2),
            })

    # 按超出量降序排列
    result.sort(key=lambda x: x["current"] - x["maxStock"], reverse=True)
    return result[:limit]


def get_top_unclaimed_quantity(limit: int = 10) -> List[Dict]:
    """20. 未领用库存 TOP（数量）"""
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
    """21. 领用 TOP（金额）"""
    rows = _get_inventory_rows()
    rows.sort(key=lambda r: r["claimed_amount"], reverse=True)
    return [
        {
            "id": r["id"],
            "material_code": r["material_code"],
            "claimed_amount": round(r["claimed_amount"], 2),
            "inbound_amount": round(r["inbound_amount"], 2),
            "unit_price": r["unit_price"],
            "inbound_date": str(r["inbound_date"]),
        }
        for r in rows[:limit]
    ]


def get_top_claimed_quantity(limit: int = 10) -> List[Dict]:
    """22. 领用 TOP（数量）"""
    rows = _get_inventory_rows()
    rows.sort(key=lambda r: r["used_quantity"], reverse=True)
    return [
        {
            "id": r["id"],
            "material_code": r["material_code"],
            "claimed_quantity": r["used_quantity"],
            "inbound_quantity": r["original_quantity"],
            "inbound_date": str(r["inbound_date"]),
        }
        for r in rows[:limit]
    ]


# ================================================================
# 主题一专用：时序 & 维度补充接口
# ================================================================

def get_claim_monthly() -> Dict:
    """
    按月统计入库金额、领用金额、领用率（最近12个月）。
    供「领用率月度趋势」「入库vs领用对比」两个图表使用。
    """
    from collections import OrderedDict

    rows = _get_inventory_rows()

    monthly: OrderedDict[str, Dict[str, float]] = OrderedDict()
    for r in rows:
        d = r["putaway_date"] or r["inbound_date"]
        if hasattr(d, 'strftime'):
            month = d.strftime("%Y-%m")
        else:
            month = str(d)[:7]
        if month not in monthly:
            monthly[month] = {"inbound": 0.0, "claimed": 0.0}
        monthly[month]["inbound"] += r["inbound_amount"]
        monthly[month]["claimed"] += r["claimed_amount"]

    all_months = list(monthly.keys())
    recent_months = all_months[-12:] if len(all_months) > 12 else all_months

    months = []
    data = []
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


def get_claim_daily() -> Dict:
    """
    按天统计上个月+当月入库金额、领用金额、领用率（两个月）。
    供「领用率当月趋势」图表使用。
    """
    from datetime import date as dt_date, timedelta

    rows = _get_inventory_rows()
    today = dt_date.today()
    # 上个月第一天
    first_day_current = today.replace(day=1)
    first_day_prev = (first_day_current - timedelta(days=1)).replace(day=1)

    # 按天聚合两个月数据
    day_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d < first_day_prev:
            continue
        key = d.strftime("%Y-%m-%d")
        if key not in day_map:
            day_map[key] = {"inbound": 0.0, "claimed": 0.0}
        day_map[key]["inbound"] += r["inbound_amount"]
        day_map[key]["claimed"] += r["claimed_amount"]

    days = []
    data = []
    d = first_day_prev
    while d <= today:
        key = d.strftime("%Y-%m-%d")
        label = f"{d.month}/{d.day}"
        if key in day_map:
            inbound = day_map[key]["inbound"]
            claimed = day_map[key]["claimed"]
        else:
            inbound = 0.0
            claimed = 0.0
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        days.append(label)
        data.append({
            "day": label,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })
        d += timedelta(days=1)

    return {"days": days, "data": data}


def get_claim_weekly() -> Dict:
    """
    按周统计入库金额、领用金额、领用率（最近12周）。
    供「领用率趋势」「入库vs领用对比」图表使用。
    """
    from datetime import date as dt_date, timedelta

    rows = _get_inventory_rows()
    today = dt_date.today()
    # 往前推 12 周
    cutoff = today - timedelta(weeks=12)

    # 按 ISO 周聚合
    week_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d < cutoff:
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        if week_key not in week_map:
            # 该周周一
            monday = d - timedelta(days=d.weekday())
            week_map[week_key] = {"inbound": 0.0, "claimed": 0.0, "monday": monday}
        week_map[week_key]["inbound"] += r["inbound_amount"]
        week_map[week_key]["claimed"] += r["claimed_amount"]

    weeks = []
    data = []
    for week_key in sorted(week_map.keys()):
        v = week_map[week_key]
        inbound = v["inbound"]
        claimed = v["claimed"]
        rate = round(claimed / inbound * 100, 2) if inbound else 0
        monday = v["monday"]
        sunday = monday + timedelta(days=6)
        label = f"{monday.month}/{monday.day}-{sunday.month}/{sunday.day}"
        weeks.append(label)
        data.append({
            "week": label,
            "inbound_amount": round(inbound, 2),
            "claimed_amount": round(claimed, 2),
            "net_amount": round(inbound - claimed, 2),
            "claim_rate": rate,
        })

    weeks.reverse()
    data.reverse()
    return {"weeks": weeks, "data": data}


def get_structure_by_category() -> Dict:
    """
    按物料编码统计库存金额，计算安全上下限。
    供「在库物资 · 安全库存偏离度」使用。
    """
    rows = query("""
        SELECT
            i.material_code,
            COALESCE(NULLIF(m.name, ''), i.material_code) AS category,
            SUM(i.current_quantity * i.unit_price) AS inventory_amount,
            COUNT(*) AS record_count
        FROM wms_inventory i
        LEFT JOIN wms_material m ON i.material_code = m.code
        WHERE i.del_flag = '0'
        GROUP BY i.material_code, m.name
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
    """
    按物资类别（matkl / wgbez）统计库存金额、领用率、SKU数。
    供「按物料类别 · 库存金额与领用率」气泡图使用。
    """
    rows = query("""
        SELECT
            z.matkl AS category_code,
            z.wgbez AS category_name,
            SUM(i.current_quantity * i.unit_price) AS inventory_amount,
            SUM(i.original_quantity * i.unit_price) AS inbound_amount,
            SUM(COALESCE(guide.total_picked, 0) * i.unit_price) AS claimed_amount,
            COUNT(DISTINCT i.material_code) AS sku_count,
            COUNT(DISTINCT i.id) AS record_count
        FROM wms_inventory i
        JOIN wbs_zmmrp048_parsed z ON z.matnr = i.material_code
        LEFT JOIN (
            SELECT inventory_id, SUM(picked_quantity) AS total_picked
            FROM wms_outbound_order_item_guide
            WHERE del_flag = '0'
            GROUP BY inventory_id
        ) guide ON guide.inventory_id = i.id
        WHERE i.del_flag = '0'
          AND z.matkl IS NOT NULL
        GROUP BY z.matkl, z.wgbez
        ORDER BY inventory_amount DESC
    """)
    rows = _rows_to_float(rows, "inventory_amount", "inbound_amount", "claimed_amount")

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
        data.append({
            "category_code": r["category_code"],
            "category_name": r["category_name"] or r["category_code"] or "未知",
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
    """
    按周统计入库/领用金额，多维度异常检测。

    异常判断维度：
      1. 新项目：近 days 天内有新项目首次入库，标记对应周
      2. 周度环比：本周领用金额 vs 上周领用金额，波动超过 ±30% 预警
      3. 周度同比：本周领用金额 vs 去年同周（若不存在则对比近 4 周均值），波动超过 ±30% 预警

    type: 0 = 正常, 1 = 存在至少一类异常
    """
    from datetime import date as dt_date, timedelta

    rows = _get_inventory_rows()
    today = dt_date.today()
    AMPLITUDE = 0.30  # 周度波动阈值

    # ================================================================
    # Step 1 — 新建项目检测
    #   查询 wms_project_inventory 中每个项目的首次 create_date，
    #   若首次创建时间在近 days 天内，视为"新项目"。
    #   将其首次出现的 ISO 周标记为新项目异常周。
    # ================================================================
    new_cutoff = today - timedelta(days=days)

    proj_rows = query("""
        SELECT owner_project_code, MIN(create_date)::date AS first_date
        FROM wms_project_inventory
        WHERE del_flag = '0'
        GROUP BY owner_project_code
    """)

    new_project_weeks: Set[str] = set()
    new_project_map: Dict[str, List[str]] = {}  # week_key → [project_code, …]
    for r in proj_rows:
        fd = r["first_date"]
        if hasattr(fd, 'date'):
            fd = fd.date()
        if not fd or fd < new_cutoff:
            continue
        iso = fd.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        new_project_weeks.add(wk)
        new_project_map.setdefault(wk, []).append(r["owner_project_code"])

    # ================================================================
    # Step 2 — 按 ISO 周聚合（扩展窗口至 60 周，用于同比计算）
    # ================================================================
    cutoff = today - timedelta(weeks=60)

    week_map: Dict[str, Dict] = {}
    for r in rows:
        d = r["inbound_date"]
        if hasattr(d, 'date'):
            d = d.date()
        if d < cutoff:
            continue
        iso = d.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        if week_key not in week_map:
            monday = d - timedelta(days=d.weekday())
            week_map[week_key] = {
                "inbound_amount": 0.0,
                "claimed_amount": 0.0,
                "monday": monday,
                "year": iso[0],
                "week_num": iso[1],
            }
        week_map[week_key]["inbound_amount"] += r["inbound_amount"]
        week_map[week_key]["claimed_amount"] += r["claimed_amount"]

    sorted_weeks = sorted(week_map.keys())

    # ================================================================
    # Step 3 — 逐周计算三个维度的异常
    # ================================================================
    data = []
    for i, week_key in enumerate(sorted_weeks):
        v = week_map[week_key]
        monday = v["monday"]
        sunday = monday + timedelta(days=6)
        date_label = f"{monday.month}/{monday.day}-{sunday.month}/{sunday.day}"

        cl_val = v["claimed_amount"]
        in_val = v["inbound_amount"]
        year = v["year"]
        week_num = v["week_num"]

        anomaly_parts: List[str] = []
        wow_ratio = None
        yoy_ratio = None

        # ----- 3a. 新项目异常 -----
        if week_key in new_project_weeks:
            proj_list = new_project_map.get(week_key, [])
            short = "、".join(proj_list[:2])
            if len(proj_list) > 2:
                short += f"等{len(proj_list)}个"
            anomaly_parts.append(f"新项目({short})")

        # ----- 3b. 周度环比（vs 上周） -----
        if i > 0:
            prev_cl = week_map[sorted_weeks[i - 1]]["claimed_amount"]
            if prev_cl > 0:
                wow_ratio = round((cl_val - prev_cl) / prev_cl, 4)
                if abs(wow_ratio) > AMPLITUDE:
                    arrow = "↑" if wow_ratio > 0 else "↓"
                    anomaly_parts.append(f"环比{arrow}{abs(wow_ratio) * 100:.0f}%")

        # ----- 3c. 周度同比（vs 去年同周，回退到近 4 周均值） -----
        last_year_key = f"{year - 1}-W{week_num:02d}"
        if last_year_key in week_map:
            ly_cl = week_map[last_year_key]["claimed_amount"]
            if ly_cl > 0:
                yoy_ratio = round((cl_val - ly_cl) / ly_cl, 4)
                if abs(yoy_ratio) > AMPLITUDE:
                    arrow = "↑" if yoy_ratio > 0 else "↓"
                    anomaly_parts.append(f"同比{arrow}{abs(yoy_ratio) * 100:.0f}%")
        else:
            # 回退：近 2–4 周领用金额均值
            past_vals = [
                week_map[sorted_weeks[j]]["claimed_amount"]
                for j in range(max(0, i - 4), i)
            ]
            if len(past_vals) >= 2:
                avg4 = sum(past_vals) / len(past_vals)
                if avg4 > 0:
                    yoy_ratio = round((cl_val - avg4) / avg4, 4)
                    if abs(yoy_ratio) > AMPLITUDE:
                        arrow = "↑" if yoy_ratio > 0 else "↓"
                        anomaly_parts.append(f"4周均值{arrow}{abs(yoy_ratio) * 100:.0f}%")

        label_str = "、".join(anomaly_parts) if anomaly_parts else "正常"

        data.append({
            "date": date_label,
            "week_key": week_key,
            "inbound_amount": round(in_val, 2),
            "claimed_amount": round(cl_val, 2),
            "type": 1 if anomaly_parts else 0,
            "label": label_str,
            "wow_ratio": wow_ratio,
            "yoy_ratio": yoy_ratio,
            "is_new_project_week": week_key in new_project_weeks,
        })

    # ================================================================
    # Step 4 — 只返回近 26 周（半年）供前端展示，移除内部字段
    # ================================================================
    result = data[-26:] if len(data) > 26 else data
    result.reverse()
    for item in result:
        del item["week_key"]

    return {"data": result}


def get_batch_digest() -> Dict:
    """
    按 batch_code 取 TOP 6 批次，模拟逐月消化进度（基于当前剩余占比和库龄估算月均消耗率）。
    供「按入库批次 · 库存消化进度」图表使用。
    """
    rows = query("""
        SELECT
            batch_code,
            MIN(inbound_date)::date AS first_inbound,
            SUM(original_quantity * unit_price) AS inbound_amt,
            SUM(current_quantity * unit_price) AS remain_amt,
            ROUND(AVG(EXTRACT(DAY FROM (CURRENT_DATE - inbound_date::timestamp)))) AS avg_age_days
        FROM wms_inventory
        WHERE del_flag = '0' AND batch_code IS NOT NULL
        GROUP BY batch_code
        ORDER BY inbound_amt DESC
        LIMIT 6
    """)
    rows = _rows_to_float(rows, "inbound_amt", "remain_amt")

    labels = ['入库月', '+1月', '+2月', '+3月', '+4月', '+5月', '+6月']
    colors = ['#3b82f6', '#f59e0b', '#f43f5e', '#10b981', '#8b5cf6', '#ec4899']
    series = []

    for idx, r in enumerate(rows):
        inbound = r["inbound_amt"] or 0
        remain = r["remain_amt"] or 0
        age_days = r["avg_age_days"] or 30

        if inbound > 0:
            total_remain_pct = remain / inbound * 100
        else:
            total_remain_pct = 100

        months = max(age_days / 30.0, 1)
        # 月均消耗率 = 已消耗百分比 / 库龄月数
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

    return {
        "labels": labels,
        "series": series,
    }


# ================================================================
# 主题三专用：库龄月度趋势
# ================================================================

def get_age_monthly() -> Dict:
    """
    按月计算加权平均库龄和超90天占比（最近12个月）。

    对每个历史月份的月末，计算「当前仍持有库存」的：
      - 加权平均库龄（按入库金额加权）
      - 库龄 ≥ 90 天的金额占比

    供「平均库龄月度趋势」图表使用。
    """
    from datetime import date as dt_date, timedelta

    today = dt_date.today()

    # ---- 生成最近12个月的月末日期（从最早到最晚） ----
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

    # ---- 获取当前库存数据 ----
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

            if d > month_end:
                continue  # 该月末还未入库，不计入

            age = (month_end - d).days
            # 使用入库金额(inbound_amount)作为权重，反映入库时的完整价值
            weight = r["inbound_amount"]
            total_weight += weight
            age_weighted_sum += weight * age
            if age >= 90:
                over90_weight += weight

        avg_age = round(age_weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
        over90_rate = round(over90_weight / total_weight * 100, 1) if total_weight > 0 else 0.0

        label = f"{month_end.month}月"
        months.append(label)
        data.append({
            "month": label,
            "avg_age": avg_age,
            "over90_rate": over90_rate,
        })

    return {"months": months, "data": data}


# ================================================================
# 主题三专用：滞留库存热力图（物料类别 × 库龄段）
# ================================================================

def get_age_heatmap() -> Dict:
    """
    按物料类别 × 库龄段 交叉统计库存金额。

    通过 wms_material.material_group_code → wms_material_group 获取物料类别，
    取库存金额 TOP 10 类别，按 6 个库龄段汇总金额。

    供「滞留库存热力图」图表使用。
    """
    rows = query("""
        SELECT
            mg.code AS category_code,
            mg.name AS category_name,
            EXTRACT(DAY FROM (CURRENT_DATE - i.inbound_date::timestamp))::int AS age_days,
            (i.current_quantity * i.unit_price) AS inventory_amount
        FROM wms_inventory i
        JOIN wms_material m ON m.code = i.material_code AND m.del_flag = '0'
        JOIN wms_material_group mg ON mg.code = m.material_group_code AND mg.del_flag = '0'
        WHERE i.del_flag = '0'
    """)
    rows = _rows_to_float(rows, "inventory_amount", "age_days")

    # 库龄段定义（从短到长，前端展示时反转）
    AGE_RANGES = [
        (0, 30, '0-30天'),
        (30, 60, '30-60天'),
        (60, 90, '60-90天'),
        (90, 180, '90-180天'),
        (180, 365, '180-365天'),
        (365, 99999, '>365天'),
    ]

    # ---- 按类别聚合 ----
    cat_data: Dict[str, Dict] = {}
    for r in rows:
        code = r["category_code"] or "未知"
        name = r["category_name"] or code
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

    # ---- 取 TOP 10 类别 ----
    top_cats = sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True)[:10]

    # ---- 构建矩阵（行 = 库龄段从老到新，列 = 类别） ----
    age_labels = [label for _, _, label in reversed(AGE_RANGES)]  # ['>365天', '180-365', ...]
    matrix: List[List[float]] = []
    for _, _, label in reversed(AGE_RANGES):
        row = []
        for _, cat in top_cats:
            # 转换为万元
            row.append(round(cat["ages"][label] / 10000, 2))
        matrix.append(row)

    categories = [cat["name"] for _, cat in top_cats]

    return {
        "categories": categories,
        "age_labels": age_labels,
        "data": matrix,
    }
