-- ============================================
-- 2. 保存当前测试结果到历史记录表
-- ============================================
-- 使用方法：在 v2rayN 中对所有节点执行"测试真连接延迟"后，
-- 在 DBeaver 中执行此脚本，将当前测试结果保存到历史记录表

-- 方式1：保存所有节点的当前测试结果（推荐）
INSERT INTO ProfileExItemHistory (IndexId, Delay, TestTime, Success)
SELECT
    IndexId,
    Delay,
    datetime('now', 'localtime') AS TestTime,
    CASE WHEN Delay > 0 THEN 1 ELSE 0 END AS Success
FROM ProfileExItem
WHERE IndexId IN (SELECT IndexId FROM ProfileItem);

-- ============================================
-- 方式2：只保存测试成功的节点（Delay > 0）
-- ============================================
-- INSERT INTO ProfileExItemHistory (IndexId, Delay, TestTime, Success)
-- SELECT
--     IndexId,
--     Delay,
--     datetime('now', 'localtime') AS TestTime,
--     1 AS Success
-- FROM ProfileExItem
-- WHERE Delay > 0
--   AND IndexId IN (SELECT IndexId FROM ProfileItem);

-- ============================================
-- 方式3：只保存指定订阅的节点
-- ============================================
-- INSERT INTO ProfileExItemHistory (IndexId, Delay, TestTime, Success)
-- SELECT
--     p.IndexId,
--     p.Delay,
--     datetime('now', 'localtime') AS TestTime,
--     CASE WHEN p.Delay > 0 THEN 1 ELSE 0 END AS Success
-- FROM ProfileExItem p
-- INNER JOIN ProfileItem pi ON p.IndexId = pi.IndexId
-- WHERE pi.Subid = '你的订阅ID';

-- ============================================
-- 使用步骤：
-- 1. 在 v2rayN 中对所有节点执行"测试真连接延迟"
-- 2. 在 DBeaver 中打开此脚本
-- 3. 选择适合的方式（方式1/2/3），注释掉不需要的方式
-- 4. 执行脚本
-- 5. 可以多次执行，每次测试后都保存一次，建立历史记录
--
-- 注意：
-- - 使用 datetime('now', 'localtime') 自动获取当前时间，无需手动替换
-- - 时间格式为：YYYY-MM-DD HH:MM:SS
-- ============================================
