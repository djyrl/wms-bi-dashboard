"""
WMS 采购库存 MCP Server
=======================
将 WMS 仓库管理系统的 22 个采购库存 BI 分析指标暴露为 AI 可调用的 MCP 工具。

启动方式：
  python3.11 mcp_server.py          # stdio 模式（Claude Code 直接拉起）
  python3.11 mcp_server.py --sse    # SSE 模式（HTTP 服务，端口 8766）
  python3.11 mcp_server.py --http   # Streamable HTTP 模式（端口 8766）

依赖：
  - Python 3.11（mcp SDK 需要 Python 3.10+）
  - mcp, psycopg2-binary
"""

import argparse
import json
import os
import sys

from mcp.server.fastmcp import FastMCP

# ---- 确保 backend 目录在 sys.path 中，方便 import ----
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from summary import get_summary
from claim_indicators import get_claim_indicators
from structure_indicators import get_structure_indicators, get_structure_by_category, get_source_structure
from time_indicators import get_time_indicators, get_age_layers, get_age_monthly, get_age_heatmap
from dimension_indicators import get_by_project, get_by_purchaser, get_project_summary, get_purchaser_summary
from top_indicators import get_top_unclaimed_amount, get_top_unclaimed_quantity, get_top_claimed_amount, get_top_claimed_quantity, get_optimize_suggest
from other_indicators import get_claim_monthly, get_claim_daily, get_claim_weekly, get_category_bubble, get_anomaly_daily, get_batch_digest, get_inventory_report
from kpi_checklist import get_kpi_checklist


# ---- 初始化 MCP Server ----
mcp = FastMCP(
    name="wms-dashboard",
    instructions="WMS 采购库存智能分析 MCP Server。"
    "提供 KPI 总览、领用率、库存结构、库龄分析、项目/采购人维度、异常检测、"
    "KPI 考核清单等 22 个指标。数据来源：WMS 人大金仓 KingbaseES 数据库。",
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8766")),
)


def _to_json(data):
    """将 Python 对象转为格式化的 JSON 字符串，方便 AI 阅读。"""
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


# ================================================================
#  核心指标工具
# ================================================================


@mcp.tool(
    name="get_kpi_summary",
    description="获取 KPI 总览：入库总额、领用总额、当前库存金额、加权平均库龄、"
    "整体领用率、库龄≥1年占比、批次数量等核心汇总指标。",
)
def tool_get_summary() -> str:
    """KPI 总览"""
    return _to_json(get_summary())


@mcp.tool(
    name="get_claim_indicators",
    description="获取采购领用率指标（按当年/全部拆分）：当年采购领用率（金额/数量）、"
    "全部采购领用率（金额/数量）、当年/全部未领用采购金额、当年/全部未领用采购占比（金额）。"
    "当年指 inbound_date 所在自然年为当前年。",
)
def tool_get_claim_indicators() -> str:
    """采购领用率"""
    return _to_json(get_claim_indicators())


@mcp.tool(
    name="get_structure_indicators",
    description="获取库存结构指标：当前库存金额（全部/当年）、库存数量、"
    "项目库存占比 TOP 10、采购人库存占比 TOP 10。"
    "当年指 inbound_date 所在自然年为当前年。",
)
def tool_get_structure_indicators() -> str:
    """库存结构分析"""
    return _to_json(get_structure_indicators())


@mcp.tool(
    name="get_time_indicators",
    description="获取库龄时间指标：长库龄库存金额占比（≥1年）、"
    "库龄结构占比（≤1年 / 1~3年 / 3~5年 / ≥5年）、金额加权平均库龄（天）。",
)
def tool_get_time_indicators() -> str:
    """库龄 & 时间指标"""
    return _to_json(get_time_indicators())


# ================================================================
#  分层 & 排名工具（带参数）
# ================================================================


