-- =====================================================================
-- 一次性迁移脚本：快照表从「每日」升级为「每小时历史快照」
-- =====================================================================
-- 用途：
--   本次改动了表结构（新增 snapshot_time 字段、唯一键从 snapshot_date 改为
--   snapshot_time）。旧的每日快照表结构不兼容新代码，必须先 DROP 旧表，
--   再由 bi_snapshot.py 的 ensure_tables() 按新结构重建。
--
-- 执行方式（只需手动执行一次，在目标库 10.239.192.131 bi_snapshot 上）：
--   psql -h 10.239.192.131 -p 54321 -U garden_wms -d bi_snapshot -f 06_migrate_snapshot_to_hourly.sql
--
-- ⚠️ 注意：本脚本会删除旧表及其历史数据（每日快照数据）。
--   如需保留旧数据，请先自行备份后执行。
-- =====================================================================

DROP TABLE IF EXISTS bi_kpi_summary          CASCADE;
DROP TABLE IF EXISTS bi_claim_indicators     CASCADE;
DROP TABLE IF EXISTS bi_structure_indicators CASCADE;
DROP TABLE IF EXISTS bi_age_indicators       CASCADE;
DROP TABLE IF EXISTS bi_dimension_project    CASCADE;
DROP TABLE IF EXISTS bi_dimension_purchaser  CASCADE;
DROP TABLE IF EXISTS bi_top_ranking          CASCADE;
DROP TABLE IF EXISTS bi_time_series          CASCADE;
DROP TABLE IF EXISTS bi_batch_digest         CASCADE;
DROP TABLE IF EXISTS bi_anomaly_detection    CASCADE;
DROP TABLE IF EXISTS bi_kpi_checklist        CASCADE;
DROP TABLE IF EXISTS bi_safety_stock         CASCADE;
DROP TABLE IF EXISTS bi_inventory_report     CASCADE;
DROP TABLE IF EXISTS bi_category_bubble      CASCADE;
DROP TABLE IF EXISTS bi_age_heatmap          CASCADE;
DROP TABLE IF EXISTS bi_optimize_suggest     CASCADE;
DROP TABLE IF EXISTS bi_source_structure     CASCADE;
