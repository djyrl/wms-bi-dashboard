"""
采购库存 BI Dashboard — Flask 后端
===================================
数据源：
  - 模拟数据：14 个指标分析接口
  - 人大金仓（KingbaseES）：4 张 WMS 核心表查询接口
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras

from data.generate_data import (
    get_summary,
    get_claim_indicators,
    get_structure_indicators,
    get_time_indicators,
    get_age_layers,
    get_by_project,
    get_by_purchaser,
    get_top_unclaimed_amount,
    get_top_unclaimed_quantity,
    get_top_claimed_amount,
    get_top_claimed_quantity,
    get_dimensions,
    drill_batches,
)

# 人大金仓真实数据计算模块
from compute_kpi_checklist import get_kpi_checklist
from compute_indicators import (
    get_summary as db_get_summary,
    get_claim_indicators as db_get_claim_indicators,
    get_structure_indicators as db_get_structure_indicators,
    get_time_indicators as db_get_time_indicators,
    get_age_layers as db_get_age_layers,
    get_by_project as db_get_by_project,
    get_by_purchaser as db_get_by_purchaser,
    get_top_unclaimed_amount as db_get_top_unclaimed_amount,
    get_top_unclaimed_quantity as db_get_top_unclaimed_quantity,
    get_top_claimed_amount as db_get_top_claimed_amount,
    get_top_claimed_quantity as db_get_top_claimed_quantity,
    get_claim_monthly as db_get_claim_monthly,
    get_claim_daily as db_get_claim_daily,
    get_claim_weekly as db_get_claim_weekly,
    get_structure_by_category as db_get_structure_by_category,
    get_category_bubble as db_get_category_bubble,
    get_anomaly_daily as db_get_anomaly_daily,
    get_batch_digest as db_get_batch_digest,
    get_age_monthly as db_get_age_monthly,
    get_age_heatmap as db_get_age_heatmap,
    get_optimize_suggest as db_get_optimize_suggest,
)

app = Flask(__name__)
CORS(app)

# ================================================================
# 人大金仓（KingbaseES）数据库连接配置
# ================================================================
DB_CONFIG = {
    "host": "122.51.39.235",
    "port": 54321,
    "dbname": "garden_wms",
    "user": "kingbase",
    "password": "123456",
}


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
#  模拟数据接口 — 采购库存 BI 指标分析
# ================================================================

@app.route("/api/summary", methods=["GET"])
def api_summary():
    """GET /api/summary — KPI 总览"""
    return ok(get_summary())


@app.route("/api/indicators/claim", methods=["GET"])
def api_claim():
    """GET /api/indicators/claim — 采购领用率、未领用金额等"""
    return ok(get_claim_indicators())


@app.route("/api/indicators/structure", methods=["GET"])
def api_structure():
    """GET /api/indicators/structure — 库存金额、项目/采购人占比"""
    return ok(get_structure_indicators())


@app.route("/api/indicators/time", methods=["GET"])
def api_time():
    """GET /api/indicators/time — 库龄结构、加权平均库龄"""
    return ok(get_time_indicators())


@app.route("/api/indicators/age-layers", methods=["GET"])
def api_age_layers():
    """GET /api/indicators/age-layers?min_amount=&min_age=&max_age= — 库龄分层统计"""
    min_amount = request.args.get("min_amount", 0, type=float)
    min_age = request.args.get("min_age", 0, type=int)
    max_age = request.args.get("max_age", None, type=int)
    return ok(get_age_layers(min_amount=min_amount, min_age=min_age, max_age=max_age))


@app.route("/api/indicators/by-project", methods=["GET"])
def api_by_project():
    """GET /api/indicators/by-project — 各项目领用率、未消耗金额、平均库龄"""
    return ok(get_by_project())


@app.route("/api/indicators/by-purchaser", methods=["GET"])
def api_by_purchaser():
    """GET /api/indicators/by-purchaser — 各采购人领用率、未消耗金额、平均库龄"""
    return ok(get_by_purchaser())


@app.route("/api/top/unclaimed-amount", methods=["GET"])
def api_top_unclaimed_amount():
    """GET /api/top/unclaimed-amount?limit=10 — 未领用库存 TOP（金额）"""
    limit = request.args.get("limit", 10, type=int)
    return ok(get_top_unclaimed_amount(limit))


@app.route("/api/top/unclaimed-quantity", methods=["GET"])
def api_top_unclaimed_quantity():
    """GET /api/top/unclaimed-quantity?limit=10 — 未领用库存 TOP（数量）"""
    limit = request.args.get("limit", 10, type=int)
    return ok(get_top_unclaimed_quantity(limit))


@app.route("/api/top/claimed-amount", methods=["GET"])
def api_top_claimed_amount():
    """GET /api/top/claimed-amount?limit=10 — 领用 TOP（金额）"""
    limit = request.args.get("limit", 10, type=int)
    return ok(get_top_claimed_amount(limit))


@app.route("/api/top/claimed-quantity", methods=["GET"])
def api_top_claimed_quantity():
    """GET /api/top/claimed-quantity?limit=10 — 领用 TOP（数量）"""
    limit = request.args.get("limit", 10, type=int)
    return ok(get_top_claimed_quantity(limit))


@app.route("/api/dimensions/<dim_type>", methods=["GET"])
def api_dimensions(dim_type: str):
    """GET /api/dimensions/materials|projects|purchasers"""
    return ok(get_dimensions(dim_type))


@app.route("/api/drill/batches", methods=["GET"])
def api_drill():
    """GET /api/drill/batches?project_id=&material_id=&purchaser_id=&age_min=&age_max="""
    return ok(drill_batches(
        project_id=request.args.get("project_id", None, type=int),
        material_id=request.args.get("material_id", None, type=int),
        purchaser_id=request.args.get("purchaser_id", None, type=int),
        age_min=request.args.get("age_min", None, type=int),
        age_max=request.args.get("age_max", None, type=int),
    ))


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
    1. 采购领用率（金额） = 领用金额 / 入库金额
    2. 采购领用率（数量） = 领用数量 / 入库数量
    3. 未领用采购金额 = 入库金额 - 净领用金额
    4. 未领用采购占比 = 未领用金额 / 入库金额
    """
    try:
        return ok(db_get_claim_indicators())
    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)})


@app.route("/api/wms/indicators/structure", methods=["GET"])
def api_wms_structure():
    """
    5. 当前库存金额
    6. 当前库存数量
    7. 项目库存占比
    8. 采购人库存占比
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
# 启动
# ================================================================
if __name__ == "__main__":
    print("=== BI Dashboard API Starting... ===")
    print("Address: http://127.0.0.1:5001")
    print()
    print("Mock Data API (13 endpoints):")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.rule.startswith("/api/") and "/wms/" not in rule.rule:
            print(f"   GET {rule.rule}")
    print()
    print("KingbaseES WMS API (5 endpoints):")
    print("   Database: KingbaseES @ 122.51.39.235:54321/garden_wms")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if "/wms/" in rule.rule:
            print(f"   GET {rule.rule}")
    app.run(debug=True, port=5001)