@mcp.tool(
    name="get_age_layers",
    description="库龄分层明细统计。按库存金额和库龄筛选具体物料。"
    "参数：min_amount 最小库存金额（元），min_age 最小库龄（天），max_age 最大库龄（天）。",
)
def tool_get_age_layers(
    min_amount: float = 0,
    min_age: int = 0,
    max_age: int = 0,
) -> str:
    """库龄分层明细

    :param min_amount: 最小库存金额（元），默认 0
    :param min_age: 最小库龄（天），默认 0
    :param max_age: 最大库龄（天），默认 0 表示不限制
    """
    real_max = max_age if max_age > 0 else None
    return _to_json(get_age_layers(min_amount=min_amount, min_age=min_age, max_age=real_max))


@mcp.tool(
    name="get_top_unclaimed_amount",
    description="未领用库存 TOP（按金额降序）。返回金额最高的 N 个库存项，附带项目和采购人信息。"
    "参数：limit 返回条数，默认 10。",
)
def tool_get_top_unclaimed_amount(limit: int = 10) -> str:
    """未领用库存 TOP（金额）"""
    return _to_json(get_top_unclaimed_amount(limit=limit))


@mcp.tool(
    name="get_top_unclaimed_quantity",
    description="未领用库存 TOP（按数量降序）。返回数量最多的 N 个库存项。"
    "参数：limit 返回条数，默认 10。",
)
def tool_get_top_unclaimed_quantity(limit: int = 10) -> str:
    """未领用库存 TOP（数量）"""
    return _to_json(get_top_unclaimed_quantity(limit=limit))


@mcp.tool(
    name="get_top_claimed_amount",
    description="领用 TOP（按领用金额降序）。返回领用最多的 N 个库存项。"
    "参数：limit 返回条数，默认 10。",
)
def tool_get_top_claimed_amount(limit: int = 10) -> str:
    """领用 TOP（金额）"""
    return _to_json(get_top_claimed_amount(limit=limit))


@mcp.tool(
    name="get_top_claimed_quantity",
    description="领用 TOP（按领用数量降序）。返回领用最多的 N 个库存项。"
    "参数：limit 返回条数，默认 10。",
)
def tool_get_top_claimed_quantity(limit: int = 10) -> str:
    """领用 TOP（数量）"""
    return _to_json(get_top_claimed_quantity(limit=limit))


# ================================================================
#  维度分析工具
# ================================================================


@mcp.tool(
    name="get_by_project",
    description="按项目维度分析：每个项目的领用率、未消耗库存金额、平均库龄。"
    "返回所有项目的详细对比数据。",
)
def tool_get_by_project() -> str:
    """项目维度分析"""
    return _to_json(get_by_project())


@mcp.tool(
    name="get_by_purchaser",
    description="按采购人维度分析：每个采购人的领用率、未消耗库存金额、平均库龄。"
    "返回所有采购人的详细对比数据。",
)
def tool_get_by_purchaser() -> str:
    """采购人维度分析"""
    return _to_json(get_by_purchaser())


# ================================================================
#  时序分析工具（Theme1）
# ================================================================


@mcp.tool(
    name="get_claim_monthly",
    description="按月统计入库金额、领用金额、领用率（最近12个月）。"
    "用于「领用率月度趋势」和「入库 vs 领用对比」图表。",
)
def tool_get_claim_monthly() -> str:
    """领用率月度趋势"""
    return _to_json(get_claim_monthly())


@mcp.tool(
    name="get_claim_daily",
    description="按天统计当月入库金额、领用金额、领用率。"
    "用于「领用率日度趋势」图表（日粒度）。",
)
def tool_get_claim_daily() -> str:
    """领用率日度趋势"""
    return _to_json(get_claim_daily())


@mcp.tool(
    name="get_claim_weekly",
    description="按周统计入库金额、领用金额、领用率（最近12周）。"
    "用于「领用率周度趋势」图表（周粒度）。",
)
def tool_get_claim_weekly() -> str:
    """领用率周度趋势"""
    return _to_json(get_claim_weekly())


