"""
BI 快照定时任务 — 每日将 MCP 指标数据存入 KingbaseES
=====================================================

用法：
  python bi_snapshot.py              # 立即执行一次
  python bi_snapshot.py --cron       # 每天凌晨 2:00 执行（需配合 cron）
  0 2 * * * cd /path/to/backend && python bi_snapshot.py >> /var/log/bi_snapshot.log 2>&1

数据流向：
  源数据库(122.51.39.235 garden_wms) → 各 MCP 指标模块 → 目标数据库(10.239.192.131 bi_snapshot)
"""

import sys
import json
import traceback
from datetime import date, datetime
from typing import Dict, List, Any

import psycopg2
import psycopg2.extras

from db_config import DB_CONFIG_BI
from utils import query

# ── 导入所有指标模块 ──
from summary import get_summary
from claim_indicators import get_claim_indicators
from structure_indicators import (
    get_structure_indicators,
    get_structure_by_category,
)
from time_indicators import get_time_indicators, get_age_monthly, get_age_heatmap
from dimension_indicators import get_by_project, get_by_purchaser
from top_indicators import (
    get_top_unclaimed_amount,
    get_top_unclaimed_quantity,
    get_top_claimed_amount,
    get_top_claimed_quantity,
    get_optimize_suggest,
)
from other_indicators import (
    get_claim_monthly,
    get_claim_daily,
    get_claim_weekly,
    get_category_bubble,
    get_anomaly_daily,
    get_batch_digest,
    get_inventory_report,
)
from kpi_checklist import get_kpi_checklist


# ================================================================
#  目标数据库连接
# ================================================================

def get_bi_db():
    """连接 BI 快照目标数据库"""
    return psycopg2.connect(**DB_CONFIG_BI)


def ensure_tables():
    """确保所有表已创建"""
    conn = get_bi_db()
    conn.autocommit = True
    cur = conn.cursor()
    with open("sql/05_bi_snapshot_tables.sql", "r") as f:
        sql = f.read()
    # 简单按分号拆分执行
    for stmt in sql.split(";"):
        s = stmt.strip()
        if s and not s.startswith("--"):
            try:
                cur.execute(s)
            except Exception as e:
                print(f"  ⚠ 建表语句跳过: {e}")
    cur.close()
    conn.close()
    print("✅ 表结构检查完成")


def insert_rows(table: str, columns: List[str], rows: List[Dict], unique_cols: List[str] = None):
    """INSERT ... ON CONFLICT 批量写入"""
    if not rows:
        return 0
    conn = get_bi_db()
    conn.autocommit = True
    cur = conn.cursor()

    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join(columns)

    conflict_clause = ""
    if unique_cols:
        conflict_cols = ", ".join(unique_cols)
        update_cols = ", ".join([f"{c} = EXCLUDED.{c}" for c in columns if c not in unique_cols])
        conflict_clause = f"ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_cols}"

    sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) {conflict_clause}"
    count = 0
    for row in rows:
        try:
            vals = [row.get(c) for c in columns]
            cur.execute(sql, vals)
            count += 1
        except Exception as e:
            print(f"  ⚠ 插入失败 {table}: {e}")
    cur.close()
    conn.close()
    return count


# ================================================================
#  各表写入函数
# ================================================================

def save_kpi_summary(snapshot_date: str):
    """表 1: bi_kpi_summary"""
    data = get_summary()
    row = {
        "snapshot_date": snapshot_date,
        "total_inbound_amount": data.get("total_inbound_amount", 0),
        "total_claimed_amount": data.get("total_claimed_amount", 0),
        "total_inventory_amount": data.get("total_inventory_amount", 0),
        "total_inventory_quantity": data.get("total_inventory_quantity", 0),
        "total_records": data.get("total_records", 0),
        "claim_rate": data.get("claim_rate", 0),
        "aged_amount_1y": data.get("aged_amount_1y", 0),
        "aged_ratio_1y": data.get("aged_ratio_1y", 0),
        "avg_age_weighted_days": data.get("avg_age_weighted_days", 0),
    }
    # 恒等式
    idt = data.get("identity_check", {})
    row["identity_inbound_minus_claimed"] = idt.get("inbound_minus_claimed")
    row["identity_actual_inventory"] = idt.get("actual_inventory")
    row["identity_deviation_wan"] = idt.get("deviation_wan")
    row["identity_deviation_pct"] = idt.get("deviation_pct")
    row["identity_holds"] = idt.get("holds")

    cols = list(row.keys())
    insert_rows("bi_kpi_summary", cols, [row], ["snapshot_date"])


