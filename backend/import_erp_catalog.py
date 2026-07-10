"""
ERP Catalog Data Import Program
================================
从 DB_CONFIG_ERP.erp_catalog_zmmrp048 读取数据，
按指定字段映射解析 row_json，导入到 DB_CONFIG 目标数据库。
"""

import sys
import json
import psycopg2
import psycopg2.extras

# Fix UnicodeEncodeError (Python 3.6 compat)
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

# ============================================================
# 数据库配置
# ============================================================

DB_CONFIG_ERP = {
    "host": "192.168.92.240",
    "port": 54324,
    "dbname": "garden_wms",
    "user": "garden_wms",
    "password": "garden_wms@2025",
}

DB_CONFIG = {
    "host": "122.51.39.235",
    "port": 54321,
    "dbname": "garden_wms",
    "user": "kingbase",
    "password": "123456",
}

TARGET_TABLE = "wbs_zmmrp048_parsed"
BATCH_SIZE = 500

# ============================================================
# 字段映射：[(字段名, SQL类型, 中文注释)]
# ============================================================

FIELD_MAPPING = [
    ("zxmh",          "VARCHAR(50)",   "需求计划行号"),
    ("matnr",         "VARCHAR(50)",   "物料号"),
    ("maktx",         "VARCHAR(255)",  "物料描述"),
    ("werks",         "VARCHAR(50)",   "工厂"),
    ("z_date",        "VARCHAR(50)",   "提报日期"),
    ("ebeln_f",       "VARCHAR(50)",   "采购订单号"),
    ("requdate",      "VARCHAR(50)",   "需求日期"),
    ("budat_rk",      "VARCHAR(50)",   "订单入库日期"),
    ("banfn_f",       "VARCHAR(50)",   "外购采购申请号"),
    ("zclose",        "VARCHAR(50)",   "关闭标记"),
    ("zzsrm_ctrno",   "VARCHAR(50)",   "合同编号"),
    ("z_user",        "VARCHAR(50)",   "申请人"),
    ("zt",            "VARCHAR(50)",   "状态"),
    ("zmemo",         "VARCHAR(255)",  "备注"),
    ("oamount",       "VARCHAR(50)",   "需求数量"),
    ("msehl",         "VARCHAR(50)",   "计量单位"),
    ("zsnetpr",       "VARCHAR(50)",   "需求计划金额"),
    ("name1",         "VARCHAR(255)",  "供应商名称"),
    ("lifnr",         "VARCHAR(50)",   "供应商"),
    ("menge_f",       "VARCHAR(50)",   "采购订单数量"),
    ("netpr",         "VARCHAR(50)",   "单价"),
    ("netpr_jj",      "VARCHAR(50)",   "订单总净价"),
    ("zhsdj",         "VARCHAR(50)",   "含税单价"),
    ("zhszj",         "VARCHAR(50)",   "含税总价"),
    ("plancat_txt",   "VARCHAR(50)",   "计划类别描述"),
    ("z_pbdnr_ms",    "VARCHAR(255)",  "需求计划描述"),
    ("reqptmt_name",  "VARCHAR(255)",  "需求部门描述"),
    ("oamount_hsl",   "VARCHAR(50)",   "已审批的需求汇总数量"),
    ("preis",         "VARCHAR(50)",   "评估单价"),
    ("zdsdhh",        "VARCHAR(50)",   "电商订货号"),
    ("z_spzt",        "VARCHAR(50)",   "审批状态"),
    ("zzcgcl_t",      "VARCHAR(50)",   "采购策略"),
    ("z_spcl",        "VARCHAR(50)",   "审批策略"),
    ("erdat",         "VARCHAR(50)",   "到货日期"),
    ("menge2",        "VARCHAR(50)",   "收货入库数量"),
    ("dmbtr_rk",      "VARCHAR(50)",   "入库金额"),
    ("charg",         "VARCHAR(50)",   "入库批次号"),
    ("menge3",        "VARCHAR(50)",   "领料数量"),
    ("dmbtr_ck",      "VARCHAR(50)",   "出库金额"),
    ("menge1_f",      "VARCHAR(50)",   "外购采购申请数量"),
    ("rlwrt",         "VARCHAR(50)",   "采购计划金额"),
    ("zlksl",         "VARCHAR(50)",   "利库数量"),
    ("zlkje",         "VARCHAR(50)",   "利库金额"),
    ("z_dxxmh",       "VARCHAR(50)",   "大修项目号"),
    ("aedat",         "VARCHAR(50)",   "订单创建日期"),
    ("budat_ly",      "VARCHAR(50)",   "订单领用日期"),
    ("saknr_t",       "VARCHAR(255)",  "领料科目描述"),
    ("ztype",         "VARCHAR(50)",   "需求计划类型"),
    ("zsdate",        "VARCHAR(50)",   "需求计划的终审日期"),
    ("matkl",         "VARCHAR(50)",   "物料组"),
    ("wgbez",         "VARCHAR(50)",   "物料组描述"),
    ("reqptmt",       "VARCHAR(50)",   "需求部门"),
    ("eindt",         "VARCHAR(50)",   "订单交货日期"),
    ("bprme_c",       "VARCHAR(50)",   "采购价格单位"),
    ("zregnum",       "VARCHAR(50)",   "收货登记数量"),
    ("clabs",         "VARCHAR(50)",   "物料当前库存"),
    ("plancat",       "VARCHAR(50)",   "计划类别"),
    ("plancat2",      "VARCHAR(50)",   "计划对象"),
    ("plancat_txt2",  "VARCHAR(255)",  "计划对象描述"),
    ("zzxmbh",        "VARCHAR(255)",  "项目名称"),
    ("plancat_txt3",  "VARCHAR(255)",  "项目名称描述"),
    ("ekgrp",         "VARCHAR(50)",   "采购组"),
    ("post1",         "VARCHAR(255)",  "WBS描述"),
    ("rspos",         "VARCHAR(50)",   "行项目"),
    ("posid",         "VARCHAR(50)",   "WBS元素"),
    ("zpost1",        "VARCHAR(255)",  "WBS描述"),
    ("wlysl",         "VARCHAR(50)",   "未领用数量"),
    ("zstk_cls",      "VARCHAR(50)",   "库存分类"),
    ("aptxt",         "VARCHAR(255)",  "库存分类描述"),
]


