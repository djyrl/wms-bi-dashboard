"""
ERP ZMMRP226 Data Import Program
=================================
从 erp_catalog_zmmrp226 读取数据，按指定字段映射解析 row_json(JSONB)，
导入到 wbs_zmmrp226_parsed。

设计：表存在则 TRUNCATE（保留依赖视图），不存在则 CREATE。
"""

import sys
import json
import psycopg2
import psycopg2.extras

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

from db_config import DB_CONFIG

TARGET_TABLE = "wbs_zmmrp226_parsed"
BATCH_SIZE = 500

# ============================================================
# 字段映射：[(字段名, SQL类型, 中文注释)]
# ============================================================

FIELD_MAPPING = [
    ("zxmh",           "VARCHAR(50)",   "项目号"),
    ("matnr",          "VARCHAR(50)",   "物料编号"),
    ("maktx",          "VARCHAR(255)",  "物料描述"),
    ("werks",          "VARCHAR(50)",   "工厂"),
    ("z_date",         "VARCHAR(50)",   "提报时间"),
    ("requdate",       "VARCHAR(50)",   "需求日期"),
    ("ramount",        "VARCHAR(50)",   "当前需求数量"),
    ("z_spztms",       "VARCHAR(50)",   "当前审批状态"),
    ("z_name",         "VARCHAR(50)",   "提报人"),
    ("contact",        "VARCHAR(50)",   "联系人"),
    ("zcat",           "VARCHAR(50)",   "计划类型"),
    ("z_dxxmh",        "VARCHAR(50)",   "WBS项目编号"),
    ("zindex",         "VARCHAR(50)",   "计数"),
    ("mstae",          "VARCHAR(50)",   "物料冻结状态"),
    ("mtstb",          "VARCHAR(255)",  "物料冻结状态描述"),
    ("znetpr",         "VARCHAR(50)",   "单价"),
    ("zyssl",          "VARCHAR(50)",   "原需求数量"),
    ("zjjsprq",        "VARCHAR(50)",   "拒绝审批日期"),
    ("zsnetpr",        "VARCHAR(50)",   "可用金额"),
    ("matkl",          "VARCHAR(50)",   "物料组"),
    ("wgbez",          "VARCHAR(50)",   "物料组描述"),
    ("kmlb",           "VARCHAR(50)",   "科目类别"),
    ("kmname",         "VARCHAR(255)",  "科目类别描述"),
    ("z_jhlb_nm",      "VARCHAR(255)",  "计划类别"),
    ("reqptmt_name",   "VARCHAR(255)",  "部门"),
    ("ekgrp",          "VARCHAR(50)",   "采购组"),
    ("eknam",          "VARCHAR(255)",  "采购组描述"),
    ("z_dqjb",         "VARCHAR(50)",   "审批层级"),
    ("zapprove",       "VARCHAR(50)",   "审批状态标识"),
    ("zzzsprq",        "VARCHAR(50)",   "最终审批日期"),
    ("fipex",          "VARCHAR(50)",   "预算类别"),
    ("zsnetpr_kp",     "VARCHAR(50)",   "行项目金额"),
    ("zsum_upd",       "VARCHAR(50)",   "本单占用金额"),
    ("z_qcys",         "VARCHAR(50)",   "期初预算金额"),
    ("zljys_yet",      "VARCHAR(50)",   "累计预算金额"),
    ("zsyys_last",     "VARCHAR(50)",   "剩余预算金额"),
    ("zuname",         "VARCHAR(50)",   "用户名"),
    ("zudate",         "VARCHAR(50)",   "更改日期"),
    ("zutime",         "VARCHAR(50)",   "更改时间"),
    ("msehl",          "VARCHAR(50)",   "单位"),
    ("zrnetpr",        "VARCHAR(50)",   "参考单价"),
    ("sum_pbdnr",      "VARCHAR(50)",   "独立需求"),
    ("z_cgjhh",        "VARCHAR(50)",   "采购申请"),
    ("z_cgjh_hh",      "VARCHAR(50)",   "采购申请行号"),
    ("berid",          "VARCHAR(50)",   "MRP范围"),
    ("bertx",          "VARCHAR(50)",   "MRP范围文本"),
    ("tel",            "VARCHAR(50)",   "联系电话"),
    ("z_sdlk",         "VARCHAR(50)",   "利库库存数"),
    ("labor",          "VARCHAR(50)",   "采购策略"),
    ("lbtxt",          "VARCHAR(255)",  "采购策略描述"),
    ("plancat2",       "VARCHAR(50)",   "计划对象"),
    ("plancat_txt2",   "VARCHAR(255)",  "计划对象描述"),
    ("zjhjsrq",        "VARCHAR(50)",   "计划结束日期"),
    ("zjhgbsj",        "VARCHAR(50)",   "计划关闭(或删除)日"),
    ("zbdzei",         "VARCHAR(50)",   "需求计划指针"),
    ("consg",          "VARCHAR(50)",   "寄售标识"),
    ("zclose",         "VARCHAR(50)",   "关闭标识"),
    ("faildt",         "VARCHAR(50)",   "失效日期"),
    ("zgscgcl",        "VARCHAR(50)",   "采购方式"),
    ("frgrp",          "VARCHAR(50)",   "审批组"),
    ("z_pbdnr_ms",     "VARCHAR(255)",  "需求计划描述"),
    ("z_sjjh",         "VARCHAR(50)",   "件号"),
    ("zstk_cls",       "VARCHAR(50)",   "库存分类"),
    ("aptxt",          "VARCHAR(255)",  "库存分类描述"),
    ("zzxmbh",         "VARCHAR(255)",  "项目编号"),
    ("ktext",          "VARCHAR(255)",  "项目描述"),
    ("zhxmje",         "VARCHAR(50)",   "需求计划汇总金额"),
    ("z_memo_yj",      "VARCHAR(255)",  "审批意见"),
    ("z_memo",         "VARCHAR(255)",  "备注"),
    ("z_sbh",          "VARCHAR(50)",   "设备号"),
    ("z_jcch",         "VARCHAR(50)",   "机车车号"),
    ("anln1",          "VARCHAR(50)",   "资产号"),
    ("plnum",          "VARCHAR(50)",   "计划订单号"),
    ("zaptxt",         "VARCHAR(255)",  "备件分类"),
    ("z_pbdnr_pzrq",   "VARCHAR(50)",   "批准日期"),
    ("zamtyp",         "VARCHAR(50)",   "备件机型编码"),
    ("amtxt",          "VARCHAR(255)",  "备件机型描述"),
    ("zmatyp",         "VARCHAR(50)",   "主机型号编码"),
    ("mttxt",          "VARCHAR(255)",  "主机型号描述"),
    ("zgc_billcode",   "VARCHAR(50)",   "公务车采购申请单号"),
    ("zgc_item",       "VARCHAR(50)",   "公务车行项目编号"),
    ("zgc_cpxh",       "VARCHAR(50)",   "公务车厂牌型号"),
    ("zgc_pl",         "VARCHAR(50)",   "公务车排量"),
    ("zgc_cllbname",   "VARCHAR(50)",   "车辆类别"),
    ("zgc_clytname",   "VARCHAR(50)",   "车辆用途"),
    ("zgc_yjjg",       "VARCHAR(50)",   "公务车预计价格"),
    ("zgc_creater",    "VARCHAR(50)",   "公务车制单人"),
    ("zdsdhh",         "VARCHAR(50)",   "电商订货号"),
    ("zzjyxyfsbh",     "VARCHAR(50)",   "建议寻源方式"),
    ("zzxyfsddtxt",    "VARCHAR(255)",  "建议寻源方式描述"),
    ("dispo",          "VARCHAR(50)",   "MRP控制者"),
    ("dsnam",          "VARCHAR(50)",   "控制者名称"),
    ("zzfbbh",         "VARCHAR(50)",   "分包编号"),
    ("zzfbms",         "VARCHAR(255)",  "分包描述"),
    ("maktx_long",     "VARCHAR(500)",  "物料长描述"),
    ("zfjwdbz",        "VARCHAR(50)",   "附件文档挂接标识"),
    ("zjhlbtxt",       "VARCHAR(255)",  "时间计划类别"),
    ("zreqyy",         "VARCHAR(255)",  "申请原因"),
    ("zxqlx",          "VARCHAR(50)",   "需求类型"),
    ("zzjwz",          "VARCHAR(50)",   "装机位置"),
    ("zzjl",           "VARCHAR(50)",   "装机量"),
    ("zyscgl",         "VARCHAR(50)",   "原始采购数量"),
    ("zysdbl",         "VARCHAR(50)",   "原始调拨数量"),
    ("zbhcs",          "VARCHAR(50)",   "驳回次数"),
    ("post1",          "VARCHAR(255)",  "WBS项目描述"),
    ("zjhfl",          "VARCHAR(50)",   "计划分类"),
    ("zsfgc",          "VARCHAR(50)",   "是否工程"),
    ("jswj_id",        "VARCHAR(50)",   "技术文件ID"),
    ("lgort",          "VARCHAR(50)",   "库存地点"),
    ("z_fh",           "VARCHAR(50)",   "返回标识"),
    ("z_fhyy",         "VARCHAR(255)",  "返回原因"),
    ("zdxsykc",        "VARCHAR(50)",   "大修剩余库存数量"),
    ("zlksl",          "VARCHAR(50)",   "利库数量"),
    ("zlkhxq",         "VARCHAR(50)",   "利库后需求数量"),
    ("zlkyy",          "VARCHAR(255)",  "利库原因"),
    ("zlkr",           "VARCHAR(50)",   "利库人"),
    ("zlkrq",          "VARCHAR(50)",   "利库日期"),
    ("zlksj",          "VARCHAR(50)",   "利库时间"),
    ("zthjkc",         "VARCHAR(50)",   "替换件库存"),
    ("flag",           "VARCHAR(50)",   "标识字段"),
    ("sobkz01",        "VARCHAR(50)",   "是否寄售"),
    ("posid",          "VARCHAR(50)",   "WBS元素"),
    ("zlcgb",          "VARCHAR(50)",   "联储共备类型"),
    ("zmmywzgbm",      "VARCHAR(50)",   "业务主管部门"),
    ("zmmywzgbmd",     "VARCHAR(255)",  "业务主管部门名称"),
    ("zljzgckc",       "VARCHAR(50)",   "零价值工厂库存"),
    ("zjhlb2",         "VARCHAR(50)",   "检修技改类型"),
    ("zjz",            "VARCHAR(50)",   "机组"),
    ("zsyccgjj",       "VARCHAR(50)",   "上一次采购净价"),
    ("zsycchsj",       "VARCHAR(50)",   "上一次采购含税价"),
    ("knttp",          "VARCHAR(50)",   "科目分配类别"),
    ("zknttx",         "VARCHAR(255)",  "科目分配类别描述"),
    ("zsaknr",         "VARCHAR(50)",   "科目编号"),
    ("zkostl",         "VARCHAR(50)",   "成本中心"),
    ("zltext",         "VARCHAR(255)",  "成本中心描述"),
    ("rzj",            "VARCHAR(50)",   "总价"),
    ("zfzhsjz",        "VARCHAR(50)",   "辅助核算机组"),
    ("zfwqxms",        "VARCHAR(255)",  "服务需求描述"),
    ("zdsbs",          "VARCHAR(50)",   "电商标识物料"),
    ("zob",            "VARCHAR(255)",  "推荐品牌"),
    ("zbzcc",          "VARCHAR(255)",  "原生产厂家"),
    ("zjhyj",          "VARCHAR(255)",  "计划依据"),
    ("zgsxmt",         "VARCHAR(50)",   "是否煤电公司项目"),
    ("zcgfw",          "VARCHAR(50)",   "采购范围"),
    ("zqztbr",         "VARCHAR(255)",  "潜在投标人及联系方式"),
    ("zgdzct",         "VARCHAR(50)",   "是否固定资产"),
    ("ndjh_bh",        "VARCHAR(50)",   "年度采购计划编号"),
    ("znumber",        "VARCHAR(50)",   "年度计划行号"),
    ("zsaknr_item",    "VARCHAR(50)",   "行项目总账科目"),
    ("z_syfx",         "VARCHAR(50)",   "使用方向"),
    ("z_syfxms",       "VARCHAR(255)",  "使用方向描述"),
    ("z_yslb",         "VARCHAR(50)",   "预算类别"),
    ("z_yslbms",       "VARCHAR(255)",  "预算类别描述"),
    ("z_dwbk",         "VARCHAR(50)",   "单位板块"),
    ("zmemo_url",      "VARCHAR(500)",  "URL备注"),
]