# ================================================================
#  结构 & 气泡分析工具（Theme2）
# ================================================================


@mcp.tool(
    name="get_structure_by_category",
    description="按物料编码统计库存金额，含安全库存上限和下限。"
    "用于「在库水位 · 安全库存偏离度」分析。",
)
def tool_get_structure_by_category() -> str:
    """物料安全库存偏离度"""
    return _to_json(get_structure_by_category())


@mcp.tool(
    name="get_category_bubble",
    description="按物资类别统计库存金额、领用率、SKU 数。"
    "用于「库存金额与领用率气泡图」分析。",
)
def tool_get_category_bubble() -> str:
    """类别气泡图数据"""
    return _to_json(get_category_bubble())


# ================================================================
#  批次 & 异常检测工具
# ================================================================


@mcp.tool(
    name="get_batch_digest",
    description="批次消化进度：按入库月份统计入库金额、剩余金额、消耗金额。"
    "用于追踪不同批次物料的消化情况。",
)
def tool_get_batch_digest() -> str:
    """批次消化进度"""
    return _to_json(get_batch_digest())


@mcp.tool(
    name="get_anomaly_daily",
    description="近 N 天逐日入库/领用异常检测（2σ 法）。检测维度包括："
    "新项目首次入库、周度环比波动超 ±30%、周度同比波动超 ±30%。"
    "参数：days 检测天数，默认 30。",
)
def tool_get_anomaly_daily(days: int = 30) -> str:
    """库存异常变动预警

    :param days: 检测天数范围，默认 30
    """
    return _to_json(get_anomaly_daily(days=days))


# ================================================================
#  库龄高级分析工具
# ================================================================


@mcp.tool(
    name="get_age_monthly",
    description="按月计算加权平均库龄和超 90 天库存占比（最近12个月）。"
    "用于「平均库龄月度趋势」分析。",
)
def tool_get_age_monthly() -> str:
    """平均库龄月度趋势"""
    return _to_json(get_age_monthly())


@mcp.tool(
    name="get_age_heatmap",
    description="按物料类别 × 库龄段交叉统计库存金额（TOP 10 类别 × 6 库龄段）。"
    "用于「滞留库存热力图」分析，快速定位高库龄的品类集中区。",
)
def tool_get_age_heatmap() -> str:
    """滞留库存热力图"""
    return _to_json(get_age_heatmap())


# ================================================================
#  优化建议工具
# ================================================================


@mcp.tool(
    name="get_optimize_suggest",
    description="智能备货优化建议：基于日均消耗计算推荐安全库存上限。"
    "参数：limit 返回建议条数（默认 8），safety_days 安全库存天数（默认 60）。",
)
def tool_get_optimize_suggest(limit: int = 8, safety_days: int = 60) -> str:
    """智能备货优化建议

    :param limit: 返回建议条数，默认 8
    :param safety_days: 安全库存天数，默认 60 天
    """
    return _to_json(get_optimize_suggest(limit=limit, safety_days=safety_days))


# ================================================================
#  KPI 考核清单
# ================================================================


@mcp.tool(
    name="get_kpi_checklist",
    description="获取 KPI 考核清单（完整版）。包含四类指标："
    "第一类 核心考核指标 K1-K3（库存总额、领用率、加权平均库龄），"
    "第二类 约束类指标 K4-K5（安全库存达标率、超上限物料数），"
    "第三类 结构分析指标 K6-K9（集中度、偏离度、新项目库存、退库异常率），"
    "第四类 TOP 指标 T1-T2（未领用 TOP 10 金额/数量，不纳入考核）。"
    "每个指标附带：实际值、目标值、达成状态、趋势、详细信息。",
)
def tool_get_kpi_checklist() -> str:
    """KPI 考核清单"""
    return _to_json(get_kpi_checklist())


# ================================================================
#  采购批次库存报表
# ================================================================