def save_claim_indicators(snapshot_date: str):
    """表 2: bi_claim_indicators"""
    data = get_claim_indicators()
    rows = []
    for period in ["all", "year"]:
        p = data[period]
        rows.append({
            "snapshot_date": snapshot_date,
            "period_type": period,
            "current_year": data["current_year"],
            "total_inbound_amount": p.get("total_inbound_amount", 0),
            "total_claimed_amount": p.get("total_claimed_amount", 0),
            "claim_rate_amount": p.get("claim_rate_amount", 0),
            "total_inbound_quantity": p.get("total_inbound_quantity", 0),
            "total_claimed_quantity": p.get("total_claimed_quantity", 0),
            "claim_rate_quantity": p.get("claim_rate_quantity", 0),
            "unclaimed_amount": p.get("unclaimed_amount", 0),
            "unclaimed_amount_ratio": p.get("unclaimed_amount_ratio", 0),
        })
    cols = list(rows[0].keys())
    insert_rows("bi_claim_indicators", cols, rows, ["snapshot_date", "period_type"])


def save_structure_indicators(snapshot_date: str):
    """表 3: bi_structure_indicators"""
    data = get_structure_indicators()
    row = {
        "snapshot_date": snapshot_date,
        "current_year": data.get("current_year", date.today().year),
        "current_inventory_amount": data.get("current_inventory_amount", 0),
        "current_year_inventory_amount": data.get("current_year_inventory_amount", 0),
        "current_inventory_quantity": data.get("current_inventory_quantity", 0),
        "project_ratios_json": json.dumps(data.get("project_ratios", []), ensure_ascii=False),
        "purchaser_ratios_json": json.dumps(data.get("purchaser_ratios", []), ensure_ascii=False),
    }
    cols = list(row.keys())
    insert_rows("bi_structure_indicators", cols, [row], ["snapshot_date"])


def save_age_indicators(snapshot_date: str):
    """表 4: bi_age_indicators"""
    data = get_time_indicators()
    row = {
        "snapshot_date": snapshot_date,
        "aged_ratio_1y": data.get("aged_ratio_1y", 0),
        "aged_amount_1y": data.get("aged_amount_1y", 0),
        "avg_age_weighted_days": data.get("avg_age_weighted_days", 0),
        "age_structure_json": json.dumps(data.get("age_structure", []), ensure_ascii=False),
    }
    cols = list(row.keys())
    insert_rows("bi_age_indicators", cols, [row], ["snapshot_date"])


def save_dimension_project(snapshot_date: str):
    """表 5: bi_dimension_project"""
    rows = get_by_project()
    for r in rows:
        r["snapshot_date"] = snapshot_date
    if rows:
        cols = ["snapshot_date", "project_code", "project_name", "inbound_amount",
                "claimed_amount", "inventory_amount", "claim_rate", "avg_age_days",
                "over90_ratio", "record_count"]
        # 字段名映射
        mapped = []
        for r in rows:
            mapped.append({
                "snapshot_date": snapshot_date,
                "project_code": r.get("project_code", ""),
                "project_name": r.get("project_name", ""),
                "inbound_amount": r.get("inbound_amount", 0),
                "claimed_amount": r.get("claimed_amount", 0),
                "inventory_amount": r.get("unclaimed_amount", 0),  # = 未消耗库存
                "claim_rate": r.get("claim_rate", 0),
                "avg_age_days": r.get("avg_age_days", 0),
                "over90_ratio": r.get("over90_ratio", 0),
                "record_count": r.get("record_count", 0),
            })
        insert_rows("bi_dimension_project", cols, mapped, ["snapshot_date", "project_code"])


def save_dimension_purchaser(snapshot_date: str):
    """表 6: bi_dimension_purchaser"""
    rows = get_by_purchaser()
    if rows:
        cols = ["snapshot_date", "purchaser_name", "inbound_amount",
                "claimed_amount", "inventory_amount", "claim_rate",
                "avg_age_days", "record_count"]
        mapped = []
        for r in rows:
            mapped.append({
                "snapshot_date": snapshot_date,
                "purchaser_name": r.get("purchaser_name", ""),
                "inbound_amount": r.get("inbound_amount", 0),
                "claimed_amount": r.get("claimed_amount", 0),
                "inventory_amount": r.get("unclaimed_amount", 0),
                "claim_rate": r.get("claim_rate", 0),
                "avg_age_days": r.get("avg_age_days", 0),
                "record_count": r.get("record_count", 0),
            })
        insert_rows("bi_dimension_purchaser", cols, mapped, ["snapshot_date", "purchaser_name"])


