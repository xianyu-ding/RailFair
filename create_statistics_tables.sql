-- ============================================================================
-- RailFair Statistics Tables - Day 6
-- 统计预计算表，用于快速查询和预测模型
-- ============================================================================

-- 1. 路线统计汇总表 (核心缓存表)
-- ============================================================================
CREATE TABLE IF NOT EXISTS route_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 路线标识
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    route_name TEXT,  -- 例如: "EUS-MAN"
    
    -- 统计时间范围
    calculation_date DATE NOT NULL,  -- 统计计算日期
    data_start_date DATE,            -- 数据起始日期
    data_end_date DATE,              -- 数据结束日期
    data_days_count INTEGER,         -- 数据天数
    
    -- 服务统计
    total_services INTEGER DEFAULT 0,      -- 总服务次数
    total_records INTEGER DEFAULT 0,       -- 总记录数
    weekday_services INTEGER DEFAULT 0,    -- 工作日服务
    weekend_services INTEGER DEFAULT 0,    -- 周末服务
    
    -- 准点率指标 (ORR标准)
    on_time_count INTEGER DEFAULT 0,       -- ≤1分钟
    on_time_percentage REAL,               -- 准点率 (≤1 min)
    time_to_3_percentage REAL,             -- ≤3分钟比例
    time_to_5_percentage REAL,             -- ≤5分钟比例 (PPM-5)
    time_to_10_percentage REAL,            -- ≤10分钟比例 (PPM-10)
    time_to_15_percentage REAL,            -- ≤15分钟比例
    time_to_30_percentage REAL,            -- ≤30分钟比例
    
    -- 延误统计
    avg_delay_minutes REAL,                -- 平均延误(分钟)
    median_delay_minutes REAL,             -- 中位数延误
    max_delay_minutes INTEGER,             -- 最大延误
    std_delay_minutes REAL,                -- 延误标准差
    
    -- 延误分布
    delays_0_5_count INTEGER DEFAULT 0,    -- 0-5分钟
    delays_5_15_count INTEGER DEFAULT 0,   -- 5-15分钟
    delays_15_30_count INTEGER DEFAULT 0,  -- 15-30分钟
    delays_30_60_count INTEGER DEFAULT 0,  -- 30-60分钟
    delays_60_plus_count INTEGER DEFAULT 0, -- >60分钟
    
    -- 取消和严重延误
    cancelled_count INTEGER DEFAULT 0,     -- 取消数量
    cancelled_percentage REAL,             -- 取消率
    severe_delay_count INTEGER DEFAULT 0,  -- 严重延误(>60min)
    
    -- 可靠性评级
    reliability_score REAL,                -- 0-100可靠性分数
    reliability_grade TEXT,                -- A/B/C/D/F 评级
    
    -- 时段统计 (JSON格式存储详细数据)
    hourly_stats TEXT,                     -- 按小时统计
    day_of_week_stats TEXT,                -- 按星期统计
    
    -- 元数据
    sample_size INTEGER,                   -- 样本大小
    data_quality_score REAL,               -- 数据质量分数
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束：每条路线每天只能有一条统计记录
    UNIQUE(origin, destination, calculation_date)
);

-- 2. TOC运营商统计表
-- ============================================================================
CREATE TABLE IF NOT EXISTS toc_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- TOC标识
    toc_code TEXT NOT NULL,
    toc_name TEXT,
    
    -- 统计时间范围
    calculation_date DATE NOT NULL,
    data_start_date DATE,
    data_end_date DATE,
    data_days_count INTEGER,
    
    -- 服务统计
    total_services INTEGER DEFAULT 0,
    total_routes_served INTEGER DEFAULT 0,
    
    -- 准点率
    on_time_percentage REAL,
    ppm_5_percentage REAL,    -- PPM-5
    ppm_10_percentage REAL,   -- PPM-10
    
    -- 延误统计
    avg_delay_minutes REAL,
    median_delay_minutes REAL,
    
    -- 取消率
    cancelled_percentage REAL,
    
    -- 可靠性评级
    reliability_score REAL,
    reliability_grade TEXT,
    
    -- 路线详情 (JSON)
    route_performance TEXT,   -- 每条路线的性能
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(toc_code, calculation_date)
);

-- 3. 时段性能统计 (用于预测不同时段的延误概率)
-- ============================================================================
CREATE TABLE IF NOT EXISTS time_slot_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 路线和时段
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    hour_of_day INTEGER NOT NULL,        -- 0-23
    day_of_week INTEGER,                 -- 0=Monday, 6=Sunday, NULL=所有
    
    -- 统计范围
    calculation_date DATE NOT NULL,
    data_start_date DATE,
    data_end_date DATE,
    
    -- 服务统计
    service_count INTEGER DEFAULT 0,
    
    -- 准点率
    on_time_percentage REAL,
    ppm_5_percentage REAL,
    
    -- 延误统计
    avg_delay_minutes REAL,
    median_delay_minutes REAL,
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(origin, destination, hour_of_day, day_of_week, calculation_date)
);

-- 4. 预测缓存表 (存储常见查询的预测结果)
-- ============================================================================
-- 注意: 如果旧的prediction_cache表存在(来自Day 2 schema)，需要先删除
-- 因为新表使用不同的schema (cache_key vs cache_id)
DROP TABLE IF EXISTS prediction_cache;

