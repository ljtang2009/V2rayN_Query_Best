-- ============================================
-- 4. 清理 ProfileExItemHistory 历史记录表
-- ============================================
-- 使用方法：定期执行此脚本，清理不需要的历史记录

-- ============================================
-- 清理1：删除不存在于 ProfileItem 中的节点历史记录（推荐）
-- ============================================
-- 当节点从 ProfileItem 表中删除时，同步删除对应的历史记录
DELETE FROM ProfileExItemHistory
WHERE IndexId NOT IN (SELECT IndexId FROM ProfileItem);

-- 查看删除了多少条记录
-- SELECT changes() AS deleted_count;

-- ============================================
-- 清理2：删除指定时间之前的旧记录
-- ============================================
-- 例如：删除30天之前的记录
-- DELETE FROM ProfileExItemHistory
-- WHERE TestTime < datetime('now', 'localtime', '-30 days');

-- 例如：删除7天之前的记录
-- DELETE FROM ProfileExItemHistory
-- WHERE TestTime < datetime('now', 'localtime', '-7 days');

-- ============================================
-- 清理3：限制每个节点保留最近N条记录
-- ============================================
-- 例如：每个节点只保留最近20条记录
-- 注意：SQLite 不支持直接在 DELETE 中使用 LIMIT 和子查询，
-- 需要使用更复杂的方式

-- 方式A：使用临时表（推荐）
-- CREATE TEMP TABLE temp_keep_ids AS
-- SELECT Id
-- FROM (
--     SELECT
--         Id,
--         IndexId,
--         ROW_NUMBER() OVER (PARTITION BY IndexId ORDER BY TestTime DESC) AS rn
--     FROM ProfileExItemHistory
-- )
-- WHERE rn <= 20;
--
-- DELETE FROM ProfileExItemHistory
-- WHERE Id NOT IN (SELECT Id FROM temp_keep_ids);
--
-- DROP TABLE temp_keep_ids;

-- 方式B：使用 NOT IN 子查询（较慢，但简单）
-- DELETE FROM ProfileExItemHistory
-- WHERE Id NOT IN (
--     SELECT Id FROM (
--         SELECT Id,
--                ROW_NUMBER() OVER (PARTITION BY IndexId ORDER BY TestTime DESC) AS rn
--         FROM ProfileExItemHistory
--     )
--     WHERE rn <= 20
-- );

-- ============================================
-- 清理4：删除测试失败的记录（Delay = 0）
-- ============================================
-- DELETE FROM ProfileExItemHistory
-- WHERE Delay = 0;

-- ============================================
-- 清理5：删除测试次数过少的节点历史记录
-- ============================================
-- 例如：删除测试次数少于3次的节点历史记录
-- DELETE FROM ProfileExItemHistory
-- WHERE IndexId IN (
--     SELECT IndexId
--     FROM ProfileExItemHistory
--     GROUP BY IndexId
--     HAVING COUNT(*) < 3
-- );

-- ============================================
-- 清理6：删除重复的测试记录（同一节点同一时间）
-- ============================================
-- 保留最新的记录，删除重复的
-- DELETE FROM ProfileExItemHistory
-- WHERE Id NOT IN (
--     SELECT MAX(Id)
--     FROM ProfileExItemHistory
--     GROUP BY IndexId, TestTime
-- );

-- ============================================
-- 清理7：组合清理（推荐定期执行）
-- ============================================
-- 执行以下清理操作：
-- 1. 删除不存在的节点历史记录
-- 2. 删除30天前的旧记录
-- 3. 每个节点只保留最近20条记录

-- 步骤1：删除不存在的节点历史记录
-- DELETE FROM ProfileExItemHistory
-- WHERE IndexId NOT IN (SELECT IndexId FROM ProfileItem);

-- 步骤2：删除30天前的旧记录
-- DELETE FROM ProfileExItemHistory
-- WHERE TestTime < datetime('now', 'localtime', '-30 days');

-- 步骤3：每个节点只保留最近20条记录
-- CREATE TEMP TABLE temp_keep_ids AS
-- SELECT Id
-- FROM (
--     SELECT
--         Id,
--         IndexId,
--         ROW_NUMBER() OVER (PARTITION BY IndexId ORDER BY TestTime DESC) AS rn
--     FROM ProfileExItemHistory
-- )
-- WHERE rn <= 20;
--
-- DELETE FROM ProfileExItemHistory
-- WHERE Id NOT IN (SELECT Id FROM temp_keep_ids);
--
-- DROP TABLE temp_keep_ids;

-- ============================================
-- 查询：查看清理前的统计信息
-- ============================================
-- 查看历史记录总数
-- SELECT COUNT(*) AS total_records FROM ProfileExItemHistory;

-- 查看有多少个节点有历史记录
-- SELECT COUNT(DISTINCT IndexId) AS nodes_with_history FROM ProfileExItemHistory;

-- 查看每个节点的历史记录数量
-- SELECT
--     IndexId,
--     COUNT(*) AS record_count,
--     MIN(TestTime) AS earliest_test,
--     MAX(TestTime) AS latest_test
-- FROM ProfileExItemHistory
-- GROUP BY IndexId
-- ORDER BY record_count DESC;

-- 查看不存在于 ProfileItem 中的节点历史记录
-- SELECT
--     h.IndexId,
--     COUNT(*) AS record_count,
--     MIN(h.TestTime) AS earliest_test,
--     MAX(h.TestTime) AS latest_test
-- FROM ProfileExItemHistory h
-- WHERE h.IndexId NOT IN (SELECT IndexId FROM ProfileItem)
-- GROUP BY h.IndexId;

-- 查看指定时间范围内的记录数量
-- SELECT
--     CASE
--         WHEN TestTime >= datetime('now', 'localtime', '-7 days') THEN '最近7天'
--         WHEN TestTime >= datetime('now', 'localtime', '-30 days') THEN '7-30天'
--         ELSE '30天前'
--     END AS time_range,
--     COUNT(*) AS record_count
-- FROM ProfileExItemHistory
-- GROUP BY time_range;

-- ============================================
-- 使用步骤：
-- 1. 先执行查询语句，查看当前历史记录的统计信息
-- 2. 根据需要选择合适的清理方式（清理1-7）
-- 3. 取消注释（删除 --）要执行的清理语句
-- 4. 执行清理语句
-- 5. 再次执行查询语句，确认清理结果
--
-- 推荐清理策略：
-- - 每次订阅更新后，执行清理1（删除不存在的节点）
-- - 每周执行一次清理7（组合清理）
-- - 根据实际需求调整保留天数和记录数量
-- ============================================