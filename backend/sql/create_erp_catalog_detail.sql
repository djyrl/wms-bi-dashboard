-- ============================================================
-- ERP Catalog ZMMRP048 需求计划明细表
-- 基于 erp_catalog_zmmrp048.row_json 解析
-- ============================================================
CREATE TABLE IF NOT EXISTS erp_catalog_zmmrp048_detail (
    -- 源表原始字段
    id              VARCHAR(128)  NOT NULL,   -- 主键ID
    tenant_id       VARCHAR(128),             -- 租户ID
    pbdnr           VARCHAR(255),             -- 需求计划号
    create_date     TIMESTAMP,                -- 创建时间
    update_date     TIMESTAMP,                -- 更新时间

    -- row_json 解析字段
    ZXMH            VARCHAR(50),              -- 需求计划行号
    MATNR           VARCHAR(50),              -- 物料号
    MAKTX           VARCHAR(255),             -- 物料描述
    WERKS           VARCHAR(50),              -- 工厂
    Z_DATE          VARCHAR(50),              -- 提报日期
    EBELN_F         VARCHAR(50),              -- 采购订单号
    REQUDATE        VARCHAR(50),              -- 需求日期
    BUDAT_RK        VARCHAR(50),              -- 订单入库日期
    BANFN_F         VARCHAR(50),              -- 外购采购申请号
    ZCLOSE          VARCHAR(50),              -- 关闭标记
    ZZSRM_CTRNO     VARCHAR(50),              -- 合同编号
    Z_USER          VARCHAR(50),              -- 申请人
    ZT              VARCHAR(50),              -- 状态
    ZMEMO           VARCHAR(255),             -- 备注
    OAMOUNT         VARCHAR(50),              -- 需求数量
    MSEHL           VARCHAR(50),              -- 计量单位
    ZSNETPR         VARCHAR(50),              -- 需求计划金额
    NAME1           VARCHAR(255),             -- 供应商名称
    LIFNR           VARCHAR(50),              -- 供应商
    MENGE_F         VARCHAR(50),              -- 采购订单数量
    NETPR           VARCHAR(50),              -- 单价
    NETPR_JJ        VARCHAR(50),              -- 订单总净价
    ZHSDJ           VARCHAR(50),              -- 含税单价
    ZHSZJ           VARCHAR(50),              -- 含税总价
    PLANCAT_TXT     VARCHAR(50),              -- 计划类别描述
    Z_PBDNR_MS      VARCHAR(255),             -- 需求计划描述
    REQPTMT_NAME    VARCHAR(255),             -- 需求部门描述
    OAMOUNT_HSL     VARCHAR(50),              -- 已审批的需求汇总数量
    PREIS           VARCHAR(50),              -- 评估单价
    ZDSDHH          VARCHAR(50),              -- 电商订货号
    Z_SPZT          VARCHAR(50),              -- 审批状态
    ZZCGCL_T        VARCHAR(50),              -- 采购策略
    Z_SPCL          VARCHAR(50),              -- 审批策略
    ERDAT           VARCHAR(50),              -- 到货日期
    MENGE2          VARCHAR(50),              -- 收货入库数量
    DMBTR_RK        VARCHAR(50),              -- 入库金额
    CHARG           VARCHAR(50),              -- 入库批次号
    MENGE3          VARCHAR(50),              -- 领料数量
    DMBTR_CK        VARCHAR(50),              -- 出库金额
    MENGE1_F        VARCHAR(50),              -- 外购采购申请数量
    RLWRT           VARCHAR(50),              -- 采购计划金额
    ZLKSL           VARCHAR(50),              -- 利库数量
    ZLKJE           VARCHAR(50),              -- 利库金额
    Z_DXXMH         VARCHAR(50),              -- 大修项目号
    AEDAT           VARCHAR(50),              -- 订单创建日期
    BUDAT_LY        VARCHAR(50),              -- 订单领用日期
    SAKNR_T         VARCHAR(255),             -- 领料科目描述
    ZTYPE           VARCHAR(50),              -- 需求计划类型
    ZSDATE          VARCHAR(50),              -- 需求计划的终审日期
    MATKL           VARCHAR(50),              -- 物料组
    WGBEZ           VARCHAR(50),              -- 物料组描述
    REQPTMT         VARCHAR(50),              -- 需求部门
    EINDT           VARCHAR(50),              -- 订单交货日期
    BPRME_C         VARCHAR(50),              -- 采购价格单位
    ZREGNUM         VARCHAR(50),              -- 收货登记数量
    CLABS           VARCHAR(50),              -- 物料当前库存
    PLANCAT         VARCHAR(50),              -- 计划类别
    PLANCAT2        VARCHAR(50),              -- 计划对象
    PLANCAT_TXT2    VARCHAR(255),             -- 计划对象描述
    ZZXMBH          VARCHAR(255),             -- 项目名称
    PLANCAT_TXT3    VARCHAR(255),             -- 项目名称描述
    EKGRP           VARCHAR(50),              -- 采购组
    POST1           VARCHAR(255),             -- WBS描述
    RSPOS           VARCHAR(50),              -- 行项目
    POSID           VARCHAR(50),              -- WBS元素
    ZPOST1          VARCHAR(255),             -- WBS描述
    WLYSL           VARCHAR(50),              -- 未领用数量
    ZSTK_CLS        VARCHAR(50),              -- 库存分类
    APTXT           VARCHAR(255),             -- 库存分类描述

    PRIMARY KEY (id)
);

