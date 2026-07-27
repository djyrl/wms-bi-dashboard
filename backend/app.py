"""
采购库存 BI Dashboard — Flask 后端
===================================
数据源：v_project_inventory_wide 视图（人大金仓 KingbaseES）
"""

import os
from flask import Flask, jsonify, request, send_from_directory, redirect
from flask_cors import CORS
import psycopg2
import psycopg2.extras

# 人大金仓真实数据计算模块
from cross_indicators import (
    get_project_matrix as db_get_project_matrix,
    get_project_types as db_get_project_types,
    get_top_projects as db_get_top_projects,
    get_project_trend as db_get_project_trend,
    get_source_distribution as db_get_source_distribution,
    get_distinct_values as db_get_distinct_values,
    get_available_dimensions as db_get_available_dimensions,
)
from kpi_checklist import get_kpi_checklist
from summary import get_summary as db_get_summary
from claim_indicators import get_claim_indicators as db_get_claim_indicators
from structure_indicators import (
    get_structure_indicators as db_get_structure_indicators,
    get_structure_by_category as db_get_structure_by_category,
    get_source_structure as db_get_source_structure,
)
from time_indicators import (
    get_time_indicators as db_get_time_indicators,
    get_age_layers as db_get_age_layers,
    get_age_monthly as db_get_age_monthly,
    get_age_heatmap as db_get_age_heatmap,
)
from dimension_indicators import (
    get_by_project as db_get_by_project,
    get_by_purchaser as db_get_by_purchaser,
    get_project_summary as db_get_project_summary,
    get_purchaser_summary as db_get_purchaser_summary,
)
from top_indicators import (
    get_top_unclaimed_amount as db_get_top_unclaimed_amount,
    get_top_unclaimed_quantity as db_get_top_unclaimed_quantity,
    get_top_claimed_amount as db_get_top_claimed_amount,
    get_top_claimed_quantity as db_get_top_claimed_quantity,
    get_optimize_suggest as db_get_optimize_suggest,
)
from other_indicators import (
    get_claim_monthly as db_get_claim_monthly,
    get_claim_yearly as db_get_claim_yearly,
    get_claim_daily as db_get_claim_daily,
    get_claim_weekly as db_get_claim_weekly,
    get_category_bubble as db_get_category_bubble,
    get_anomaly_daily as db_get_anomaly_daily,
    get_batch_digest as db_get_batch_digest,
    get_inventory_report as db_get_inventory_report,
)

app = Flask(__name__)
CORS(app)

# ================================================================
# 人大金仓（KingbaseES）数据库连接配置
# ================================================================
from db_config import DB_CONFIG

def get_db():
    """获取数据库连接。"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def query_table(table_name: str):
    """通用数据库查询，支持 ?limit=&offset= 分页。"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        sql = f"SELECT * FROM {table_name} ORDER BY 1"
        params = []

        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)
        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            sql += " OFFSET %s"
            params.append(offset)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()

        return {"code": 0, "data": rows, "total": len(rows)}
    except Exception as e:
        return {"code": -1, "msg": str(e)}
    finally:
        if conn:
            conn.close()


def ok(data):
    return jsonify({"code": 0, "data": data})


# ================================================================
#  兼容 URL — 旧 mock API 路径重定向至真实 WMS 端点
# ================================================================

_REDIRECT_MAP = {
    "/api/summary":                          "/api/wms/indicators/summary",
    "/api/indicators/claim":                 "/api/wms/indicators/claim",
    "/api/indicators/structure":             "/api/wms/indicators/structure",
    "/api/indicators/time":                  "/api/wms/indicators/time",
    "/api/indicators/age-layers":            "/api/wms/indicators/age-layers",
    "/api/indicators/by-project":            "/api/wms/indicators/by-project",
    "/api/indicators/by-purchaser":          "/api/wms/indicators/by-purchaser",
    "/api/top/unclaimed-amount":             "/api/wms/indicators/top/unclaimed-amount",
    "/api/top/unclaimed-quantity":           "/api/wms/indicators/top/unclaimed-quantity",
    "/api/top/claimed-amount":               "/api/wms/indicators/top/claimed-amount",
    "/api/top/claimed-quantity":             "/api/wms/indicators/top/claimed-quantity",
}


def _add_redirect_routes():
    """为旧 mock API 路径注册 HTTP 307 重定向到新的 WMS 端点。"""
    for old_path, new_path in _REDIRECT_MAP.items():
        endpoint_name = f"redirect_{old_path.replace('/', '_').strip('_')}"

        def _make_handler(target=new_path, methods=["GET"]):
            def _handler():
                return redirect(target, code=307)
            return _handler

        app.add_url_rule(old_path, endpoint_name, _make_handler(), methods=["GET"])