def save_top_ranking(snapshot_date: str):
    """表 7: bi_top_ranking"""
    cols = ["snapshot_date", "rank_type", "rank_position", "material_code",
            "material_name", "batch_code", "inventory_amount", "current_quantity",
            "claimed_amount", "claimed_quantity", "inbound_amount", "unit_price",
            "unit", "age_days", "inbound_date", "project_code", "project_name",
            "purchaser_name"]

    all_rows = []
    for rank_type, fetch_fn, limit in [
        ("unclaimed_amount", get_top_unclaimed_amount, 10),
        ("unclaimed_quantity", get_top_unclaimed_quantity, 10),
        ("claimed_amount", get_top_claimed_amount, 10),
        ("claimed_quantity", get_top_claimed_quantity, 10),
    ]:
        try:
            items = fetch_fn(limit)
            for i, item in enumerate(items):
                all_rows.append({
                    "snapshot_date": snapshot_date,
                    "rank_type": rank_type,
                    "rank_position": i + 1,
                    "material_code": item.get("material_code", ""),
                    "material_name": item.get("material_name", ""),
                    "batch_code": item.get("batch_code", ""),
                    "inventory_amount": item.get("inventory_amount", 0),
                    "current_quantity": item.get("current_quantity", 0),
                    "claimed_amount": item.get("claimed_amount", 0),
                    "claimed_quantity": item.get("claimed_quantity", 0),
                    "inbound_amount": item.get("inbound_amount", 0),
                    "unit_price": item.get("unit_price", 0),
                    "unit": item.get("unit", ""),
                    "age_days": item.get("age_days", 0),
                    "inbound_date": item.get("inbound_date"),
                    "project_code": item.get("project_code", ""),
                    "project_name": item.get("project_name", ""),
                    "purchaser_name": item.get("purchaser_name", ""),
                })
        except Exception as e:
            print(f"  ⚠ TOP {rank_type}: {e}")

    insert_rows("bi_top_ranking", cols, all_rows, ["snapshot_date", "rank_type", "rank_position"])


def save_time_series(snapshot_date: str):
    """表 8: bi_time_series (月/日/周)"""
    cols = ["snapshot_date", "granularity", "period_label",
            "inbound_amount", "claimed_amount", "net_amount", "claim_rate"]
    all_rows = []

    for granularity, fetch_fn, label_key in [
        ("monthly", get_claim_monthly, "month"),
        ("daily", get_claim_daily, "day"),
        ("weekly", get_claim_weekly, "week"),
    ]:
        try:
            data = fetch_fn()
            items = data.get("data", [])
            for item in items:
                all_rows.append({
                    "snapshot_date": snapshot_date,
                    "granularity": granularity,
                    "period_label": str(item.get(label_key, "")),
                    "inbound_amount": item.get("inbound_amount", 0),
                    "claimed_amount": item.get("claimed_amount", 0),
                    "net_amount": item.get("net_amount", 0),
                    "claim_rate": item.get("claim_rate", 0),
                })
        except Exception as e:
            print(f"  ⚠ 时序 {granularity}: {e}")

    insert_rows("bi_time_series", cols, all_rows, ["snapshot_date", "granularity", "period_label"])

    # 库龄月度趋势也写这里
    try:
        am = get_age_monthly()
        for item in am.get("data", []):
            all_rows.append({
                "snapshot_date": snapshot_date,
                "granularity": "age_monthly",
                "period_label": str(item.get("month", "")),
                "inbound_amount": item.get("avg_age", 0),
                "claimed_amount": item.get("over90_rate", 0),
                "net_amount": 0,
                "claim_rate": 0,
            })
        insert_rows("bi_time_series", cols, all_rows, ["snapshot_date", "granularity", "period_label"])
    except Exception as e:
        print(f"  ⚠ 库龄月度: {e}")


def save_batch_digest(snapshot_date: str):
    """表 9: bi_batch_digest"""
    try:
        data = get_batch_digest()
        items = data.get("data", [])
        cols = ["snapshot_date", "batch_code", "inbound_wan", "remain_pct",
                "avg_age_days", "digest_data_json", "color_hex"]
        rows = []
        for item in items:
            rows.append({
                "snapshot_date": snapshot_date,
                "batch_code": str(item.get("batch_code", "")),
                "inbound_wan": item.get("inbound_wan", 0),
                "remain_pct": item.get("remain_pct", 0),
                "avg_age_days": item.get("avg_age_days", 0),
                "digest_data_json": json.dumps(item.get("digest_data", []), ensure_ascii=False),
                "color_hex": item.get("color_hex", ""),
            })
        insert_rows("bi_batch_digest", cols, rows, ["snapshot_date", "batch_code"])
    except Exception as e:
        print(f"  ⚠ 批次消化: {e}")