-- ============================================================
-- 字段备注
-- ============================================================
COMMENT ON TABLE erp_catalog_zmmrp048_detail IS 'ERP ZMMRP048 需求计划明细表，从 erp_catalog_zmmrp048.row_json 解析';

COMMENT ON COLUMN erp_catalog_zmmrp048_detail.pbdnr IS '需求计划号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZXMH IS '需求计划行号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MATNR IS '物料号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MAKTX IS '物料描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.WERKS IS '工厂';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.Z_DATE IS '提报日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.EBELN_F IS '采购订单号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.REQUDATE IS '需求日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.BUDAT_RK IS '订单入库日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.BANFN_F IS '外购采购申请号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZCLOSE IS '关闭标记';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZZSRM_CTRNO IS '合同编号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.Z_USER IS '申请人';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZT IS '状态';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZMEMO IS '备注';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.OAMOUNT IS '需求数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MSEHL IS '计量单位';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZSNETPR IS '需求计划金额';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.NAME1 IS '供应商名称';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.LIFNR IS '供应商';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MENGE_F IS '采购订单数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.NETPR IS '单价';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.NETPR_JJ IS '订单总净价';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZHSDJ IS '含税单价';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZHSZJ IS '含税总价';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.PLANCAT_TXT IS '计划类别描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.Z_PBDNR_MS IS '需求计划描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.REQPTMT_NAME IS '需求部门描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.OAMOUNT_HSL IS '已审批的需求汇总数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.PREIS IS '评估单价';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZDSDHH IS '电商订货号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.Z_SPZT IS '审批状态';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZZCGCL_T IS '采购策略';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.Z_SPCL IS '审批策略';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ERDAT IS '到货日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MENGE2 IS '收货入库数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.DMBTR_RK IS '入库金额';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.CHARG IS '入库批次号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MENGE3 IS '领料数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.DMBTR_CK IS '出库金额';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MENGE1_F IS '外购采购申请数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.RLWRT IS '采购计划金额';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZLKSL IS '利库数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZLKJE IS '利库金额';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.Z_DXXMH IS '大修项目号';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.AEDAT IS '订单创建日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.BUDAT_LY IS '订单领用日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.SAKNR_T IS '领料科目描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZTYPE IS '需求计划类型';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZSDATE IS '需求计划的终审日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.MATKL IS '物料组';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.WGBEZ IS '物料组描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.REQPTMT IS '需求部门';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.EINDT IS '订单交货日期';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.BPRME_C IS '采购价格单位';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZREGNUM IS '收货登记数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.CLABS IS '物料当前库存';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.PLANCAT IS '计划类别';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.PLANCAT2 IS '计划对象';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.PLANCAT_TXT2 IS '计划对象描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZZXMBH IS '项目名称';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.PLANCAT_TXT3 IS '项目名称描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.EKGRP IS '采购组';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.POST1 IS 'WBS描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.RSPOS IS '行项目';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.POSID IS 'WBS元素';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZPOST1 IS 'WBS描述';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.WLYSL IS '未领用数量';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.ZSTK_CLS IS '库存分类';
COMMENT ON COLUMN erp_catalog_zmmrp048_detail.APTXT IS '库存分类描述';