# ============================================================
# Step 1: 生成建表语句
# ============================================================

def generate_create_table_sql() -> str:
    lines = []
    lines.append("-- ============================================================")
    lines.append("-- ERP ZMMRP226 需求计划明细表")
    lines.append("-- 基于 erp_catalog_zmmrp226.row_json 解析")
    lines.append("-- ============================================================")
    lines.append("CREATE TABLE IF NOT EXISTS {} (".format(TARGET_TABLE))
    lines.append("    -- 源表原始字段")
    lines.append("    id              VARCHAR(128)  NOT NULL,")
    lines.append("    tenant_id       VARCHAR(128),")
    lines.append("    pbdnr           VARCHAR(255),")
    lines.append("    create_date     TIMESTAMP,")
    lines.append("    update_date     TIMESTAMP,")
    lines.append("")
    lines.append("    -- row_json 解析字段")

    for i, (name, sql_type, comment) in enumerate(FIELD_MAPPING):
        is_last = (i == len(FIELD_MAPPING) - 1)
        if is_last:
            lines.append("    {:<16s} {:<15s},  -- {}".format(name, sql_type, comment))
        else:
            lines.append("    {:<16s} {:<15s},  -- {}".format(name, sql_type, comment))

    lines.append("")
    lines.append("    PRIMARY KEY (id)")
    lines.append(");")

    lines.append("")
    lines.append("COMMENT ON TABLE {} IS 'ERP ZMMRP226 需求计划明细表';".format(TARGET_TABLE))
    lines.append("COMMENT ON COLUMN {}.pbdnr IS '需求计划号';".format(TARGET_TABLE))
    for name, sql_type, comment in FIELD_MAPPING:
        lines.append("COMMENT ON COLUMN {}.{} IS '{}';".format(TARGET_TABLE, name, comment))

    return "\n".join(lines)


