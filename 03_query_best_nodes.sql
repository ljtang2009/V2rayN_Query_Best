-- ============================================
-- 3. 查询优秀节点（基于历史延迟和稳定性）
-- ============================================
-- 使用方法：在 DBeaver 中执行此脚本，查询出优秀的节点
-- 然后在 v2rayN 界面中搜索这些节点的 IndexId 或备注名称

-- ============================================
-- 查询1：基础统计信息（所有节点）
-- ============================================
-- 显示每个节点的测试次数、成功次数、成功率、平均延迟等
SELECT
    h.IndexId,
    pi.Remarks AS NodeName,
    pi.Address,
    pi.Port,
    COUNT(*) AS TotalTests,
    SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) AS SuccessfulTests,
    ROUND(SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS SuccessRate,
    ROUND(AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END), 0) AS AvgDelay,
    MIN(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MinDelay,
    MAX(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MaxDelay,
    MAX(h.TestTime) AS LastTestTime
FROM ProfileExItemHistory h
INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
GROUP BY h.IndexId, pi.Remarks, pi.Address, pi.Port
ORDER BY SuccessRate DESC, AvgDelay ASC;

-- ============================================
-- 查询2：优秀节点（综合评分）
-- ============================================
-- 综合评分 = 成功率 * 60 + (1 - 标准化延迟) * 40
-- 标准化延迟 = (延迟 - 最小延迟) / (最大延迟 - 最小延迟)
-- 延迟越低、成功率越高，综合评分越高

WITH NodeStats AS (
    SELECT
        h.IndexId,
        pi.Remarks AS NodeName,
        pi.Address,
        pi.Port,
        COUNT(*) AS TotalTests,
        SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) AS SuccessfulTests,
        ROUND(SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS SuccessRate,
        ROUND(AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END), 0) AS AvgDelay,
        MIN(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MinDelay,
        MAX(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MaxDelay,
        MAX(h.TestTime) AS LastTestTime,
        -- 计算延迟方差
        ROUND(
            AVG(CASE WHEN h.Success = 1 THEN h.Delay * h.Delay ELSE NULL END) -
            AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) *
            AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END),
            0
        ) AS Variance
    FROM ProfileExItemHistory h
    INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
    GROUP BY h.IndexId, pi.Remarks, pi.Address, pi.Port
    HAVING COUNT(*) >= 3  -- 至少测试3次
),
DelayRange AS (
    SELECT
        MIN(AvgDelay) AS MinAvgDelay,
        MAX(AvgDelay) AS MaxAvgDelay
    FROM NodeStats
    WHERE AvgDelay IS NOT NULL
)
SELECT
    ns.IndexId,
    ns.NodeName,
    ns.Address,
    ns.Port,
    ns.TotalTests,
    ns.SuccessfulTests,
    ns.SuccessRate,
    ns.AvgDelay,
    ns.MinDelay,
    ns.MaxDelay,
    ns.LastTestTime,
    -- 计算稳定性评分（基于方差）
    ROUND(
        ns.SuccessRate * 60 +
        CASE
            WHEN dr.MinAvgDelay = dr.MaxAvgDelay THEN 40
            ELSE 40 * (1 - (ns.AvgDelay - dr.MinAvgDelay) * 1.0 / (dr.MaxAvgDelay - dr.MinAvgDelay))
        END,
        2
    ) AS StabilityScore,
    -- 计算综合评分
    ROUND(
        ns.SuccessRate * 60 +
        CASE
            WHEN dr.MinAvgDelay = dr.MaxAvgDelay THEN 40
            ELSE 40 * (1 - (ns.AvgDelay - dr.MinAvgDelay) * 1.0 / (dr.MaxAvgDelay - dr.MinAvgDelay))
        END -
        CASE
            WHEN ns.Variance < 1000 THEN 0
            WHEN ns.Variance < 5000 THEN 5
            WHEN ns.Variance < 10000 THEN 10
            ELSE 20
        END,
        2
    ) AS OverallScore
FROM NodeStats ns, DelayRange dr
WHERE ns.SuccessRate >= 50  -- 成功率至少50%
ORDER BY OverallScore DESC, ns.AvgDelay ASC
LIMIT 20;  -- 返回前20个优秀节点

-- ============================================
-- 查询3：按成功率排序的节点
-- ============================================
SELECT
    h.IndexId,
    pi.Remarks AS NodeName,
    pi.Address,
    pi.Port,
    COUNT(*) AS TotalTests,
    SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) AS SuccessfulTests,
    ROUND(SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS SuccessRate,
    ROUND(AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END), 0) AS AvgDelay,
    MAX(h.TestTime) AS LastTestTime
