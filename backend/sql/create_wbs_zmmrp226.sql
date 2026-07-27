-- ============================================================
-- ERP ZMMRP226 需求计划明细表
-- 基于 erp_catalog_zmmrp226.row_json 解析
-- ============================================================
CREATE TABLE IF NOT EXISTS wbs_zmmrp226_parsed (
    -- 源表原始字段
    id              VARCHAR(128)  NOT NULL,
    tenant_id       VARCHAR(128),
    pbdnr           VARCHAR(255),
    create_date     TIMESTAMP,
    update_date     TIMESTAMP,

    -- row_json 解析字段
    zxmh             VARCHAR(50)    ,  -- 项目号
    matnr            VARCHAR(50)    ,  -- 物料编号
    maktx            VARCHAR(255)   ,  -- 物料描述
    werks            VARCHAR(50)    ,  -- 工厂
    z_date           VARCHAR(50)    ,  -- 提报时间
    requdate         VARCHAR(50)    ,  -- 需求日期
    ramount          VARCHAR(50)    ,  -- 当前需求数量
    z_spztms         VARCHAR(50)    ,  -- 当前审批状态
    z_name           VARCHAR(50)    ,  -- 提报人
    contact          VARCHAR(50)    ,  -- 联系人
    zcat             VARCHAR(50)    ,  -- 计划类型
    z_dxxmh          VARCHAR(50)    ,  -- WBS项目编号
    zindex           VARCHAR(50)    ,  -- 计数
    mstae            VARCHAR(50)    ,  -- 物料冻结状态
    mtstb            VARCHAR(255)   ,  -- 物料冻结状态描述
    znetpr           VARCHAR(50)    ,  -- 单价
    zyssl            VARCHAR(50)    ,  -- 原需求数量
    zjjsprq          VARCHAR(50)    ,  -- 拒绝审批日期
    zsnetpr          VARCHAR(50)    ,  -- 可用金额
    matkl            VARCHAR(50)    ,  -- 物料组
    wgbez            VARCHAR(50)    ,  -- 物料组描述
    kmlb             VARCHAR(50)    ,  -- 科目类别
    kmname           VARCHAR(255)   ,  -- 科目类别描述
    z_jhlb_nm        VARCHAR(255)   ,  -- 计划类别
    reqptmt_name     VARCHAR(255)   ,  -- 部门
    ekgrp            VARCHAR(50)    ,  -- 采购组
    eknam            VARCHAR(255)   ,  -- 采购组描述
    z_dqjb           VARCHAR(50)    ,  -- 审批层级
    zapprove         VARCHAR(50)    ,  -- 审批状态标识
    zzzsprq          VARCHAR(50)    ,  -- 最终审批日期
    fipex            VARCHAR(50)    ,  -- 预算类别
    zsnetpr_kp       VARCHAR(50)    ,  -- 行项目金额
    zsum_upd         VARCHAR(50)    ,  -- 本单占用金额
    z_qcys           VARCHAR(50)    ,  -- 期初预算金额
    zljys_yet        VARCHAR(50)    ,  -- 累计预算金额
    zsyys_last       VARCHAR(50)    ,  -- 剩余预算金额
    zuname           VARCHAR(50)    ,  -- 用户名
    zudate           VARCHAR(50)    ,  -- 更改日期
    zutime           VARCHAR(50)    ,  -- 更改时间
    msehl            VARCHAR(50)    ,  -- 单位
    zrnetpr          VARCHAR(50)    ,  -- 参考单价
    sum_pbdnr        VARCHAR(50)    ,  -- 独立需求
    z_cgjhh          VARCHAR(50)    ,  -- 采购申请
    z_cgjh_hh        VARCHAR(50)    ,  -- 采购申请行号
    berid            VARCHAR(50)    ,  -- MRP范围
    bertx            VARCHAR(50)    ,  -- MRP范围文本
    tel              VARCHAR(50)    ,  -- 联系电话
    z_sdlk           VARCHAR(50)    ,  -- 利库库存数
    labor            VARCHAR(50)    ,  -- 采购策略
    lbtxt            VARCHAR(255)   ,  -- 采购策略描述
    plancat2         VARCHAR(50)    ,  -- 计划对象
    plancat_txt2     VARCHAR(255)   ,  -- 计划对象描述
    zjhjsrq          VARCHAR(50)    ,  -- 计划结束日期
    zjhgbsj          VARCHAR(50)    ,  -- 计划关闭(或删除)日
    zbdzei           VARCHAR(50)    ,  -- 需求计划指针
    consg            VARCHAR(50)    ,  -- 寄售标识
    zclose           VARCHAR(50)    ,  -- 关闭标识
    faildt           VARCHAR(50)    ,  -- 失效日期
    zgscgcl          VARCHAR(50)    ,  -- 采购方式
    frgrp            VARCHAR(50)    ,  -- 审批组
    z_pbdnr_ms       VARCHAR(255)   ,  -- 需求计划描述
    z_sjjh           VARCHAR(50)    ,  -- 件号
    zstk_cls         VARCHAR(50)    ,  -- 库存分类
    aptxt            VARCHAR(255)   ,  -- 库存分类描述
    zzxmbh           VARCHAR(255)   ,  -- 项目编号
    ktext            VARCHAR(255)   ,  -- 项目描述
    zhxmje           VARCHAR(50)    ,  -- 需求计划汇总金额
    z_memo_yj        VARCHAR(255)   ,  -- 审批意见
    z_memo           VARCHAR(255)   ,  -- 备注
    z_sbh            VARCHAR(50)    ,  -- 设备号
    z_jcch           VARCHAR(50)    ,  -- 机车车号
    anln1            VARCHAR(50)    ,  -- 资产号
    plnum            VARCHAR(50)    ,  -- 计划订单号
    zaptxt           VARCHAR(255)   ,  -- 备件分类
    z_pbdnr_pzrq     VARCHAR(50)    ,  -- 批准日期
    zamtyp           VARCHAR(50)    ,  -- 备件机型编码
    amtxt            VARCHAR(255)   ,  -- 备件机型描述
    zmatyp           VARCHAR(50)    ,  -- 主机型号编码
    mttxt            VARCHAR(255)   ,  -- 主机型号描述
    zgc_billcode     VARCHAR(50)    ,  -- 公务车采购申请单号
    zgc_item         VARCHAR(50)    ,  -- 公务车行项目编号
    zgc_cpxh         VARCHAR(50)    ,  -- 公务车厂牌型号
    zgc_pl           VARCHAR(50)    ,  -- 公务车排量
    zgc_cllbname     VARCHAR(50)    ,  -- 车辆类别
    zgc_clytname     VARCHAR(50)    ,  -- 车辆用途
    zgc_yjjg         VARCHAR(50)    ,  -- 公务车预计价格
    zgc_creater      VARCHAR(50)    ,  -- 公务车制单人
    zdsdhh           VARCHAR(50)    ,  -- 电商订货号
    zzjyxyfsbh       VARCHAR(50)    ,  -- 建议寻源方式
    zzxyfsddtxt      VARCHAR(255)   ,  -- 建议寻源方式描述
    dispo            VARCHAR(50)    ,  -- MRP控制者
    dsnam            VARCHAR(50)    ,  -- 控制者名称
    zzfbbh           VARCHAR(50)    ,  -- 分包编号
    zzfbms           VARCHAR(255)   ,  -- 分包描述
    maktx_long       VARCHAR(500)   ,  -- 物料长描述
    zfjwdbz          VARCHAR(50)    ,  -- 附件文档挂接标识
    zjhlbtxt         VARCHAR(255)   ,  -- 时间计划类别
    zreqyy           VARCHAR(255)   ,  -- 申请原因
    zxqlx            VARCHAR(50)    ,  -- 需求类型
    zzjwz            VARCHAR(50)    ,  -- 装机位置
    zzjl             VARCHAR(50)    ,  -- 装机量
    zyscgl           VARCHAR(50)    ,  -- 原始采购数量
    zysdbl           VARCHAR(50)    ,  -- 原始调拨数量
    zbhcs            VARCHAR(50)    ,  -- 驳回次数
    post1            VARCHAR(255)   ,  -- WBS项目描述
    zjhfl            VARCHAR(50)    ,  -- 计划分类
    zsfgc            VARCHAR(50)    ,  -- 是否工程
    jswj_id          VARCHAR(50)    ,  -- 技术文件ID
    lgort            VARCHAR(50)    ,  -- 库存地点
    z_fh             VARCHAR(50)    ,  -- 返回标识
    z_fhyy           VARCHAR(255)   ,  -- 返回原因
    zdxsykc          VARCHAR(50)    ,  -- 大修剩余库存数量
    zlksl            VARCHAR(50)    ,  -- 利库数量
    zlkhxq           VARCHAR(50)    ,  -- 利库后需求数量
    zlkyy            VARCHAR(255)   ,  -- 利库原因
    zlkr             VARCHAR(50)    ,  -- 利库人
    zlkrq            VARCHAR(50)    ,  -- 利库日期
    zlksj            VARCHAR(50)    ,  -- 利库时间
    zthjkc           VARCHAR(50)    ,  -- 替换件库存
    flag             VARCHAR(50)    ,  -- 标识字段
    sobkz01          VARCHAR(50)    ,  -- 是否寄售
    posid            VARCHAR(50)    ,  -- WBS元素
    zlcgb            VARCHAR(50)    ,  -- 联储共备类型
    zmmywzgbm        VARCHAR(50)    ,  -- 业务主管部门
    zmmywzgbmd       VARCHAR(255)   ,  -- 业务主管部门名称
    zljzgckc         VARCHAR(50)    ,  -- 零价值工厂库存
    zjhlb2           VARCHAR(50)    ,  -- 检修技改类型
    zjz              VARCHAR(50)    ,  -- 机组
    zsyccgjj         VARCHAR(50)    ,  -- 上一次采购净价
    zsycchsj         VARCHAR(50)    ,  -- 上一次采购含税价
    knttp            VARCHAR(50)    ,  -- 科目分配类别
    zknttx           VARCHAR(255)   ,  -- 科目分配类别描述
    zsaknr           VARCHAR(50)    ,  -- 科目编号
    zkostl           VARCHAR(50)    ,  -- 成本中心
    zltext           VARCHAR(255)   ,  -- 成本中心描述
    rzj              VARCHAR(50)    ,  -- 总价
    zfzhsjz          VARCHAR(50)    ,  -- 辅助核算机组
    zfwqxms          VARCHAR(255)   ,  -- 服务需求描述
    zdsbs            VARCHAR(50)    ,  -- 电商标识物料
    zob              VARCHAR(255)   ,  -- 推荐品牌
    zbzcc            VARCHAR(255)   ,  -- 原生产厂家
    zjhyj            VARCHAR(255)   ,  -- 计划依据
    zgsxmt           VARCHAR(50)    ,  -- 是否煤电公司项目
    zcgfw            VARCHAR(50)    ,  -- 采购范围
    zqztbr           VARCHAR(255)   ,  -- 潜在投标人及联系方式
    zgdzct           VARCHAR(50)    ,  -- 是否固定资产
    ndjh_bh          VARCHAR(50)    ,  -- 年度采购计划编号
    znumber          VARCHAR(50)    ,  -- 年度计划行号
    zsaknr_item      VARCHAR(50)    ,  -- 行项目总账科目
    z_syfx           VARCHAR(50)    ,  -- 使用方向
    z_syfxms         VARCHAR(255)   ,  -- 使用方向描述
    z_yslb           VARCHAR(50)    ,  -- 预算类别
    z_yslbms         VARCHAR(255)   ,  -- 预算类别描述
    z_dwbk           VARCHAR(50)    ,  -- 单位板块
    zmemo_url        VARCHAR(500)   ,  -- URL备注

    PRIMARY KEY (id)
);

