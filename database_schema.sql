-- ============================================
-- UK Rail Delay Predictor Database Schema
-- Day 2: Database Design
-- Created: 2025-11-12
-- ============================================

-- 1. 车站表 (Stations)
CREATE TABLE IF NOT EXISTS stations (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_code VARCHAR(10) UNIQUE NOT NULL,  -- CRS代码 (如 PAD, KGX)
    station_name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    region VARCHAR(50),  -- 区域 (如 London, South East)
    zone INTEGER,  -- 伦敦交通分区
    is_active BOOLEAN DEFAULT 1,
    -- 扩展字段
    facilities TEXT,  -- JSON格式存储设施信息
    passenger_volume INTEGER,  -- 年客流量
    metro_area VARCHAR(50),  -- 都市圈
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 列车运营公司表 (Train Operating Companies)
CREATE TABLE IF NOT EXISTS train_operators (
    operator_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_code VARCHAR(10) UNIQUE NOT NULL,  -- 如 GWR, LNER
    operator_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200),
    website VARCHAR(200),
    is_active BOOLEAN DEFAULT 1,
    -- 扩展字段
    parent_company VARCHAR(100),
    franchise_start_date DATE,
    franchise_end_date DATE,
    service_quality_rating DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 列车类型表 (Train Types)
CREATE TABLE IF NOT EXISTS train_types (
    train_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_code VARCHAR(20) UNIQUE NOT NULL,  -- 如 CLASS_800, PENDOLINO
    type_name VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100),
    max_speed INTEGER,  -- km/h
    capacity INTEGER,  -- 座位数
    comfort_rating INTEGER,  -- 1-5星
    -- 扩展字段
    year_introduced INTEGER,
    power_type VARCHAR(50),  -- Electric, Diesel, Hybrid
    bi_mode BOOLEAN DEFAULT 0,
    wheelchair_spaces INTEGER,
    bike_spaces INTEGER,
    wifi_available BOOLEAN DEFAULT 0,
    power_sockets BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 路线表 (Routes)
CREATE TABLE IF NOT EXISTS routes (
    route_id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_code VARCHAR(20) UNIQUE NOT NULL,
    route_name VARCHAR(200) NOT NULL,
    origin_station_id INTEGER NOT NULL,
    destination_station_id INTEGER NOT NULL,
    distance_km DECIMAL(8, 2),
    typical_duration_minutes INTEGER,
    operator_id INTEGER,
    is_express BOOLEAN DEFAULT 0,  -- 是否快车
    -- 扩展字段
    scenic_rating INTEGER,  -- 风景评分 1-5
    difficulty_level INTEGER,  -- 复杂度 1-5
    main_line VARCHAR(100),  -- 主干线名称
    electrified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (origin_station_id) REFERENCES stations(station_id),
    FOREIGN KEY (destination_station_id) REFERENCES stations(station_id),
    FOREIGN KEY (operator_id) REFERENCES train_operators(operator_id)
);

-- 5. 车次表 (Services)
CREATE TABLE IF NOT EXISTS services (
    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_code VARCHAR(20) UNIQUE NOT NULL,  -- 如 1A23
    route_id INTEGER NOT NULL,
    operator_id INTEGER NOT NULL,
    train_type_id INTEGER,
    departure_time TIME NOT NULL,
    arrival_time TIME NOT NULL,
    scheduled_duration_minutes INTEGER,
    frequency VARCHAR(50),  -- 运行频率 (如 Daily, Weekdays)
    -- 扩展字段
    weekday_only BOOLEAN DEFAULT 0,
    saturday_service BOOLEAN DEFAULT 1,
    sunday_service BOOLEAN DEFAULT 1,
    bank_holiday_service BOOLEAN DEFAULT 0,
    reservation_required BOOLEAN DEFAULT 0,
    first_class_available BOOLEAN DEFAULT 1,
    catering_available BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES routes(route_id),
    FOREIGN KEY (operator_id) REFERENCES train_operators(operator_id),
    FOREIGN KEY (train_type_id) REFERENCES train_types(train_type_id)
);

-- 6. 车站停靠表 (Service Stops)
CREATE TABLE IF NOT EXISTS service_stops (
    stop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL,
    station_id INTEGER NOT NULL,
    stop_sequence INTEGER NOT NULL,  -- 停靠顺序
    arrival_time TIME,
    departure_time TIME,
    platform VARCHAR(10),
    dwell_time_minutes INTEGER,  -- 停站时间
    is_pickup BOOLEAN DEFAULT 1,  -- 是否上客
    is_dropoff BOOLEAN DEFAULT 1,  -- 是否下客
    -- 扩展字段
    typical_delay_minutes INTEGER,  -- 历史平均延误
    delay_risk_level INTEGER,  -- 延误风险等级 1-5
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(service_id),
    FOREIGN KEY (station_id) REFERENCES stations(station_id),
    UNIQUE(service_id, station_id, stop_sequence)
);

-- 7. 票价表 (Fares)
CREATE TABLE IF NOT EXISTS fares (
    fare_id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_station_id INTEGER NOT NULL,
    destination_station_id INTEGER NOT NULL,
    fare_type VARCHAR(50) NOT NULL,  -- Anytime, Off-Peak, Advance, Season
    ticket_class VARCHAR(20) NOT NULL,  -- Standard, First
    adult_fare DECIMAL(10, 2) NOT NULL,
    child_fare DECIMAL(10, 2),
    railcard_discount DECIMAL(5, 2),  -- 百分比折扣
    valid_from DATE,
    valid_to DATE,
    -- 扩展字段
    restrictions TEXT,  -- 使用限制
    refundable BOOLEAN DEFAULT 0,
    exchangeable BOOLEAN DEFAULT 0,
    route_restriction VARCHAR(200),  -- 路线限制
    operator_restriction INTEGER,  -- 限定运营商
    peak_time_surcharge DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (origin_station_id) REFERENCES stations(station_id),
    FOREIGN KEY (destination_station_id) REFERENCES stations(station_id),
    FOREIGN KEY (operator_restriction) REFERENCES train_operators(operator_id)
);

-- 8. 历史延误记录表 (Delay Records)
CREATE TABLE IF NOT EXISTS delay_records (
    delay_id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL,
    station_id INTEGER NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    actual_time TIMESTAMP,
    delay_minutes INTEGER,  -- 延误分钟数（负数表示早到）
    cancellation BOOLEAN DEFAULT 0,
    delay_reason VARCHAR(200),
    delay_category VARCHAR(50),  -- Weather, Technical, Staff, Passenger, etc.
    -- 扩展字段
    weather_condition VARCHAR(50),
    temperature DECIMAL(5, 2),
    precipitation DECIMAL(5, 2),
    wind_speed DECIMAL(5, 2),
    day_of_week INTEGER,  -- 1-7
    is_peak_hour BOOLEAN DEFAULT 0,
    is_holiday BOOLEAN DEFAULT 0,
    passenger_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(service_id),
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

-- 9. 天气数据表 (Weather Data)
CREATE TABLE IF NOT EXISTS weather_data (
    weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER NOT NULL,
    record_time TIMESTAMP NOT NULL,
    temperature DECIMAL(5, 2),  -- 摄氏度
    feels_like DECIMAL(5, 2),
    humidity INTEGER,  -- 百分比
    pressure DECIMAL(7, 2),  -- hPa
    wind_speed DECIMAL(5, 2),  -- km/h
    wind_direction INTEGER,  -- 度数
    precipitation DECIMAL(5, 2),  -- mm
    visibility INTEGER,  -- 米
    weather_condition VARCHAR(50),  -- Sunny, Rainy, Snowy, Foggy
    -- 扩展字段
    uv_index INTEGER,
    cloud_cover INTEGER,  -- 百分比
    dew_point DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

-- 10. 用户查询历史表 (Query History)
CREATE TABLE IF NOT EXISTS query_history (
    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(100),
    origin_station_id INTEGER,
    destination_station_id INTEGER,
    departure_date DATE,
    departure_time TIME,
    passengers INTEGER DEFAULT 1,
    railcard_type VARCHAR(50),
    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 扩展字段
    user_agent TEXT,
    ip_address VARCHAR(50),
    response_time_ms INTEGER,
    results_count INTEGER,
    FOREIGN KEY (origin_station_id) REFERENCES stations(station_id),
    FOREIGN KEY (destination_station_id) REFERENCES stations(station_id)
);

-- 11. 预测结果缓存表 (Prediction Cache)
CREATE TABLE IF NOT EXISTS prediction_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL,
    station_id INTEGER NOT NULL,
    prediction_date DATE NOT NULL,
    prediction_time TIME NOT NULL,
    predicted_delay_minutes INTEGER,
    confidence_score DECIMAL(5, 4),  -- 0-1之间
    model_version VARCHAR(50),
    features_used TEXT,  -- JSON格式
    -- 扩展字段
    weather_factor DECIMAL(5, 4),
    time_factor DECIMAL(5, 4),
    historical_factor DECIMAL(5, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (service_id) REFERENCES services(service_id),
    FOREIGN KEY (station_id) REFERENCES stations(station_id)
);

-- ============================================
-- 索引设计
-- ============================================

-- 车站索引
CREATE INDEX idx_stations_code ON stations(station_code);
CREATE INDEX idx_stations_name ON stations(station_name);
CREATE INDEX idx_stations_region ON stations(region);
CREATE INDEX idx_stations_location ON stations(latitude, longitude);

-- 路线索引
CREATE INDEX idx_routes_origin ON routes(origin_station_id);
CREATE INDEX idx_routes_destination ON routes(destination_station_id);
CREATE INDEX idx_routes_operator ON routes(operator_id);
CREATE INDEX idx_routes_origin_dest ON routes(origin_station_id, destination_station_id);

-- 车次索引
CREATE INDEX idx_services_route ON services(route_id);
CREATE INDEX idx_services_operator ON services(operator_id);
CREATE INDEX idx_services_departure ON services(departure_time);
CREATE INDEX idx_services_code ON services(service_code);

-- 停靠站索引
CREATE INDEX idx_stops_service ON service_stops(service_id);
CREATE INDEX idx_stops_station ON service_stops(station_id);
CREATE INDEX idx_stops_sequence ON service_stops(service_id, stop_sequence);

-- 票价索引
CREATE INDEX idx_fares_origin ON fares(origin_station_id);
CREATE INDEX idx_fares_destination ON fares(destination_station_id);
CREATE INDEX idx_fares_route ON fares(origin_station_id, destination_station_id);
CREATE INDEX idx_fares_type ON fares(fare_type);
CREATE INDEX idx_fares_validity ON fares(valid_from, valid_to);

-- 延误记录索引
CREATE INDEX idx_delays_service ON delay_records(service_id);
CREATE INDEX idx_delays_station ON delay_records(station_id);
CREATE INDEX idx_delays_time ON delay_records(scheduled_time);
CREATE INDEX idx_delays_category ON delay_records(delay_category);
CREATE INDEX idx_delays_date ON delay_records(scheduled_time, station_id);

-- 天气数据索引
CREATE INDEX idx_weather_station ON weather_data(station_id);
CREATE INDEX idx_weather_time ON weather_data(record_time);
CREATE INDEX idx_weather_station_time ON weather_data(station_id, record_time);

-- 查询历史索引
CREATE INDEX idx_query_session ON query_history(session_id);
CREATE INDEX idx_query_route ON query_history(origin_station_id, destination_station_id);
CREATE INDEX idx_query_timestamp ON query_history(search_timestamp);

-- 预测缓存索引
CREATE INDEX idx_cache_service ON prediction_cache(service_id);
CREATE INDEX idx_cache_station ON prediction_cache(station_id);
CREATE INDEX idx_cache_datetime ON prediction_cache(prediction_date, prediction_time);
CREATE INDEX idx_cache_expires ON prediction_cache(expires_at);

-- ============================================
-- 视图定义
-- ============================================

-- 热门路线视图
CREATE VIEW IF NOT EXISTS popular_routes AS
SELECT 
    r.route_id,
    r.route_name,
    s1.station_name AS origin_name,
    s2.station_name AS destination_name,
    COUNT(DISTINCT qh.query_id) AS search_count,
    AVG(dr.delay_minutes) AS avg_delay_minutes
FROM routes r
JOIN stations s1 ON r.origin_station_id = s1.station_id
JOIN stations s2 ON r.destination_station_id = s2.station_id
LEFT JOIN query_history qh ON (
    qh.origin_station_id = r.origin_station_id 
    AND qh.destination_station_id = r.destination_station_id
)
LEFT JOIN services svc ON svc.route_id = r.route_id
LEFT JOIN delay_records dr ON dr.service_id = svc.service_id
GROUP BY r.route_id, r.route_name, s1.station_name, s2.station_name;

-- 延误统计视图
CREATE VIEW IF NOT EXISTS delay_statistics AS
SELECT 
    s.service_code,
    s.operator_id,
    st.station_name,
    COUNT(dr.delay_id) AS total_delays,
    AVG(dr.delay_minutes) AS avg_delay,
    MAX(dr.delay_minutes) AS max_delay,
    SUM(CASE WHEN dr.cancellation = 1 THEN 1 ELSE 0 END) AS cancellations
FROM delay_records dr
JOIN services s ON dr.service_id = s.service_id
JOIN stations st ON dr.station_id = st.station_id
GROUP BY s.service_code, s.operator_id, st.station_name;

-- ============================================
-- 触发器 (更新时间戳)
-- ============================================

-- 车站更新触发器
CREATE TRIGGER IF NOT EXISTS update_stations_timestamp 
AFTER UPDATE ON stations
BEGIN
    UPDATE stations SET updated_at = CURRENT_TIMESTAMP 
    WHERE station_id = NEW.station_id;
END;

-- 运营商更新触发器
CREATE TRIGGER IF NOT EXISTS update_operators_timestamp 
AFTER UPDATE ON train_operators
BEGIN
    UPDATE train_operators SET updated_at = CURRENT_TIMESTAMP 
    WHERE operator_id = NEW.operator_id;
END;

-- 路线更新触发器
CREATE TRIGGER IF NOT EXISTS update_routes_timestamp 
AFTER UPDATE ON routes
BEGIN
    UPDATE routes SET updated_at = CURRENT_TIMESTAMP 
    WHERE route_id = NEW.route_id;
END;

-- 车次更新触发器
CREATE TRIGGER IF NOT EXISTS update_services_timestamp 
AFTER UPDATE ON services
BEGIN
    UPDATE services SET updated_at = CURRENT_TIMESTAMP 
    WHERE service_id = NEW.service_id;
END;

-- ============================================
-- 初始数据示例
-- ============================================

-- 插入示例车站
INSERT OR IGNORE INTO stations (station_code, station_name, latitude, longitude, region, zone) VALUES
('PAD', 'London Paddington', 51.5154, -0.1755, 'London', 1),
('KGX', 'London Kings Cross', 51.5308, -0.1238, 'London', 1),
('EUS', 'London Euston', 51.5282, -0.1337, 'London', 1),
('VIC', 'London Victoria', 51.4952, -0.1441, 'London', 1),
('LST', 'London Liverpool Street', 51.5179, -0.0813, 'London', 1),
('WAT', 'London Waterloo', 51.5031, -0.1132, 'London', 1),
('BRI', 'Bristol Temple Meads', 51.4490, -2.5813, 'South West', NULL),
('MAN', 'Manchester Piccadilly', 53.4776, -2.2309, 'North West', NULL),
('BHM', 'Birmingham New Street', 52.4777, -1.9004, 'West Midlands', NULL),
('EDN', 'Edinburgh Waverley', 55.9520, -3.1892, 'Scotland', NULL);

-- 插入示例运营商
INSERT OR IGNORE INTO train_operators (operator_code, operator_name, full_name) VALUES
('GWR', 'GWR', 'Great Western Railway'),
('LNER', 'LNER', 'London North Eastern Railway'),
('AWC', 'Avanti', 'Avanti West Coast'),
('SWR', 'SWR', 'South Western Railway'),
('SE', 'Southeastern', 'Southeastern Railway'),
('TL', 'Thameslink', 'Thameslink Railway');

-- ============================================
-- 数据完整性检查
-- ============================================

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- 设置WAL模式以提高并发性能
PRAGMA journal_mode = WAL;

-- 设置合理的缓存大小 (10MB)
PRAGMA cache_size = -10000;

-- ============================================
-- Schema创建完成
-- ============================================
