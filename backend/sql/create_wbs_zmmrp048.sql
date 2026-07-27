-- ============================================================
-- ERP ZMMRP048 需求计划明细表
-- 基于 erp_catalog_zmmrp048.row_json 解析
-- ============================================================
CREATE TABLE IF NOT EXISTS wbs_zmmrp048_parsed (
    -- 源表原始字段
    id              VARCHAR(128)  NOT NULL,
    tenant_id       VARCHAR(128),
    pbdnr           VARCHAR(255),
    create_date     TIMESTAMP,
    update_date     TIMESTAMP,

    -- row_json 解析字段
    zxmh             VARCHAR(50)    ,  -- 需求计划行号
    matnr            VARCHAR(50)    ,  -- 物料号
    maktx            VARCHAR(255)   ,  -- 物料描述
    werks            VARCHAR(50)    ,  -- 工厂
    z_date           VARCHAR(50)    ,  -- 提报日期
    ebeln_f          VARCHAR(50)    ,  -- 采购订单号
    requdate         VARCHAR(50)    ,  -- 需求日期
    budat_rk         VARCHAR(50)    ,  -- 订单入库日期
    banfn_f          VARCHAR(50)    ,  -- 外购采购申请号
    zclose           VARCHAR(50)    ,  -- 关闭标记
    zzsrm_ctrno      VARCHAR(50)    ,  -- 合同编号
    z_user           VARCHAR(50)    ,  -- 申请人
    zt               VARCHAR(50)    ,  -- 状态
    zmemo            VARCHAR(255)   ,  -- 备注
    oamount          VARCHAR(50)    ,  -- 需求数量
    msehl            VARCHAR(50)    ,  -- 计量单位
    zsnetpr          VARCHAR(50)    ,  -- 需求计划金额
    name1            VARCHAR(255)   ,  -- 供应商名称
    lifnr            VARCHAR(50)    ,  -- 供应商
    menge_f          VARCHAR(50)    ,  -- 采购订单数量
    netpr            VARCHAR(50)    ,  -- 单价
    netpr_jj         VARCHAR(50)    ,  -- 订单总净价
    zhsdj            VARCHAR(50)    ,  -- 含税单价
    zhszj            VARCHAR(50)    ,  -- 含税总价
    plancat_txt      VARCHAR(50)    ,  -- 计划类别描述
    z_pbdnr_ms       VARCHAR(255)   ,  -- 需求计划描述
    reqptmt_name     VARCHAR(255)   ,  -- 需求部门描述
    oamount_hsl      VARCHAR(50)    ,  -- 已审批的需求汇总数量
    preis            VARCHAR(50)    ,  -- 评估单价
    zdsdhh           VARCHAR(50)    ,  -- 电商订货号
    z_spzt           VARCHAR(50)    ,  -- 审批状态
    zzcgcl_t         VARCHAR(50)    ,  -- 采购策略
    z_spcl           VARCHAR(50)    ,  -- 审批策略
    erdat            VARCHAR(50)    ,  -- 到货日期
    menge2           VARCHAR(50)    ,  -- 收货入库数量
    dmbtr_rk         VARCHAR(50)    ,  -- 入库金额
    charg            VARCHAR(50)    ,  -- 入库批次号
    menge3           VARCHAR(50)    ,  -- 领料数量
    dmbtr_ck         VARCHAR(50)    ,  -- 出库金额
    menge1_f         VARCHAR(50)    ,  -- 外购采购申请数量
    rlwrt            VARCHAR(50)    ,  -- 采购计划金额
    zlksl            VARCHAR(50)    ,  -- 利库数量
    zlkje            VARCHAR(50)    ,  -- 利库金额
    z_dxxmh          VARCHAR(50)    ,  -- 大修项目号
    aedat            VARCHAR(50)    ,  -- 订单创建日期
    budat_ly         VARCHAR(50)    ,  -- 订单领用日期
    saknr_t          VARCHAR(255)   ,  -- 领料科目描述
    ztype            VARCHAR(50)    ,  -- 需求计划类型
    zsdate           VARCHAR(50)    ,  -- 需求计划的终审日期
    matkl            VARCHAR(50)    ,  -- 物料组
    wgbez            VARCHAR(50)    ,  -- 物料组描述
    reqptmt          VARCHAR(50)    ,  -- 需求部门
    eindt            VARCHAR(50)    ,  -- 订单交货日期
    bprme_c          VARCHAR(50)    ,  -- 采购价格单位
    zregnum          VARCHAR(50)    ,  -- 收货登记数量
    clabs            VARCHAR(50)    ,  -- 物料当前库存
    plancat          VARCHAR(50)    ,  -- 计划类别
    plancat2         VARCHAR(50)    ,  -- 计划对象
    plancat_txt2     VARCHAR(255)   ,  -- 计划对象描述
    zzxmbh           VARCHAR(255)   ,  -- 项目名称
    plancat_txt3     VARCHAR(255)   ,  -- 项目名称描述
    ekgrp            VARCHAR(50)    ,  -- 采购组
    post1            VARCHAR(255)   ,  -- WBS描述
    rspos            VARCHAR(50)    ,  -- 行项目
    posid            VARCHAR(50)    ,  -- WBS元素
    zpost1           VARCHAR(255)   ,  -- WBS描述
    wlysl            VARCHAR(50)    ,  -- 未领用数量
    zstk_cls         VARCHAR(50)    ,  -- 库存分类
    aptxt            VARCHAR(255)   ,  -- 库存分类描述

    PRIMARY KEY (id)
);

