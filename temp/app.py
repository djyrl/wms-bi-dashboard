"""
采购库存 BI Dashboard — Flask 后端
提供 14 个 RESTful API 端点，覆盖 6 大类 22 个指标。
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
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

app = Flask(__name__)
CORS(app)


def ok(data):
    return jsonify({"code": 0, "data": data})


# ================================================================
# Overview
# ================================================================
@app.route("/api/summary", methods=["GET"])
def api_summary():
    """GET /api/summary — KPI 总览"""
    return ok(get_summary())


# ================================================================
# I. 库存领用指标
# ================================================================
@app.route("/api/indicators/claim", methods=["GET"])
def api_claim():
    """GET /api/indicators/claim — 采购领用率、未领用金额等"""
    return ok(get_claim_indicators())


# ================================================================
# II. 库存结构指标
# ================================================================
@app.route("/api/indicators/structure", methods=["GET"])
def api_structure():
    """GET /api/indicators/structure — 库存金额、项目/采购人占比"""
    return ok(get_structure_indicators())


# ================================================================
# III. 库存时间指标
# ================================================================
@app.route("/api/indicators/time", methods=["GET"])
def api_time():
    """GET /api/indicators/time — 库龄结构、加权平均库龄"""
    return ok(get_time_indicators())


@app.route("/api/indicators/age-layers", methods=["GET"])
def api_age_layers():
    """GET /api/indicators/age-layers?min_amount=100000&min_age=365 — 库龄分层统计"""
    min_amount = request.args.get("min_amount", 0, type=float)
    min_age = request.args.get("min_age", 0, type=int)
    max_age = request.args.get("max_age", None, type=int)
    return ok(get_age_layers(min_amount=min_amount, min_age=min_age, max_age=max_age))


# ================================================================
# IV. 项目维度指标
# ================================================================
@app.route("/api/indicators/by-project", methods=["GET"])
def api_by_project():
    """GET /api/indicators/by-project — 各项目领用率、未消耗金额、平均库龄"""
    return ok(get_by_project())


# ================================================================
# V. 采购人维度指标
# ================================================================
@app.route("/api/indicators/by-purchaser", methods=["GET"])
def api_by_purchaser():
    """GET /api/indicators/by-purchaser — 各采购人领用率、未消耗金额、平均库龄"""
    return ok(get_by_purchaser())


# ================================================================
# VI. TOP 排行
# ================================================================
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


# ================================================================
# 维度 & 下钻
# ================================================================
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
# 启动
# ================================================================
if __name__ == "__main__":
    print("=== BI Dashboard API (Mock Data) Starting... ===")
    print("Address: http://127.0.0.1:5001")
    print("Data: Mock / Simulated Data")
    print("API Endpoints:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.rule.startswith("/api"):
            print(f"   GET {rule.rule}")
    app.run(debug=True, port=5001)
