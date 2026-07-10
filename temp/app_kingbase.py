"""
WMS 数据查询 API — Flask 后端
连接人大金仓（KingbaseES）数据库 garden_wms，提供 4 张核心表的查询接口。
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras

app = Flask(__name__)
CORS(app)

# ================================================================
# 人大金仓（KingbaseES）数据库连接配置
# KingbaseES 兼容 PostgreSQL 协议，使用 psycopg2 驱动
# ================================================================
DB_CONFIG = {
    "host": "122.51.39.235",
    "port": 54321,
    "dbname": "garden_wms",
    "user": "kingbase",
    "password": "123456",
}


def get_db():
    """获取数据库连接，设置 autocommit 避免长事务。"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def query_table(table_name: str):
    """
    通用查询方法：查询指定表全部数据。
    支持 ?limit=&offset= 分页参数。
    """
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        sql = f"SELECT * FROM {table_name} ORDER BY 1"
        params = []

        # 分页
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


# ================================================================
# 1. 库存表 — wms_inventory
# ================================================================
@app.route("/api/wms_inventory", methods=["GET"])
def api_wms_inventory():
    """
    GET /api/wms_inventory?limit=&offset=
    查询 wms_inventory 表全部数据。
    """
    result = query_table("wms_inventory")
    return jsonify(result)


# ================================================================
# 2. 项目库存表 — wms_project_inventory
# ================================================================
@app.route("/api/wms_project_inventory", methods=["GET"])
def api_wms_project_inventory():
    """
    GET /api/wms_project_inventory?limit=&offset=
    查询 wms_project_inventory 表全部数据。
    """
    result = query_table("wms_project_inventory")
    return jsonify(result)


# ================================================================
# 3. 物料表 — wms_material
# ================================================================
@app.route("/api/wms_material", methods=["GET"])
def api_wms_material():
    """
    GET /api/wms_material?limit=&offset=
    查询 wms_material 表全部数据。
    """
    result = query_table("wms_material")
    return jsonify(result)


# ================================================================
# 4. 入库单表 — wms_inbound_order
# ================================================================
@app.route("/api/wms_inbound_order", methods=["GET"])
def api_wms_inbound_order():
    """
    GET /api/wms_inbound_order?limit=&offset=
    查询 wms_inbound_order 表全部数据。
    """
    result = query_table("wms_inbound_order")
    return jsonify(result)


# ================================================================
# 健康检查
# ================================================================
@app.route("/api/health", methods=["GET"])
def api_health():
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
# 启动
# ================================================================
if __name__ == "__main__":
    print("=== WMS Data API (KingbaseES) Starting... ===")
    print("Address: http://127.0.0.1:5002")
    print("Database: KingbaseES @ 122.51.39.235:54321/garden_wms")
    print("API Endpoints:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.rule.startswith("/api"):
            print(f"   GET {rule.rule}")
    app.run(debug=True, port=5002)