_add_redirect_routes()


# 特殊兼容：/api/dimensions/<dim_type> → /api/wms/indicators/distinct-values
_DIM_FIELD_MAP = {
    "materials": "material_code",
    "projects": "project_code",
    "purchasers": "purchaser_name",
}

@app.route("/api/dimensions/<dim_type>", methods=["GET"])
def api_dimensions_compat(dim_type: str):
    field = _DIM_FIELD_MAP.get(dim_type, dim_type)
    target = f"/api/wms/indicators/distinct-values?field={field}"
    return redirect(target, code=307)


# 特殊兼容：/api/drill/batches → /api/wms/indicators/age-layers
@app.route("/api/drill/batches", methods=["GET"])
def api_drill_batches_compat():
    params = []
    for old_key, new_key in [
        ("min_age", "min_age"),
        ("max_age", "max_age"),
    ]:
        val = request.args.get(old_key)
        if val is not None:
            params.append(f"{new_key}={val}")
    target = "/api/wms/indicators/age-layers"
    if params:
        target += "?" + "&".join(params)
    return redirect(target, code=307)


# ================================================================
#  人大金仓数据库接口 — WMS 核心表查询
# ================================================================

@app.route("/api/wms/inventory", methods=["GET"])
def api_wms_inventory():
    """GET /api/wms/inventory?limit=&offset= — 库存表"""
    result = query_table("wms_inventory")
    return jsonify(result)


@app.route("/api/wms/project-inventory", methods=["GET"])
def api_wms_project_inventory():
    """GET /api/wms/project-inventory?limit=&offset= — 项目库存表"""
    result = query_table("wms_project_inventory")
    return jsonify(result)


@app.route("/api/wms/material", methods=["GET"])
def api_wms_material():
    """GET /api/wms/material?limit=&offset= — 物料表"""
    result = query_table("wms_material")
    return jsonify(result)


@app.route("/api/wms/inbound-order", methods=["GET"])
def api_wms_inbound_order():
    """GET /api/wms/inbound-order?limit=&offset= — 入库单表"""
    result = query_table("wms_inbound_order")
    return jsonify(result)


@app.route("/api/wms/health", methods=["GET"])
def api_wms_health():
    """数据库连通性检查"""
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return jsonify({"code": 0, "msg": "数据库连接正常"})
    except Exception as e:
        return jsonify({"code": -1, "msg": f"数据库连接失败: {e}"})
    finally:
        if conn:
            conn.close()


# ================================================================
#  人大金仓指标计算接口 — 22 个指标
# ================================================================

@app.route("/api/wms/indicators/summary", methods=["GET"])
def api_wms_summary():
    """0. KPI 总览：入库总额、库存总额、平均库龄等"""
    try:
        return ok(db_get_summary())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/claim", methods=["GET"])
def api_wms_claim():
    """
    1. 当年采购领用率（金额） / 全部采购领用率（金额） = 领用金额 / 入库金额
    2. 当年采购领用率（数量） / 全部采购领用率（数量） = 领用数量 / 入库数量
    3. 当年未领用采购金额 / 全部未领用采购金额 = 入库金额 - 净领用金额
    4. 当年未领用采购占比（金额） / 全部未领用采购占比（金额） = 未领用金额 / 入库金额
    当年区间：当前自然年；NULL 入库日期不计入当年。
    """
    try:
        return ok(db_get_claim_indicators())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/structure", methods=["GET"])
def api_wms_structure():
    """
    5. 当前库存金额（全部 / 当年）
    6. 当前库存数量
    7. 项目库存占比
    8. 采购人库存占比
    当年区间：当前自然年；NULL 入库日期不计入当年。
    """
    try:
        return ok(db_get_structure_indicators())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/time", methods=["GET"])
def api_wms_time():
    """
    9. 长库龄库存金额占比（≥1年）
    10. 库龄结构占比（≤1年、1~3年、3~5年、≥5年）
    11. 平均库龄（金额加权）= Σ（库存金额 × 库龄） / 总库存金额
    """
    try:
        return ok(db_get_time_indicators())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/age-layers", methods=["GET"])
def api_wms_age_layers():
    """
    12. 库龄分层统计
    筛选条件：?min_amount=100000&min_age=365&max_age=1095
    """
    try:
        min_amount = request.args.get("min_amount", 0, type=float)
        min_age = request.args.get("min_age", 0, type=int)
        max_age = request.args.get("max_age", None, type=int)
        return ok(db_get_age_layers(min_amount, min_age, max_age))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/by-project", methods=["GET"])