CREATE TABLE IF NOT EXISTS prediction_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 查询参数 (哈希作为缓存键)
    cache_key TEXT NOT NULL UNIQUE,  -- MD5(origin+dest+date+time)
    
    -- 路线信息
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    departure_time TIME NOT NULL,
    
    -- 预测结果
    predicted_delay_minutes REAL,
    on_time_probability REAL,       -- 准点概率
    delay_5_probability REAL,       -- ≤5分钟概率
    delay_15_probability REAL,      -- ≤15分钟概率
    severe_delay_probability REAL,  -- >30分钟概率
    
    -- 置信度
    confidence_level TEXT,           -- high/medium/low
    confidence_score REAL,           -- 0-1
    
    -- 推荐
    recommendation TEXT,             -- earlier/later/this_train/alternative
    alternative_suggestions TEXT,    -- JSON格式的替代方案
    
    -- 缓存元数据
    model_version TEXT,              -- 使用的模型版本
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,            -- 缓存过期时间
    hit_count INTEGER DEFAULT 0,     -- 缓存命中次数
    
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 数据质量监控表
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    metric_date DATE NOT NULL,
    
    -- 数据完整性
    total_records INTEGER,
    null_departure_count INTEGER,
    null_arrival_count INTEGER,
    null_delay_count INTEGER,
    
    -- 数据准确性
    extreme_delay_count INTEGER,     -- >180分钟
    negative_delay_count INTEGER,    -- 负延误（到早了）
    time_inconsistency_count INTEGER, -- 时间逻辑错误
    
    -- 覆盖率
    routes_with_data INTEGER,
    tocs_with_data INTEGER,
    days_with_data INTEGER,
    
    -- 质量分数
    overall_quality_score REAL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(metric_date)
);

-- ============================================================================
-- 索引优化 (提升查询性能)
-- ============================================================================

-- route_statistics 索引
CREATE INDEX IF NOT EXISTS idx_route_stats_route 
    ON route_statistics(origin, destination);
CREATE INDEX IF NOT EXISTS idx_route_stats_date 
    ON route_statistics(calculation_date);
CREATE INDEX IF NOT EXISTS idx_route_stats_reliability 
    ON route_statistics(reliability_score DESC);

-- toc_statistics 索引
CREATE INDEX IF NOT EXISTS idx_toc_stats_code 
    ON toc_statistics(toc_code);
CREATE INDEX IF NOT EXISTS idx_toc_stats_date 
    ON toc_statistics(calculation_date);

-- time_slot_statistics 索引
CREATE INDEX IF NOT EXISTS idx_timeslot_route 
    ON time_slot_statistics(origin, destination, hour_of_day);
CREATE INDEX IF NOT EXISTS idx_timeslot_dow 
    ON time_slot_statistics(day_of_week);

-- prediction_cache 索引
CREATE INDEX IF NOT EXISTS idx_cache_key 
    ON prediction_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_route_date 
    ON prediction_cache(origin, destination, departure_date);
CREATE INDEX IF NOT EXISTS idx_cache_expires 
    ON prediction_cache(expires_at);

-- ============================================================================
-- 视图：最新统计快速查询
-- ============================================================================

-- 最新路线统计 (先删除旧视图，再创建新视图)
DROP VIEW IF EXISTS v_latest_route_stats;
CREATE VIEW v_latest_route_stats AS
SELECT 
    origin,
    destination,
    route_name,
    on_time_percentage,
    time_to_5_percentage AS ppm_5,
    time_to_10_percentage AS ppm_10,
    avg_delay_minutes,
    reliability_score,
    reliability_grade,
    total_services,
    calculation_date,
    last_updated
FROM route_statistics
WHERE calculation_date = (
    SELECT MAX(calculation_date) 
    FROM route_statistics rs2 
    WHERE rs2.origin = route_statistics.origin 
      AND rs2.destination = route_statistics.destination
)
ORDER BY reliability_score DESC;

-- 最新TOC统计 (先删除旧视图，再创建新视图)
DROP VIEW IF EXISTS v_latest_toc_stats;
CREATE VIEW v_latest_toc_stats AS
SELECT 
    toc_code,
    toc_name,
    on_time_percentage,
    ppm_5_percentage AS ppm_5,
    ppm_10_percentage AS ppm_10,
    cancelled_percentage,
    reliability_score,
    reliability_grade,
    total_services,
    calculation_date
FROM toc_statistics
WHERE calculation_date = (
    SELECT MAX(calculation_date) 
    FROM toc_statistics ts2 
    WHERE ts2.toc_code = toc_statistics.toc_code
)
ORDER BY reliability_score DESC;

-- ============================================================================
-- 触发器：自动更新时间戳
-- ============================================================================

CREATE TRIGGER IF NOT EXISTS update_route_stats_timestamp 
    AFTER UPDATE ON route_statistics
BEGIN
    UPDATE route_statistics 
    SET last_updated = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_cache_access_time
    AFTER UPDATE ON prediction_cache
BEGIN
    UPDATE prediction_cache 
    SET last_accessed = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- ============================================================================
-- 初始化完成
-- ============================================================================

-- 插入一条测试记录验证表结构
INSERT OR IGNORE INTO data_quality_metrics (
    metric_date,
    total_records,
    overall_quality_score
) VALUES (
    date('now'),
    0,
    0.0
);

SELECT '✅ Statistics tables created successfully' AS status;