COMMENT ON TABLE wbs_zmmrp048_parsed IS 'ERP ZMMRP048 需求计划明细表';
COMMENT ON COLUMN wbs_zmmrp048_parsed.pbdnr IS '需求计划号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zxmh IS '需求计划行号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.matnr IS '物料号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.maktx IS '物料描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.werks IS '工厂';
COMMENT ON COLUMN wbs_zmmrp048_parsed.z_date IS '提报日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.ebeln_f IS '采购订单号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.requdate IS '需求日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.budat_rk IS '订单入库日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.banfn_f IS '外购采购申请号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zclose IS '关闭标记';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zzsrm_ctrno IS '合同编号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.z_user IS '申请人';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zt IS '状态';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zmemo IS '备注';
COMMENT ON COLUMN wbs_zmmrp048_parsed.oamount IS '需求数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.msehl IS '计量单位';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zsnetpr IS '需求计划金额';
COMMENT ON COLUMN wbs_zmmrp048_parsed.name1 IS '供应商名称';
COMMENT ON COLUMN wbs_zmmrp048_parsed.lifnr IS '供应商';
COMMENT ON COLUMN wbs_zmmrp048_parsed.menge_f IS '采购订单数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.netpr IS '单价';
COMMENT ON COLUMN wbs_zmmrp048_parsed.netpr_jj IS '订单总净价';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zhsdj IS '含税单价';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zhszj IS '含税总价';
COMMENT ON COLUMN wbs_zmmrp048_parsed.plancat_txt IS '计划类别描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.z_pbdnr_ms IS '需求计划描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.reqptmt_name IS '需求部门描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.oamount_hsl IS '已审批的需求汇总数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.preis IS '评估单价';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zdsdhh IS '电商订货号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.z_spzt IS '审批状态';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zzcgcl_t IS '采购策略';
COMMENT ON COLUMN wbs_zmmrp048_parsed.z_spcl IS '审批策略';
COMMENT ON COLUMN wbs_zmmrp048_parsed.erdat IS '到货日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.menge2 IS '收货入库数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.dmbtr_rk IS '入库金额';
COMMENT ON COLUMN wbs_zmmrp048_parsed.charg IS '入库批次号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.menge3 IS '领料数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.dmbtr_ck IS '出库金额';
COMMENT ON COLUMN wbs_zmmrp048_parsed.menge1_f IS '外购采购申请数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.rlwrt IS '采购计划金额';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zlksl IS '利库数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zlkje IS '利库金额';
COMMENT ON COLUMN wbs_zmmrp048_parsed.z_dxxmh IS '大修项目号';
COMMENT ON COLUMN wbs_zmmrp048_parsed.aedat IS '订单创建日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.budat_ly IS '订单领用日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.saknr_t IS '领料科目描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.ztype IS '需求计划类型';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zsdate IS '需求计划的终审日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.matkl IS '物料组';
COMMENT ON COLUMN wbs_zmmrp048_parsed.wgbez IS '物料组描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.reqptmt IS '需求部门';
COMMENT ON COLUMN wbs_zmmrp048_parsed.eindt IS '订单交货日期';
COMMENT ON COLUMN wbs_zmmrp048_parsed.bprme_c IS '采购价格单位';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zregnum IS '收货登记数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.clabs IS '物料当前库存';
COMMENT ON COLUMN wbs_zmmrp048_parsed.plancat IS '计划类别';
COMMENT ON COLUMN wbs_zmmrp048_parsed.plancat2 IS '计划对象';
COMMENT ON COLUMN wbs_zmmrp048_parsed.plancat_txt2 IS '计划对象描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zzxmbh IS '项目名称';
COMMENT ON COLUMN wbs_zmmrp048_parsed.plancat_txt3 IS '项目名称描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.ekgrp IS '采购组';
COMMENT ON COLUMN wbs_zmmrp048_parsed.post1 IS 'WBS描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.rspos IS '行项目';
COMMENT ON COLUMN wbs_zmmrp048_parsed.posid IS 'WBS元素';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zpost1 IS 'WBS描述';
COMMENT ON COLUMN wbs_zmmrp048_parsed.wlysl IS '未领用数量';
COMMENT ON COLUMN wbs_zmmrp048_parsed.zstk_cls IS '库存分类';
COMMENT ON COLUMN wbs_zmmrp048_parsed.aptxt IS '库存分类描述';