@mcp.tool(
    name="get_inventory_report",
    description="采购批次库存报表。按批次维度展示每批物料的入库金额、领用金额、库存金额、"
    "领用率、库龄，支持排序和分页。"
    "参数：sort_by 排序字段（claim_rate / age_days / inventory_amount，默认 inventory_amount），"
    "sort_order 排序方向（asc / desc，默认 desc），"
    "limit 返回条数（默认 500），offset 偏移量（默认 0）。",
)
def tool_get_inventory_report(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
    limit: int = 500,
    offset: int = 0,
) -> str:
    """采购批次库存报表

    :param sort_by: 排序字段 — claim_rate(领用率) / age_days(库龄) / inventory_amount(库存金额)
    :param sort_order: 排序方向 — asc / desc
    :param limit: 每页条数
    :param offset: 偏移量
    """
    return _to_json(get_inventory_report(sort_by, sort_order, limit, offset))


# ================================================================
#  项目库存追溯汇总
# ================================================================


@mcp.tool(
    name="get_project_summary",
    description="项目库存追溯汇总表。按项目维度汇总：入库金额、领用金额、库存金额、"
    "领用率、加权平均库龄。支持排序。"
    "参数：sort_by 排序字段（inventory_amount / claim_rate / avg_age_days，默认 inventory_amount），"
    "sort_order 排序方向（asc / desc，默认 desc）。",
)
def tool_get_project_summary(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
) -> str:
    """项目库存追溯汇总表

    :param sort_by: 排序字段 — inventory_amount(库存金额) / claim_rate(领用率) / avg_age_days(平均库龄)
    :param sort_order: 排序方向 — asc / desc
    """
    return _to_json(get_project_summary(sort_by, sort_order))


# ================================================================
#  采购人库存追溯汇总
# ================================================================


@mcp.tool(
    name="get_purchaser_summary",
    description="采购人库存追溯汇总表。按采购人维度汇总：入库金额、领用金额、库存金额、"
    "领用率、加权平均库龄。",
)
def tool_get_purchaser_summary(
    sort_by: str = "inventory_amount",
    sort_order: str = "desc",
) -> str:
    """采购人库存追溯汇总表

    :param sort_by: 排序字段 — inventory_amount / claim_rate / avg_age_days
    :param sort_order: 排序方向 — asc / desc
    """
    return _to_json(get_purchaser_summary(sort_by, sort_order))


# ================================================================
#  库存来源结构
# ================================================================


@mcp.tool(
    name="get_source_structure",
    description="库存来源结构表。按项目维度统计库存金额及占比，"
    "用于分析库存的来源构成。",
)
def tool_get_source_structure() -> str:
    """库存来源结构表"""
    return _to_json(get_source_structure())


# ================================================================
#  启动入口
# ================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WMS MCP Server — 采购库存智能分析",
    )
    parser.add_argument(
        "--sse",
        action="store_true",
        help="使用 SSE（Server-Sent Events）模式启动 HTTP 服务（端口 8766）",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="使用 Streamable HTTP 模式启动（端口 8766）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="SSE/HTTP 模式下的监听端口（默认 8766）",
    )
    args = parser.parse_args()

    # 传输模式优先级：命令行 > 环境变量 MCP_TRANSPORT > 默认 stdio
    transport = os.getenv("MCP_TRANSPORT", "")
    port = args.port or int(os.getenv("MCP_PORT", "8766"))

    if args.sse or transport == "sse":
        label = "SSE"
        mode = "sse"
    elif args.http or transport == "streamable-http":
        label = "Streamable HTTP"
        mode = "streamable-http"
    else:
        # stdio 模式（本地开发，Claude Code 直接拉起）
        mcp.run()
        sys.exit(0)

    print(f"=== WMS MCP Server ({label}) === {mcp.settings.host}:{mcp.settings.port}")
    mcp.run(transport=mode)