# ============================================================
# Step 1: 生成建表语句
# ============================================================

def generate_create_table_sql() -> str:
    lines = []
    lines.append("-- ============================================================")
    lines.append("-- ERP ZMMRP048 需求计划明细表")
    lines.append("-- 基于 erp_catalog_zmmrp048.row_json 解析")
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
            # Last column: trailing comma must be present BEFORE the PRIMARY KEY
            # constraint, since -- inline comments eat the newline to the next token.
            lines.append("    {:<16s} {:<15s},  -- {}".format(name, sql_type, comment))
        else:
            lines.append("    {:<16s} {:<15s},  -- {}".format(name, sql_type, comment))

    lines.append("")
    lines.append("    PRIMARY KEY (id)")
    lines.append(");")

    # COMMENT ON
    lines.append("")
    lines.append("COMMENT ON TABLE {} IS 'ERP ZMMRP048 需求计划明细表';".format(TARGET_TABLE))
    lines.append("COMMENT ON COLUMN {}.pbdnr IS '需求计划号';".format(TARGET_TABLE))
    for name, sql_type, comment in FIELD_MAPPING:
        lines.append("COMMENT ON COLUMN {}.{} IS '{}';".format(TARGET_TABLE, name, comment))

    return "\n".join(lines)


# ============================================================
# Step 2: 创建目标表
# ============================================================

def create_target_table(create_sql: str):
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS {} CASCADE".format(TARGET_TABLE))
    print("Dropped old table: {}".format(TARGET_TABLE))

    # Split CREATE TABLE and COMMENT ON statements — psycopg2 only
    # executes one statement per execute() call.
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
    src_conn = psycopg2.connect(**DB_CONFIG_ERP)
    src_conn.set_client_encoding("UTF8")

    dst_conn = psycopg2.connect(**DB_CONFIG)
    dst_conn.set_client_encoding("UTF8")
    dst_conn.autocommit = False

    src_cur = src_conn.cursor("erp_cursor")
    src_cur.itersize = BATCH_SIZE
    dst_cur = dst_conn.cursor()

    source_columns = ["id", "tenant_id", "pbdnr", "create_date", "update_date"]
    json_columns_lower = [name for name, _, _ in FIELD_MAPPING]
    # row_json keys are UPPERCASE, so map lowercase column -> uppercase key for lookup
    json_keys_upper = [name.upper() for name in json_columns_lower]
    all_columns = source_columns + json_columns_lower
    insert_sql = "INSERT INTO {} ({}) VALUES %s".format(
        TARGET_TABLE, ", ".join(all_columns)
    )

    src_cur.execute(
        "SELECT id, tenant_id, pbdnr, create_date, update_date, row_json "
        "FROM erp_catalog_zmmrp048"
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
            print("Imported {:,} / 10,255 rows...".format(total))
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
    print("ERP Catalog Import Program")
    print("=" * 60)
    print("Source: {host}:{port}/{dbname}".format(**DB_CONFIG_ERP))
    print("Target: {host}:{port}/{dbname}".format(**DB_CONFIG))
    print("Source table: erp_catalog_zmmrp048")
    print("Target table: {}".format(TARGET_TABLE))
    print("Fields: {}".format(len(FIELD_MAPPING)))
    print("=" * 60)

    # Step 1: Generate CREATE TABLE SQL
    print("\n[Step 1] Generating CREATE TABLE SQL...")
    create_sql = generate_create_table_sql()

    # Write SQL to file for review
    with open("sql/create_wms_zmmrp048.sql", "w", encoding="utf-8") as f:
        f.write(create_sql)
    print("SQL written to sql/create_wms_zmmrp048.sql")
    print("\n" + create_sql)
    print("=" * 60)

    # Step 2: Create table
    print("\n[Step 2] Creating target table...")
    create_target_table(create_sql)

    # Step 3: Import data
    print("\n[Step 3] Importing data...")
    import_data()

    print("\nDone!")


if __name__ == "__main__":
    main()