def save_anomaly_detection(snapshot_date: str):
    """表 10: bi_anomaly_detection"""
    try:
        data = get_anomaly_daily()
        items = data.get("data", [])
        cols = ["snapshot_date", "week_label", "inbound_amount", "claimed_amount",
                "anomaly_type", "anomaly_label", "huanbi_pct"]
        rows = []
        for item in items:
            rows.append({
                "snapshot_date": snapshot_date,
                "week_label": str(item.get("week", item.get("date", ""))),
                "inbound_amount": item.get("inbound_amount", 0),
                "claimed_amount": item.get("claimed_amount", 0),
                "anomaly_type": item.get("type", 0),
                "anomaly_label": item.get("label", ""),
                "huanbi_pct": item.get("huanbi", 0),
            })
        insert_rows("bi_anomaly_detection", cols, rows, ["snapshot_date", "week_label"])
    except Exception as e:
        print(f"  ⚠ 异常检测: {e}")


def save_kpi_checklist(snapshot_date: str):
    """表 11: bi_kpi_checklist"""
    try:
        data = get_kpi_checklist()
        summary = data.get("summary", {})
        row = {
            "snapshot_date": snapshot_date,
            "total_inbound_wan": summary.get("total_inbound_wan", 0),
            "total_claimed_wan": summary.get("total_claimed_wan", 0),
            "current_inventory_wan": summary.get("current_inventory_wan", 0),
            "overall_claim_rate": summary.get("overall_claim_rate", 0),
            "aged_ratio_1y": summary.get("aged_ratio_1y", 0),
            "ok_count": summary.get("ok_count", 0),
            "warning_count": summary.get("warning_count", 0),
            "alert_count": summary.get("alert_count", 0),
            "identity_deviation_pct": summary.get("identity_deviation_pct"),
            "identity_holds": summary.get("identity_holds"),
            "core_kpis_json": json.dumps(data.get("core_kpis", {}), ensure_ascii=False, default=str),
            "constraint_kpis_json": json.dumps(data.get("constraint_kpis", {}), ensure_ascii=False, default=str),
            "structure_kpis_json": json.dumps(data.get("structure_kpis", {}), ensure_ascii=False, default=str),
            "top_kpis_json": json.dumps(data.get("top_kpis", {}), ensure_ascii=False, default=str),
            "data_start_date": summary.get("data_start_date"),
            "data_end_date": summary.get("data_end_date"),
        }
        cols = list(row.keys())
        insert_rows("bi_kpi_checklist", cols, [row], ["snapshot_date"])
    except Exception as e:
        print(f"  ⚠ KPI考核: {e}")


def save_safety_stock(snapshot_date: str):
    """表 12: bi_safety_stock"""
    try:
        data = get_structure_by_category()
        items = data.get("data", [])
        cols = ["snapshot_date", "rank_position", "material_code", "category_name",
                "current_amount", "safe_max", "safe_min", "record_count"]
        rows = []
        for i, item in enumerate(items):
            rows.append({
                "snapshot_date": snapshot_date,
                "rank_position": i + 1 if i < 10 else 99,
                "material_code": item.get("material_code", ""),
                "category_name": item.get("category", ""),
                "current_amount": item.get("current", 0),
                "safe_max": item.get("safe_max", 0),
                "safe_min": item.get("safe_min", 0),
                "record_count": item.get("record_count", 0),
            })
        insert_rows("bi_safety_stock", cols, rows, ["snapshot_date", "material_code"])
    except Exception as e:
        print(f"  ⚠ 安全库存: {e}")