# ============================================================
# Step 2: 创建或清空目标表
# ============================================================

def create_target_table(create_sql: str):
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    conn.autocommit = True
    cur = conn.cursor()

    # 检查表是否存在：存在则 TRUNCATE（保留依赖视图），不存在则 CREATE
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s
        )
    """, (TARGET_TABLE,))
    table_exists = cur.fetchone()[0]

    if table_exists:
        cur.execute("TRUNCATE TABLE {}".format(TARGET_TABLE))
        print("Truncated table: {} (views preserved)".format(TARGET_TABLE))
    else:
        statements = [s.strip() for s in create_sql.split(";") if s.strip()]
        for stmt in statements:
            cur.execute(stmt)
        print("Created table: {}".format(TARGET_TABLE))

    cur.close()
    conn.close()


# ============================================================
# Step 3: 导入数据
# ============================================================

def import_data():
    src_conn = psycopg2.connect(**DB_CONFIG)
    src_conn.set_client_encoding("UTF8")

    dst_conn = psycopg2.connect(**DB_CONFIG)
    dst_conn.set_client_encoding("UTF8")
    dst_conn.autocommit = False

    src_cur = src_conn.cursor("erp_zmmrp226_cursor")
    src_cur.itersize = BATCH_SIZE
    dst_cur = dst_conn.cursor()

    source_columns = ["id", "tenant_id", "pbdnr", "create_date", "update_date"]
    json_columns_lower = [name for name, _, _ in FIELD_MAPPING]
    json_keys_upper = [name.upper() for name in json_columns_lower]
    all_columns = source_columns + json_columns_lower
    insert_sql = "INSERT INTO {} ({}) VALUES %s".format(
        TARGET_TABLE, ", ".join(all_columns)
    )

    src_cur.execute(
        "SELECT id, tenant_id, pbdnr, create_date, update_date, row_json "
        "FROM erp_catalog_zmmrp226"
    )

    total = 0
    batch = []
    for row in src_cur:
        row_id, tenant_id, pbdnr, create_date, update_date, row_json = row
        source_vals = [row_id, tenant_id, pbdnr, create_date, update_date]

        if isinstance(row_json, dict):
            json_vals = []
            for key in json_keys_upper:
                v = row_json.get(key)
                if isinstance(v, dict):
                    v = json.dumps(v, ensure_ascii=False)
                json_vals.append(v)
        else:
            json_vals = [None] * len(json_columns_lower)

        batch.append(tuple(source_vals) + tuple(json_vals))

        if len(batch) >= BATCH_SIZE:
            psycopg2.extras.execute_values(dst_cur, insert_sql, batch)
            dst_conn.commit()
            total += len(batch)
            print("Imported {:,} rows...".format(total))
            batch = []

    if batch:
        psycopg2.extras.execute_values(dst_cur, insert_sql, batch)
        dst_conn.commit()
        total += len(batch)

    src_cur.close()
    dst_cur.close()
    src_conn.close()
    dst_conn.close()

    print("\nImport complete! {} rows -> {}".format(total, TARGET_TABLE))


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("ERP ZMMRP226 Import Program")
    print("=" * 60)
    db_info = "{host}:{port}/{dbname}".format(**DB_CONFIG)
    print("Database: {}".format(db_info))
    print("Source table: erp_catalog_zmmrp226")
    print("Target table: {}".format(TARGET_TABLE))
    print("Fields: {}".format(len(FIELD_MAPPING)))
    print("=" * 60)

    # Step 1: Generate CREATE TABLE SQL
    print("\n[Step 1] Generating CREATE TABLE SQL...")
    create_sql = generate_create_table_sql()

    # Write SQL to file for review
    with open("sql/create_wbs_zmmrp226.sql", "w", encoding="utf-8") as f:
        f.write(create_sql)
    print("SQL written to sql/create_wbs_zmmrp226.sql")

    # Step 2: Create or truncate table
    print("\n[Step 2] Preparing target table...")
    create_target_table(create_sql)

    # Step 3: Import data
    print("\n[Step 3] Importing data from erp_catalog_zmmrp226...")
    import_data()

    print("\nDone!")


if __name__ == "__main__":
    main()
