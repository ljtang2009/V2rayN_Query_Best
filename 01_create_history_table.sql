-- ============================================
-- 1. 创建延迟测试历史记录表
-- ============================================

CREATE TABLE IF NOT EXISTS ProfileExItemHistory (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    IndexId TEXT NOT NULL,
    Delay INTEGER NOT NULL,
    TestTime TEXT NOT NULL,
    Success INTEGER NOT NULL
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_history_indexid ON ProfileExItemHistory(IndexId);
CREATE INDEX IF NOT EXISTS idx_history_testtime ON ProfileExItemHistory(TestTime);

-- ============================================
-- 说明：
-- - IndexId: 节点ID，对应 ProfileItem.IndexId
-- - Delay: 延迟值（毫秒），0表示测试失败
-- - TestTime: 测试时间，格式为 'YYYY-MM-DD HH:MM:SS'
-- - Success: 是否成功，1=成功（Delay>0），0=失败（Delay=0）
-- ============================================