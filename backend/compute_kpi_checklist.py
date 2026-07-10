"""
采购库存 KPI 考核清单 指标计算模块（高性能版）
=============================================
自包含数据库访问，不依赖 compute_indicators.py。
策略：一次拉取库存明细 + 3 条聚合 SQL → Python 内存计算全部 K1-K9、T1-T2。
"""

import psycopg2
import psycopg2.extras
from datetime import date
from typing import Any, Dict, List, Tuple

# ================================================================
# 数据库基础设施（自包含，不 import 其他模块）
# ================================================================

DB_CONFIG = {
    "host": "122.51.39.235",
    "port": 54321,
    "dbname": "garden_wms",
    "user": "kingbase",
    "password": "123456",
}

TODAY = date.today()


def _f(v) -> float:
    if v is None:
        return 0.0
    return float(v)


def _rows_to_float(rows: List[Dict], *fields: str) -> List[Dict]:
    for r in rows:
        for f in fields:
            if f in r:
                r[f] = _f(r[f])
    return rows


def _get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def _query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = _get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        if conn:
            conn.close()


# ================================================================
# 库存基础数据 — 一条 SQL 拉取全部库存明细
# ================================================================

_INVENTORY_SQL = """
    SELECT
        i.id,
        i.material_code,
        COALESCE(NULLIF(m.name, ''), i.material_code) AS material_name,
        COALESCE(m.unit, '') AS unit,
        i.batch_code,
        i.original_quantity,
        i.current_quantity,
        i.used_quantity,
        i.unit_price,
        i.inbound_date::date AS inbound_date,
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


def _fetch_inventory() -> List[Dict]:
    """拉取全部库存明细（唯一一次全表查询）。"""
    rows = _query(_INVENTORY_SQL)
    return _rows_to_float(rows,
        "original_quantity", "current_quantity", "used_quantity",
        "unit_price", "inbound_amount", "claimed_amount", "inventory_amount",
        "age_days")


# ================================================================
# 聚合 SQL 查询（3 条，替代原方案的 7 次全量拉取 + 多次 JOIN）
# ================================================================

def _fetch_project_inventory() -> List[Dict]:
    """
    按 项目×物料 汇总当前库存数量。
    用于 K6（项目库存占比）、K5/K8（项目分析）。
    """
    rows = _query("""
        SELECT
            pi.owner_project_code,
            pi.material_code,
            SUM(pi.current_quantity) AS pi_qty
        FROM wms_project_inventory pi
        WHERE pi.del_flag = '0'
        GROUP BY pi.owner_project_code, pi.material_code
    """)
    return _rows_to_float(rows, "pi_qty")


def _fetch_project_names() -> Dict[str, str]:
    """project_code → project_name 映射。"""
    rows = _query("""
        SELECT posid, zpost1
        FROM public.wms_zmmrp048_parsed
        WHERE posid IS NOT NULL AND zpost1 IS NOT NULL
        GROUP BY posid, zpost1
    """)
    return {r["posid"]: r["zpost1"] for r in rows}


def _fetch_purchaser_stats() -> List[Dict]:
    """
    按采购人汇总入库/领用/库存金额及加权库龄（K6 采购人占比 + K9 采购人分析）。
    直接 SQL 聚合，不在 Python 中逐行遍历。
    """
    rows = _query("""
        SELECT
            z.z_user AS purchaser_name,
            SUM(i.original_quantity * i.unit_price) AS inbound_amt,
            SUM(i.used_quantity * i.unit_price)     AS claimed_amt,
            SUM(i.current_quantity * i.unit_price)  AS inventory_amt,
            SUM(i.current_quantity * i.unit_price
                * EXTRACT(DAY FROM (CURRENT_DATE - i.inbound_date::timestamp))) AS age_weighted,
            COUNT(DISTINCT i.id) AS record_count
        FROM wms_inventory i
        JOIN wms_project_inventory pi
            ON pi.material_code = i.material_code AND pi.del_flag = '0'
        JOIN wbs_zmmrp048_parsed z
            ON z.posid = pi.owner_project_code AND z.matnr = i.material_code
        WHERE i.del_flag = '0'
          AND z.z_user IS NOT NULL
        GROUP BY z.z_user
        ORDER BY inventory_amt DESC
    """)
    return _rows_to_float(rows, "inbound_amt", "claimed_amt", "inventory_amt", "age_weighted")


# ================================================================
# 辅助：状态判定
# ================================================================

def _status_for_rate(rate: float, target: float, direction: str = "up") -> str:
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


# ================================================================
# 主入口：一次拉取 + 内存计算全部指标
# ================================================================

def get_kpi_checklist() -> Dict[str, Any]:
    # ── Step 1: 拉取数据（4 次 DB 查询，全部无 JOIN 或简单 JOIN） ──
    inv_rows = _fetch_inventory()                        # 库存明细
    proj_inv_rows = _fetch_project_inventory()           # 项目-物料映射
    proj_name_map = _fetch_project_names()                # 项目编码→名称
    purchaser_rows = _fetch_purchaser_stats()             # 采购人汇总

    # ── Step 2: 单次遍历 inv_rows 完成全部「总计」计算 ──
    total_inbound_amt = 0.0
    total_claimed_amt = 0.0
    total_inventory_amt = 0.0
    total_inbound_qty = 0.0
    total_claimed_qty = 0.0
    total_inventory_qty = 0.0
    age_weighted_sum = 0.0
    aged_365_amt = 0.0

    # 库龄分段
    AGE_BUCKETS: List[Tuple[str, int, int]] = [
        ("≤1年", 0, 365),
        ("1~3年", 365, 1095),
        ("3~5年", 1095, 1825),
        ("≥5年", 1825, 999999),
    ]
    age_amt = {label: 0.0 for label, _, _ in AGE_BUCKETS}
    age_cnt = {label: 0 for label, _, _ in AGE_BUCKETS}

    # 未动用（claimed=0）加权
    unused_weighted = 0.0
    unused_total_amt = 0.0

    for r in inv_rows:
        inbound = r["inbound_amount"]
        claimed = r["claimed_amount"]
        inventory = r["inventory_amount"]
        age = r["age_days"]

        total_inbound_amt += inbound
        total_claimed_amt += claimed
        total_inventory_amt += inventory
        total_inbound_qty += r["original_quantity"]
        total_claimed_qty += r["used_quantity"]
        total_inventory_qty += r["current_quantity"]
        age_weighted_sum += inventory * age

        if age >= 365:
            aged_365_amt += inventory

        for label, lo, hi in AGE_BUCKETS:
            if lo <= age < hi:
                age_amt[label] += inventory
                age_cnt[label] += 1
                break

        if claimed == 0 and r["current_quantity"] > 0:
            unused_weighted += inventory * age
            unused_total_amt += inventory

    # ── Step 3: 派生指标 ──
    claim_rate_amt = round(total_claimed_amt / total_inbound_amt * 100, 2) if total_inbound_amt else 0.0
    claim_rate_qty = round(total_claimed_qty / total_inbound_qty * 100, 2) if total_inbound_qty else 0.0
    unclaimed_amt = round((total_inbound_amt - total_claimed_amt) / 10000, 2)
    total_inbound_wan = round(total_inbound_amt / 10000, 2)
    total_claimed_wan = round(total_claimed_amt / 10000, 2)
    total_inventory_wan = round(total_inventory_amt / 10000, 2)
    unclaimed_ratio = round((total_inbound_amt - total_claimed_amt) / total_inbound_amt * 100, 2) if total_inbound_amt else 0.0
    avg_age_days = round(age_weighted_sum / total_inventory_amt, 2) if total_inventory_amt else 0.0
    aged_ratio = round(aged_365_amt / total_inventory_amt, 4) if total_inventory_amt else 0.0
    unused_days = round(unused_weighted / unused_total_amt, 2) if unused_total_amt else 0.0

    age_structure = []
    for label, lo, hi in AGE_BUCKETS:
        amt = age_amt[label]
        age_structure.append({
            "range": label,
            "amount": round(amt, 2),
            "ratio": round(amt / total_inventory_amt, 4) if total_inventory_amt else 0,
            "count": age_cnt[label],
        })

    # ── Step 4: 项目维度指标（K5 + K6 项目占比 + K8） ──
    # 构建 material_code → [(project_code, pi_qty), ...] 索引
    mat_to_projects: Dict[str, List[Tuple[str, float]]] = {}
    for pi in proj_inv_rows:
        mat = pi["material_code"]
        proj = pi["owner_project_code"]
        qty = pi["pi_qty"]
        if mat not in mat_to_projects:
            mat_to_projects[mat] = []
        mat_to_projects[mat].append((proj, qty))

    # 分配库存金额到项目（O(N) 单次遍历，非 O(N×M) 嵌套）
    proj_inbound = {}
    proj_claimed = {}
    proj_inventory = {}
    proj_age_weighted = {}
    proj_over90_amt = {}
    proj_count = {}

    # 收集所有出现的 project_code
    all_projects = set()
    for r in inv_rows:
        mat = r["material_code"]
        cur_qty = r["current_quantity"]
        if mat not in mat_to_projects:
            continue
        for proj, pi_qty in mat_to_projects[mat]:
            all_projects.add(proj)
            # 按数量比例分配
            factor = pi_qty / cur_qty if cur_qty > 0 else 0
            inv_amt = r["inventory_amount"] * factor
            proj_inbound[proj] = proj_inbound.get(proj, 0.0) + r["inbound_amount"] * factor
            proj_claimed[proj] = proj_claimed.get(proj, 0.0) + r["claimed_amount"] * factor
            proj_inventory[proj] = proj_inventory.get(proj, 0.0) + inv_amt
            proj_age_weighted[proj] = proj_age_weighted.get(proj, 0.0) + inv_amt * r["age_days"]
            if r["age_days"] >= 90:
                proj_over90_amt[proj] = proj_over90_amt.get(proj, 0.0) + inv_amt
            proj_count[proj] = proj_count.get(proj, 0) + 1

    # 构建 K8 项目列表
    by_project = []
    for proj in sorted(all_projects, key=lambda p: proj_inventory.get(p, 0), reverse=True):
        inv = proj_inventory.get(proj, 0)
        inb = proj_inbound.get(proj, 0)
        clm = proj_claimed.get(proj, 0)
        age_w = proj_age_weighted.get(proj, 0)
        over90 = proj_over90_amt.get(proj, 0)
        by_project.append({
            "project_code": proj,
            "project_name": proj_name_map.get(proj, proj),
            "inbound_amount": round(inb, 2),
            "claimed_amount": round(clm, 2),
            "unclaimed_amount": round(inv, 2),
            "claim_rate": round(clm / inb * 100, 2) if inb else 0.0,
            "avg_age_days": round(age_w / inv, 2) if inv else 0.0,
            "over90_ratio": round(over90 / inv * 100, 1) if inv else 0.0,
            "record_count": proj_count.get(proj, 0),
        })

    # 项目库存占比（K6）
    project_ratios = []
    for p in by_project:
        project_ratios.append({
            "project_code": p["project_code"],
            "project_name": p["project_name"],
            "inventory_amount": p["unclaimed_amount"],
            "ratio": round(p["unclaimed_amount"] / total_inventory_amt, 4) if total_inventory_amt else 0,
        })

    # ── Step 5: 采购人维度（K6 采购人占比 + K9） ──
    purchaser_ratios = []
    by_purchaser = []
    for r in purchaser_rows:
        inv_amt = r["inventory_amt"]
        inb_amt = r["inbound_amt"]
        clm_amt = r["claimed_amt"]
        age_w = r["age_weighted"]
        name = r["purchaser_name"] or "未知"
        purchaser_ratios.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inventory_amount": round(inv_amt, 2),
            "ratio": round(inv_amt / total_inventory_amt, 4) if total_inventory_amt else 0,
        })
        by_purchaser.append({
            "purchaser_id": name,
            "purchaser_name": name,
            "inbound_amount": round(inb_amt, 2),
            "claimed_amount": round(clm_amt, 2),
            "unclaimed_amount": round(inv_amt, 2),
            "claim_rate": round(clm_amt / inb_amt * 100, 2) if inb_amt else 0.0,
            "avg_age_days": round(age_w / inv_amt, 2) if inv_amt else 0.0,
            "record_count": int(r["record_count"] or 0),
        })

    # ── Step 6: TOP 排行（Python 内存排序，O(N log N)，远快于另起 SQL） ──

    # T1: 未领用库存 TOP10（按 inventory_amount 降序）
    sorted_by_inventory = sorted(inv_rows, key=lambda r: r["inventory_amount"], reverse=True)
    top10_unclaimed = sorted_by_inventory[:10]

    # T1 物料 → 项目/采购人（仅对 10 条做查询，极快）
    top10_mats = [r["material_code"] for r in top10_unclaimed]
    top10_project = {}
    top10_purchaser = {}
    if top10_mats:
        placeholders = ",".join(["%s"] * len(top10_mats))
        proj_rows = _query(f"""
            SELECT DISTINCT ON (material_code) material_code, owner_project_code
            FROM wms_project_inventory
            WHERE del_flag = '0' AND material_code IN ({placeholders})
            ORDER BY material_code, current_quantity DESC
        """, tuple(top10_mats))
        top10_project = {r["material_code"]: r["owner_project_code"] or "" for r in proj_rows}

        purchaser_rows2 = _query(f"""
            SELECT DISTINCT ON (z.matnr) z.matnr AS material_code, z.z_user AS purchaser_name
            FROM wbs_zmmrp048_parsed z
            WHERE z.matnr IN ({placeholders}) AND z.z_user IS NOT NULL
        """, tuple(top10_mats))
        top10_purchaser = {r["material_code"]: r["purchaser_name"] or "" for r in purchaser_rows2}

    t1_items = []
    for idx, r in enumerate(top10_unclaimed):
        proj_code = top10_project.get(r["material_code"], "")
        t1_items.append({
            "rank": idx + 1,
            "material_code": r["material_code"],
            "material_name": r["material_name"],
            "inventory_amount_wan": round(r["inventory_amount"] / 10000, 2),
            "current_quantity": r["current_quantity"],
            "unit": r["unit"],
            "age_days": int(r["age_days"]),
            "owner_project_code": proj_code,
            "owner_project_name": proj_name_map.get(proj_code, ""),
            "purchaser_name": top10_purchaser.get(r["material_code"], ""),
        })

    # T2: 领用 TOP10（按金额降序）
    sorted_by_claimed = sorted(inv_rows, key=lambda r: r["claimed_amount"], reverse=True)
    top10_claimed_amt = sorted_by_claimed[:10]
    t2_by_amount = [
        {
            "rank": idx + 1,
            "material_code": r["material_code"],
            "claimed_amount_wan": round(r["claimed_amount"] / 10000, 2),
            "inbound_amount_wan": round(r["inbound_amount"] / 10000, 2),
            "inbound_date": str(r["inbound_date"]),
        }
        for idx, r in enumerate(top10_claimed_amt)
    ]

    # T2: 领用 TOP10（按数量降序）
    sorted_by_used_qty = sorted(inv_rows, key=lambda r: r["used_quantity"], reverse=True)
    top10_claimed_qty = sorted_by_used_qty[:10]
    t2_by_quantity = [
        {
            "rank": idx + 1,
            "material_code": r["material_code"],
            "claimed_quantity": r["used_quantity"],
            "inbound_quantity": r["original_quantity"],
            "inbound_date": str(r["inbound_date"]),
        }
        for idx, r in enumerate(top10_claimed_qty)
    ]

    # ── Step 7: 组装返回结构 ──

    # K1
    K1_status = _status_for_rate(claim_rate_amt, 80, "up")
    core_kpis = {
        "K1": {
            "key": "K1",
            "name": "采购领用率（金额）",
            "formula": "领用金额 / 入库金额",
            "value": claim_rate_amt,
            "unit": "%",
            "target": "≥80%",
            "target_value": 80,
            "direction": "up",
            "status": K1_status,
            "detail": {
                "claimed_amount_wan": total_claimed_wan,
                "inbound_amount_wan": total_inbound_wan,
                "unclaimed_amount_wan": unclaimed_amt,
                "claim_rate_quantity": claim_rate_qty,
            },
        },
        "K2": {
            "key": "K2",
            "name": "当前库存金额",
            "formula": "SUM(当前库存数量 × 单价)",
            "value": total_inventory_wan,
            "unit": "万元",
            "target": "控制上限，同比下降",
            "target_value": None,
            "direction": "down",
            "status": "info",
            "detail": {
                "inventory_quantity": round(total_inventory_qty, 2),
            },
        },
        "K3": {
            "key": "K3",
            "name": "长库龄库存金额占比（≥1年）",
            "formula": "库龄≥365天的库存金额 / 总库存金额",
            "value": round(aged_ratio * 100, 2),
            "unit": "%",
            "target": "逐年下降",
            "target_value": None,
            "direction": "down",
            "status": "warning" if aged_ratio > 0.15 else "ok",
            "detail": {
                "aged_amount_1y_wan": round(aged_365_amt / 10000, 2),
                "avg_age_weighted_days": avg_age_days,
                "age_structure": age_structure,
            },
        },
    }

    # K4
    K4_status = "warning" if unclaimed_ratio > 30 else "ok"
    constraint_kpis = {
        "K4": {
            "key": "K4",
            "name": "未领用采购金额",
            "formula": "入库金额 - 领用金额（针对当年入库整体）",
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
            },
        },
        "K5": {
            "key": "K5",
            "name": "项目未消耗库存",
            "formula": "按项目汇总未领用库存金额",
            "value": round(sum(p["unclaimed_amount"] for p in by_project) / 10000, 2),
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
                    for p in by_project[:10]
                ],
                "total_count": len(by_project),
            },
        },
    }

    structure_kpis = {
        "K6": {
            "key": "K6",
            "name": "库存结构分析",
            "description": "项目库存占比、采购人库存占比",
            "project_ratios": [
                {
                    "project_code": p["project_code"],
                    "project_name": p["project_name"],
                    "inventory_amount_wan": round(p["inventory_amount"] / 10000, 2),
                    "ratio": round(p["ratio"] * 100, 2),
                }
                for p in project_ratios[:10]
            ],
            "purchaser_ratios": [
                {
                    "purchaser_name": p["purchaser_name"],
                    "inventory_amount_wan": round(p["inventory_amount"] / 10000, 2),
                    "ratio": round(p["ratio"] * 100, 2),
                }
                for p in purchaser_ratios[:10]
            ],
        },
        "K7": {
            "key": "K7",
            "name": "时间分析",
            "description": "平均库龄、未动用天数",
            "avg_age_weighted_days": avg_age_days,
            "unused_days": unused_days,
            "age_structure": age_structure,
            "aged_ratio_1y": round(aged_ratio * 100, 2),
        },
        "K8": {
            "key": "K8",
            "name": "项目分析",
            "description": "回答：哪个项目带来库存",
            "items": [
                {
                    "project_code": p["project_code"],
                    "project_name": p["project_name"],
                    "claim_rate": p["claim_rate"],
                    "inventory_amount_wan": round(p["unclaimed_amount"] / 10000, 2),
                    "avg_age_days": p["avg_age_days"],
                    "over90_ratio": p["over90_ratio"],
                }
                for p in by_project
            ],
        },
        "K9": {
            "key": "K9",
            "name": "采购人分析",
            "description": "采购人领用率、未消耗库存、库龄",
            "items": [
                {
                    "purchaser_name": p["purchaser_name"],
                    "claim_rate": p["claim_rate"],
                    "unclaimed_amount_wan": round(p["unclaimed_amount"] / 10000, 2),
                    "avg_age_days": p["avg_age_days"],
                }
                for p in by_purchaser
            ],
        },
    }

    top_kpis = {
        "T1": {
            "key": "T1",
            "name": "未领用库存TOP10（金额）",
            "description": "每月必须输出，责任到项目、跟踪处理",
            "is_kpi": False,
            "items": t1_items,
        },
        "T2": {
            "key": "T2",
            "name": "领用TOP10",
            "description": "每月必须输出，用于优化备货、识别关键物资",
            "is_kpi": False,
            "by_amount": t2_by_amount,
            "by_quantity": t2_by_quantity,
        },
    }

    # Summary
    all_status_kpis = [
        core_kpis["K1"], core_kpis["K2"], core_kpis["K3"],
        constraint_kpis["K4"], constraint_kpis["K5"],
    ]
    ok_count = sum(1 for k in all_status_kpis if k["status"] == "ok")
    warning_count = sum(1 for k in all_status_kpis if k["status"] == "warning")
    alert_count = sum(1 for k in all_status_kpis if k["status"] == "alert")

    summary = {
        "update_time": TODAY.strftime("%Y-%m-%d"),
        "total_inbound_wan": total_inbound_wan,
        "total_claimed_wan": total_claimed_wan,
        "current_inventory_wan": total_inventory_wan,
        "overall_claim_rate": claim_rate_amt,
        "aged_ratio_1y": round(aged_ratio * 100, 2),
        "ok_count": ok_count,
        "warning_count": warning_count,
        "alert_count": alert_count,
    }

    return {
        "summary": summary,
        "core_kpis": core_kpis,
        "constraint_kpis": constraint_kpis,
        "structure_kpis": structure_kpis,
        "top_kpis": top_kpis,
    }