def api_wms_by_project():
    """
    13. 项目采购领用率
    14. 项目未消耗库存金额
    15. 项目平均库龄
    """
    try:
        return ok(db_get_by_project())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/by-purchaser", methods=["GET"])
def api_wms_by_purchaser():
    """
    16. 采购人领用率
    17. 采购人未消耗库存金额
    18. 采购人库存库龄
    """
    try:
        return ok(db_get_by_purchaser())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/top/unclaimed-amount", methods=["GET"])
def api_wms_top_unclaimed_amount():
    """19. 未领用库存 TOP（金额）?limit=10"""
    limit = request.args.get("limit", 10, type=int)
    try:
        return ok(db_get_top_unclaimed_amount(limit))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/top/unclaimed-quantity", methods=["GET"])
def api_wms_top_unclaimed_quantity():
    """20. 未领用库存 TOP（数量）?limit=10"""
    limit = request.args.get("limit", 10, type=int)
    try:
        return ok(db_get_top_unclaimed_quantity(limit))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/top/claimed-amount", methods=["GET"])
def api_wms_top_claimed_amount():
    """21. 领用 TOP（金额）?limit=10"""
    limit = request.args.get("limit", 10, type=int)
    try:
        return ok(db_get_top_claimed_amount(limit))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/top/claimed-quantity", methods=["GET"])
def api_wms_top_claimed_quantity():
    """22. 领用 TOP（数量）?limit=10"""
    limit = request.args.get("limit", 10, type=int)
    try:
        return ok(db_get_top_claimed_quantity(limit))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


# ================================================================
#  主题一专属接口（时序 & 维度补充）
# ================================================================

@app.route("/api/wms/indicators/claim/monthly", methods=["GET"])
def api_wms_claim_monthly():
    """
    按月统计入库金额、领用金额、领用率（最近12个月）。
    供「领用率月度趋势」「入库vs领用对比」图表使用。
    """
    try:
        return ok(db_get_claim_monthly())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/claim/yearly", methods=["GET"])
def api_wms_claim_yearly():
    """按年统计入库金额、领用金额、领用率（全部年份）。"""
    try:
        return ok(db_get_claim_yearly())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/claim/daily", methods=["GET"])
def api_wms_claim_daily():
    """
    按天统计当月入库金额、领用金额、领用率。
    供「领用率月度趋势」「入库vs领用对比」图表使用（日粒度）。
    """
    try:
        return ok(db_get_claim_daily())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/claim/weekly", methods=["GET"])
def api_wms_claim_weekly():
    """
    按周统计入库金额、领用金额、领用率（最近12周）。
    供「领用率趋势」「入库vs领用对比」图表使用（周粒度）。
    """
    try:
        return ok(db_get_claim_weekly())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/structure/by-category", methods=["GET"])
def api_wms_structure_by_category():
    """
    按物料编码统计库存金额，含安全上限/下限。
    供「在库水位 · 安全库存偏离度」图表使用（Theme1）。
    """
    try:
        return ok(db_get_structure_by_category())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/category/bubble", methods=["GET"])
def api_wms_category_bubble():
    """
    按物资类别统计库存金额、领用率、SKU数。
    供「按物料类别 · 库存金额与领用率」气泡图使用（Theme2）。
    """
    try:
        return ok(db_get_category_bubble())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/batch/digest", methods=["GET"])
def api_wms_batch_digest():
    """批次消化进度：按入库月份统计入库/剩余/消耗金额"""
    try:
        return ok(db_get_batch_digest())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/anomaly/daily", methods=["GET"])
def api_wms_anomaly_daily():
    """
    近N天逐日入库/领用异常检测（2σ法），默认30天。
    供「库存异常变动预警日历」图表使用。
    """
    days = request.args.get("days", 30, type=int)
    try:
        return ok(db_get_anomaly_daily(days))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/age/monthly", methods=["GET"])
def api_wms_age_monthly():
    """
    按月计算加权平均库龄和超90天占比（最近12个月）。
    供「平均库龄月度趋势」图表使用。
    """
    try:
        return ok(db_get_age_monthly())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/age/heatmap", methods=["GET"])
def api_wms_age_heatmap():
    """
    按物料类别 × 库龄段交叉统计库存金额（TOP 10 类别 × 6 库龄段）。
    供「滞留库存热力图」图表使用。
    """
    try:
        return ok(db_get_age_heatmap())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/optimize-suggest", methods=["GET"])