def save_inventory_report(snapshot_date: str):
    """表 13: bi_inventory_report"""
    try:
        data = get_inventory_report(limit=10000)
        items = data.get("rows", [])
        cols = ["snapshot_date", "purchase_batch", "material_name", "material_code",
                "project_code", "project_name", "purchaser_name", "submitter_name",
                "contact_name", "project_type", "inbound_date", "putaway_date",
                "batch_code", "original_quantity", "current_quantity", "used_quantity",
                "pick_quantity", "repair_quantity", "scrap_quantity", "repaired_quantity",
                "unit_price", "unit", "supplier_code", "inbound_amount", "claimed_amount",
                "inventory_amount", "claim_rate", "age_days"]
        rows = []
        for item in items:
            rows.append({
                "snapshot_date": snapshot_date,
                "purchase_batch": item.get("purchase_batch", ""),
                "material_name": item.get("material_name", ""),
                "material_code": item.get("material_code", ""),
                "project_code": item.get("project_code", ""),
                "project_name": item.get("project_name", ""),
                "purchaser_name": item.get("purchaser_name", ""),
                "submitter_name": item.get("applicant_name", ""),
                "contact_name": item.get("contact_name", ""),
                "project_type": item.get("project_type", ""),
                "inbound_date": item.get("inbound_date"),
                "putaway_date": item.get("putaway_date"),
                "batch_code": item.get("batch_code", ""),
                "original_quantity": item.get("original_quantity", 0),
                "current_quantity": item.get("current_quantity", 0),
                "used_quantity": item.get("used_quantity", 0),
                "pick_quantity": item.get("pick_quantity", 0),
                "repair_quantity": item.get("repair_quantity", 0),
                "scrap_quantity": item.get("scrap_quantity", 0),
                "repaired_quantity": item.get("repaired_quantity", 0),
                "unit_price": item.get("unit_price", 0),
                "unit": item.get("unit", ""),
                "supplier_code": item.get("supplier_code", ""),
                "inbound_amount": item.get("inbound_amount", 0),
                "claimed_amount": item.get("claimed_amount", 0),
                "inventory_amount": item.get("inventory_amount", 0),
                "claim_rate": item.get("claim_rate", 0),
                "age_days": item.get("age_days", 0),
            })
        insert_rows("bi_inventory_report", cols, rows, ["snapshot_date", "material_code", "purchase_batch", "project_code"])
    except Exception as e:
        print(f"  ⚠ 库存报表: {e}")
        traceback.print_exc()


def save_category_bubble(snapshot_date: str):
    """附加表: bi_category_bubble"""
    try:
        data = get_category_bubble()
        items = data.get("data", [])
        cols = ["snapshot_date", "category_code", "category_name", "inventory_amount",
                "inbound_amount", "claimed_amount", "claim_rate", "sku_count", "record_count"]
        rows = []
        for item in items:
            rows.append({
                "snapshot_date": snapshot_date,
                "category_code": item.get("material_code", item.get("category_code", "")),
                "category_name": item.get("category", ""),
                "inventory_amount": item.get("inventory_amount", 0),
                "inbound_amount": item.get("inbound_amount", 0),
                "claimed_amount": item.get("claimed_amount", 0),
                "claim_rate": item.get("claim_rate", 0),
                "sku_count": item.get("sku_count", 0),
                "record_count": item.get("record_count", 0),
            })
        insert_rows("bi_category_bubble", cols, rows, ["snapshot_date", "category_code"])
    except Exception as e:
        print(f"  ⚠ 类别气泡: {e}")


# ================================================================
#  主流程
# ================================================================

# 所有保存任务（按表顺序）
SAVE_TASKS = [
    ("bi_kpi_summary",         save_kpi_summary),
    ("bi_claim_indicators",    save_claim_indicators),
    ("bi_structure_indicators", save_structure_indicators),
    ("bi_age_indicators",      save_age_indicators),
    ("bi_dimension_project",   save_dimension_project),
    ("bi_dimension_purchaser", save_dimension_purchaser),
    ("bi_top_ranking",         save_top_ranking),
    ("bi_time_series",         save_time_series),
    ("bi_batch_digest",        save_batch_digest),
    ("bi_anomaly_detection",   save_anomaly_detection),
    ("bi_kpi_checklist",       save_kpi_checklist),
    ("bi_safety_stock",        save_safety_stock),
    ("bi_inventory_report",    save_inventory_report),
    ("bi_category_bubble",     save_category_bubble),
]


def run_snapshot():
    """执行一次完整快照"""
    today = date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"  BI 快照 {today}")
    print(f"{'='*60}")

    # 1. 确保表存在
    ensure_tables()

    # 2. 逐表写入
    success = 0
    fail = 0
    for table_name, save_fn in SAVE_TASKS:
        try:
            print(f"  → {table_name}...", end=" ")
            save_fn(today)
            print("✅")
            success += 1
        except Exception as e:
            print(f"❌ {e}")
            fail += 1
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"  成功 {success}/{len(SAVE_TASKS)}, 失败 {fail}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if "--cron" in sys.argv:
        # Cron 模式：每天凌晨 2:00 循环
        import time as _time
        print("🕐 BI Snapshot cron mode, waiting for 02:00...")
        while True:
            now = datetime.now()
            if now.hour == 2 and now.minute == 0:
                run_snapshot()
                _time.sleep(86400)  # 一天后再检查
            _time.sleep(30)
    else:
        run_snapshot()