COMMENT ON TABLE wbs_zmmrp226_parsed IS 'ERP ZMMRP226 需求计划明细表';
COMMENT ON COLUMN wbs_zmmrp226_parsed.pbdnr IS '需求计划号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zxmh IS '项目号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.matnr IS '物料编号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.maktx IS '物料描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.werks IS '工厂';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_date IS '提报时间';
COMMENT ON COLUMN wbs_zmmrp226_parsed.requdate IS '需求日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.ramount IS '当前需求数量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_spztms IS '当前审批状态';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_name IS '提报人';
COMMENT ON COLUMN wbs_zmmrp226_parsed.contact IS '联系人';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zcat IS '计划类型';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_dxxmh IS 'WBS项目编号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zindex IS '计数';
COMMENT ON COLUMN wbs_zmmrp226_parsed.mstae IS '物料冻结状态';
COMMENT ON COLUMN wbs_zmmrp226_parsed.mtstb IS '物料冻结状态描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.znetpr IS '单价';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zyssl IS '原需求数量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjjsprq IS '拒绝审批日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsnetpr IS '可用金额';
COMMENT ON COLUMN wbs_zmmrp226_parsed.matkl IS '物料组';
COMMENT ON COLUMN wbs_zmmrp226_parsed.wgbez IS '物料组描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.kmlb IS '科目类别';
COMMENT ON COLUMN wbs_zmmrp226_parsed.kmname IS '科目类别描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_jhlb_nm IS '计划类别';
COMMENT ON COLUMN wbs_zmmrp226_parsed.reqptmt_name IS '部门';
COMMENT ON COLUMN wbs_zmmrp226_parsed.ekgrp IS '采购组';
COMMENT ON COLUMN wbs_zmmrp226_parsed.eknam IS '采购组描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_dqjb IS '审批层级';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zapprove IS '审批状态标识';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzzsprq IS '最终审批日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.fipex IS '预算类别';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsnetpr_kp IS '行项目金额';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsum_upd IS '本单占用金额';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_qcys IS '期初预算金额';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zljys_yet IS '累计预算金额';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsyys_last IS '剩余预算金额';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zuname IS '用户名';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zudate IS '更改日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zutime IS '更改时间';
COMMENT ON COLUMN wbs_zmmrp226_parsed.msehl IS '单位';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zrnetpr IS '参考单价';
COMMENT ON COLUMN wbs_zmmrp226_parsed.sum_pbdnr IS '独立需求';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_cgjhh IS '采购申请';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_cgjh_hh IS '采购申请行号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.berid IS 'MRP范围';
COMMENT ON COLUMN wbs_zmmrp226_parsed.bertx IS 'MRP范围文本';
COMMENT ON COLUMN wbs_zmmrp226_parsed.tel IS '联系电话';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_sdlk IS '利库库存数';
COMMENT ON COLUMN wbs_zmmrp226_parsed.labor IS '采购策略';
COMMENT ON COLUMN wbs_zmmrp226_parsed.lbtxt IS '采购策略描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.plancat2 IS '计划对象';
COMMENT ON COLUMN wbs_zmmrp226_parsed.plancat_txt2 IS '计划对象描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjhjsrq IS '计划结束日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjhgbsj IS '计划关闭(或删除)日';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zbdzei IS '需求计划指针';
COMMENT ON COLUMN wbs_zmmrp226_parsed.consg IS '寄售标识';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zclose IS '关闭标识';
COMMENT ON COLUMN wbs_zmmrp226_parsed.faildt IS '失效日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgscgcl IS '采购方式';
COMMENT ON COLUMN wbs_zmmrp226_parsed.frgrp IS '审批组';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_pbdnr_ms IS '需求计划描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_sjjh IS '件号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zstk_cls IS '库存分类';
COMMENT ON COLUMN wbs_zmmrp226_parsed.aptxt IS '库存分类描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzxmbh IS '项目编号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.ktext IS '项目描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zhxmje IS '需求计划汇总金额';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_memo_yj IS '审批意见';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_memo IS '备注';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_sbh IS '设备号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_jcch IS '机车车号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.anln1 IS '资产号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.plnum IS '计划订单号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zaptxt IS '备件分类';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_pbdnr_pzrq IS '批准日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zamtyp IS '备件机型编码';
COMMENT ON COLUMN wbs_zmmrp226_parsed.amtxt IS '备件机型描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zmatyp IS '主机型号编码';
COMMENT ON COLUMN wbs_zmmrp226_parsed.mttxt IS '主机型号描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_billcode IS '公务车采购申请单号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_item IS '公务车行项目编号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_cpxh IS '公务车厂牌型号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_pl IS '公务车排量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_cllbname IS '车辆类别';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_clytname IS '车辆用途';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_yjjg IS '公务车预计价格';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgc_creater IS '公务车制单人';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zdsdhh IS '电商订货号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzjyxyfsbh IS '建议寻源方式';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzxyfsddtxt IS '建议寻源方式描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.dispo IS 'MRP控制者';
COMMENT ON COLUMN wbs_zmmrp226_parsed.dsnam IS '控制者名称';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzfbbh IS '分包编号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzfbms IS '分包描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.maktx_long IS '物料长描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zfjwdbz IS '附件文档挂接标识';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjhlbtxt IS '时间计划类别';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zreqyy IS '申请原因';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zxqlx IS '需求类型';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzjwz IS '装机位置';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zzjl IS '装机量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zyscgl IS '原始采购数量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zysdbl IS '原始调拨数量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zbhcs IS '驳回次数';
COMMENT ON COLUMN wbs_zmmrp226_parsed.post1 IS 'WBS项目描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjhfl IS '计划分类';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsfgc IS '是否工程';
COMMENT ON COLUMN wbs_zmmrp226_parsed.jswj_id IS '技术文件ID';
COMMENT ON COLUMN wbs_zmmrp226_parsed.lgort IS '库存地点';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_fh IS '返回标识';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_fhyy IS '返回原因';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zdxsykc IS '大修剩余库存数量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zlksl IS '利库数量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zlkhxq IS '利库后需求数量';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zlkyy IS '利库原因';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zlkr IS '利库人';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zlkrq IS '利库日期';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zlksj IS '利库时间';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zthjkc IS '替换件库存';
COMMENT ON COLUMN wbs_zmmrp226_parsed.flag IS '标识字段';
COMMENT ON COLUMN wbs_zmmrp226_parsed.sobkz01 IS '是否寄售';
COMMENT ON COLUMN wbs_zmmrp226_parsed.posid IS 'WBS元素';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zlcgb IS '联储共备类型';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zmmywzgbm IS '业务主管部门';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zmmywzgbmd IS '业务主管部门名称';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zljzgckc IS '零价值工厂库存';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjhlb2 IS '检修技改类型';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjz IS '机组';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsyccgjj IS '上一次采购净价';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsycchsj IS '上一次采购含税价';
COMMENT ON COLUMN wbs_zmmrp226_parsed.knttp IS '科目分配类别';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zknttx IS '科目分配类别描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsaknr IS '科目编号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zkostl IS '成本中心';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zltext IS '成本中心描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.rzj IS '总价';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zfzhsjz IS '辅助核算机组';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zfwqxms IS '服务需求描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zdsbs IS '电商标识物料';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zob IS '推荐品牌';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zbzcc IS '原生产厂家';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zjhyj IS '计划依据';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgsxmt IS '是否煤电公司项目';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zcgfw IS '采购范围';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zqztbr IS '潜在投标人及联系方式';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zgdzct IS '是否固定资产';
COMMENT ON COLUMN wbs_zmmrp226_parsed.ndjh_bh IS '年度采购计划编号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.znumber IS '年度计划行号';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zsaknr_item IS '行项目总账科目';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_syfx IS '使用方向';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_syfxms IS '使用方向描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_yslb IS '预算类别';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_yslbms IS '预算类别描述';
COMMENT ON COLUMN wbs_zmmrp226_parsed.z_dwbk IS '单位板块';
COMMENT ON COLUMN wbs_zmmrp226_parsed.zmemo_url IS 'URL备注';