FROM ProfileExItemHistory h
INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
GROUP BY h.IndexId, pi.Remarks, pi.Address, pi.Port
HAVING COUNT(*) >= 3  -- 至少测试3次
ORDER BY SuccessRate DESC, AvgDelay ASC;

-- ============================================
-- 查询4：低延迟节点（平均延迟 < 200ms）
-- ============================================
SELECT
    h.IndexId,
    pi.Remarks AS NodeName,
    pi.Address,
    pi.Port,
    COUNT(*) AS TotalTests,
    SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) AS SuccessfulTests,
    ROUND(SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS SuccessRate,
    ROUND(AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END), 0) AS AvgDelay,
    MIN(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MinDelay,
    MAX(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MaxDelay,
    MAX(h.TestTime) AS LastTestTime
FROM ProfileExItemHistory h
INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
GROUP BY h.IndexId, pi.Remarks, pi.Address, pi.Port
HAVING COUNT(*) >= 3
  AND AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) < 200
  AND SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) >= 60
ORDER BY AvgDelay ASC;

-- ============================================
-- 查询5：稳定节点（成功率 >= 80% 且至少测试5次）
-- ============================================
SELECT
    h.IndexId,
    pi.Remarks AS NodeName,
    pi.Address,
    pi.Port,
    COUNT(*) AS TotalTests,
    SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) AS SuccessfulTests,
    ROUND(SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS SuccessRate,
    ROUND(AVG(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END), 0) AS AvgDelay,
    MIN(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MinDelay,
    MAX(CASE WHEN h.Success = 1 THEN h.Delay ELSE NULL END) AS MaxDelay,
    MAX(h.TestTime) AS LastTestTime
FROM ProfileExItemHistory h
INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
GROUP BY h.IndexId, pi.Remarks, pi.Address, pi.Port
HAVING COUNT(*) >= 5
  AND SUM(CASE WHEN h.Success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) >= 80
ORDER BY SuccessRate DESC, AvgDelay ASC;

-- ============================================
-- 查询6：查看指定节点的详细历史记录
-- ============================================
-- 替换 'your_index_id' 为实际的节点ID
-- SELECT
--     h.*,
--     pi.Remarks AS NodeName
-- FROM ProfileExItemHistory h
-- INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
-- WHERE h.IndexId = 'your_index_id'
-- ORDER BY h.TestTime DESC;

-- ============================================
-- 查询7：最近测试的节点（按时间排序）
-- ============================================
SELECT
    h.IndexId,
    pi.Remarks AS NodeName,
    h.Delay,
    h.TestTime,
    CASE WHEN h.Success = 1 THEN '成功' ELSE '失败' END AS Status
FROM ProfileExItemHistory h
INNER JOIN ProfileItem pi ON h.IndexId = pi.IndexId
ORDER BY h.TestTime DESC
LIMIT 50;

-- ============================================
-- 使用步骤：
-- 1. 先执行查询1，查看所有节点的基础统计信息
-- 2. 根据需要选择查询2-7中的某个查询
-- 3. 将查询结果中的 IndexId 或 NodeName 复制
-- 4. 在 v2rayN 界面中搜索这些节点
-- 5. 选择综合评分高、延迟低、稳定性好的节点使用
--
-- 注意：历史记录清理请使用 04_cleanup_history.sql
-- ============================================