def api_wms_optimize_suggest():
    """智能备货优化建议：基于日均消耗推荐安全库存上限"""
    limit = request.args.get("limit", 8, type=int)
    safety_days = request.args.get("safety_days", 60, type=int)
    try:
        return ok(db_get_optimize_suggest(limit, safety_days))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/inventory-report", methods=["GET"])
def api_wms_inventory_report():
    """
    采购批次库存报表。
    参数：?sort_by=claim_rate|age_days|inventory_amount&sort_order=asc|desc&limit=500&offset=0
    """
    sort_by = request.args.get("sort_by", "inventory_amount")
    sort_order = request.args.get("sort_order", "desc")
    limit = request.args.get("limit", 500, type=int)
    offset = request.args.get("offset", 0, type=int)
    try:
        return ok(db_get_inventory_report(sort_by, sort_order, limit, offset))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/project-summary", methods=["GET"])
def api_wms_project_summary():
    """
    项目库存追溯汇总表。
    参数：?sort_by=inventory_amount|claim_rate|avg_age_days&sort_order=desc|asc
    """
    sort_by = request.args.get("sort_by", "inventory_amount")
    sort_order = request.args.get("sort_order", "desc")
    try:
        return ok(db_get_project_summary(sort_by, sort_order))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/project-matrix", methods=["GET"])
def api_wms_project_matrix():
    """
    项目 × 时间 热力图矩阵
    参数：?metric=inventory_amount&project_type=A修&months=12
    """
    metric = request.args.get("metric", "inventory_amount")
    project_type = request.args.get("project_type", None)
    months = request.args.get("months", 12, type=int)
    try:
        return ok(db_get_project_matrix(metric, project_type, months))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/project-types", methods=["GET"])
def api_wms_project_types():
    try:
        return ok(db_get_project_types())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/project-top", methods=["GET"])
def api_wms_project_top():
    metric = request.args.get("metric", "inventory_amount")
    project_type = request.args.get("project_type", None)
    limit = request.args.get("limit", 15, type=int)
    group_by = request.args.get("group_by", "project")
    try:
        return ok(db_get_top_projects(metric, project_type, limit, group_by))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/project-trend", methods=["GET"])
def api_wms_project_trend():
    metric = request.args.get("metric", "inventory_amount")
    project_type = request.args.get("project_type", None)
    months = request.args.get("months", 12, type=int)
    try:
        return ok(db_get_project_trend(project_type, metric, months))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/source-distribution", methods=["GET"])
def api_wms_source_distribution():
    project_type = request.args.get("project_type", None)
    try:
        return ok(db_get_source_distribution(project_type))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/available-dimensions", methods=["GET"])
def api_wms_dimensions():
    try:
        return ok(db_get_available_dimensions())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/distinct-values", methods=["GET"])
def api_wms_distinct_values():
    field = request.args.get("field", "")
    project_type = request.args.get("project_type", None)
    project_code = request.args.get("project_code", None)
    try:
        return ok(db_get_distinct_values(field, project_type, project_code))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/purchaser-summary", methods=["GET"])
def api_wms_purchaser_summary():
    """
    采购人库存追溯汇总表。
    参数：?sort_by=inventory_amount|claim_rate|avg_age_days&sort_order=desc|asc
    """
    sort_by = request.args.get("sort_by", "inventory_amount")
    sort_order = request.args.get("sort_order", "desc")
    try:
        return ok(db_get_purchaser_summary(sort_by, sort_order))
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/source-structure", methods=["GET"])
def api_wms_source_structure():
    """库存来源结构表。"""
    try:
        return ok(db_get_source_structure())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


# ================================================================
#  KPI 考核清单接口
# ================================================================

@app.route("/api/wms/indicators/kpi-checklist", methods=["GET"])
def api_wms_kpi_checklist():
    """
    KPI 考核清单 — 包含 K1-K9 考核指标和 T1-T2 TOP指标。
    返回四类指标：
      第一类：核心考核指标（K1-K3）
      第二类：约束类考核指标（K4-K5）
      第三类：结构分析指标（K6-K9）
      第四类：TOP类指标（T1-T2，不考核）
    """
    try:
        return ok(get_kpi_checklist())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


# ================================================================
#  调试接口 — 逐个测试各模块，帮助定位线上问题
# ================================================================

@app.route("/api/wms/debug", methods=["GET"])
def api_wms_debug():
    """
    逐个运行 compute_indicators 中的函数，返回每个函数的执行结果。
    成功 → 返回数据摘要；失败 → 返回完整 traceback。
    访问 http://服务器IP:端口/api/wms/debug 即可在线诊断。
    """
    import traceback
    import time

    results = {}

    # ---- compute_indicators 各函数 ----
    indicator_tests = [
        ("summary", "db_get_summary"),
        ("claim", "db_get_claim_indicators"),
        ("structure", "db_get_structure_indicators"),
        ("time", "db_get_time_indicators"),
        ("by_project", "db_get_by_project"),
        ("by_purchaser", "db_get_by_purchaser"),
        ("top_unclaimed_amount", "db_get_top_unclaimed_amount"),
        ("top_unclaimed_quantity", "db_get_top_unclaimed_quantity"),
        ("top_claimed_amount", "db_get_top_claimed_amount"),
        ("top_claimed_quantity", "db_get_top_claimed_quantity"),
        ("claim_monthly", "db_get_claim_monthly"),
        ("claim_yearly", "db_get_claim_yearly"),
        ("claim_weekly", "db_get_claim_weekly"),
        ("structure_by_category", "db_get_structure_by_category"),
        ("category_bubble", "db_get_category_bubble"),
        ("anomaly_daily", "db_get_anomaly_daily"),
        ("age_monthly", "db_get_age_monthly"),
        ("age_heatmap", "db_get_age_heatmap"),
        ("optimize_suggest", "db_get_optimize_suggest"),
    ]

    for key, func_name in indicator_tests:
        t0 = time.time()
        try:
            func = globals().get(func_name)
            if func is None:
                results[key] = {"status": "error", "msg": f"函数 {func_name} 未找到"}
                continue
            data = func()
            elapsed = time.time() - t0
            # 返回摘要而非完整数据
            if isinstance(data, dict):
                summary = f"keys={list(data.keys())[:5]}, elapsed={elapsed:.2f}s"
            elif isinstance(data, list):
                summary = f"items={len(data)}, elapsed={elapsed:.2f}s"
            else:
                summary = f"type={type(data).__name__}, elapsed={elapsed:.2f}s"
            results[key] = {"status": "ok", "summary": summary}
        except Exception:
            elapsed = time.time() - t0
            results[key] = {
                "status": "error",
                "elapsed": f"{elapsed:.2f}s",
                "error": str(traceback.format_exc()),
            }

    # ---- compute_kpi_checklist ----
    t0 = time.time()
    try:
        kpi_data = get_kpi_checklist()
        results["kpi_checklist"] = {
            "status": "ok",
            "summary": f"summary keys={list(kpi_data['summary'].keys())}, elapsed={time.time() - t0:.2f}s",
        }
    except Exception:
        results["kpi_checklist"] = {
            "status": "error",
            "elapsed": f"{time.time() - t0:.2f}s",
            "error": str(traceback.format_exc()),
        }

    # ---- 数据库连通性 ----
    t0 = time.time()
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        results["db_connect"] = {"status": "ok", "elapsed": f"{time.time() - t0:.2f}s"}
    except Exception:
        results["db_connect"] = {
            "status": "error",
            "elapsed": f"{time.time() - t0:.2f}s",
            "error": str(traceback.format_exc()),
        }

    ok_count = sum(1 for v in results.values() if v["status"] == "ok")
    err_count = len(results) - ok_count

    return jsonify({
        "code": 0,
        "data": {
            "total": len(results),
            "ok": ok_count,
            "error": err_count,
            "results": results,
        },
    })


# ================================================================
# 生产环境：托管前端静态文件（Docker 部署时使用）
# ================================================================

STATIC_FOLDER = os.environ.get("STATIC_FOLDER", "")

if STATIC_FOLDER and os.path.isdir(STATIC_FOLDER):
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str):
        """非 /api/ 路径，返回前端静态资源或 index.html（SPA 回退）。"""
        # 先检查是否是静态资源文件
        if path and os.path.isfile(os.path.join(STATIC_FOLDER, path)):
            return send_from_directory(STATIC_FOLDER, path)
        # SPA 回退：所有非 API 路由返回 index.html
        return send_from_directory(STATIC_FOLDER, "index.html")


# ================================================================
# 启动
# ================================================================
if __name__ == "__main__":
    is_prod = bool(STATIC_FOLDER)
    print("=== BI Dashboard API Starting... ===")
    if is_prod:
        print(f"Mode: Production (static: {STATIC_FOLDER})")
    print("Address: http://0.0.0.0:5001")
    print()
    if not is_prod:
        print("Compatibility redirects active (old mock paths → WMS endpoints)")
        for old, new in _REDIRECT_MAP.items():
            print(f"   GET {old} → {new}")
        print()
    print("KingbaseES WMS API endpoints active")
    app.run(debug=not is_prod, host="0.0.0.0", port=5001, use_reloader=False)
