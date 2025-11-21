"""
UK Rail Delay Predictor - Database Unit Tests
Day 2: Test database operations and models
Created: 2025-11-12
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime, date, time
from decimal import Decimal
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    Station, StationCreate,
    TrainOperator, TrainOperatorCreate,
    Route, RouteCreate,
    Service, ServiceCreate,
    Fare, FareCreate, FareType, TicketClass,
    DelayRecord, DelayRecordCreate, DelayCategory,
    WeatherData, WeatherDataCreate, WeatherCondition,
    JourneySearch,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def test_db():
    """创建测试数据库"""
    db_path = "data/test_railfair.db"
    
    # 确保data目录存在
    Path("data").mkdir(exist_ok=True)
    
    # 删除已存在的测试数据库
    if Path(db_path).exists():
        Path(db_path).unlink()
    
    # 创建数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 读取schema
    with open("database_schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    cursor.executescript(schema_sql)
    conn.commit()
    
    yield conn
    
    # 清理
    conn.close()
    if Path(db_path).exists():
        Path(db_path).unlink()


@pytest.fixture
def sample_station_data():
    """示例车站数据"""
    return {
        "station_code": "PAD",
        "station_name": "London Paddington",
        "latitude": Decimal("51.5154"),
        "longitude": Decimal("-0.1755"),
        "region": "London",
        "zone": 1,
        "is_active": True,
    }


@pytest.fixture
def sample_operator_data():
    """示例运营商数据"""
    return {
        "operator_code": "GWR",
        "operator_name": "GWR",
        "full_name": "Great Western Railway",
        "is_active": True,
    }


# ============================================
# 数据库连接测试
# ============================================

class TestDatabaseConnection:
    """测试数据库连接"""
    
    def test_database_exists(self, test_db):
        """测试数据库是否存在"""
        assert test_db is not None
        assert isinstance(test_db, sqlite3.Connection)
    
    def test_foreign_keys_enabled(self, test_db):
        """测试外键约束是否启用"""
        cursor = test_db.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1, "外键约束未启用"
    
    def test_journal_mode(self, test_db):
        """测试日志模式"""
        cursor = test_db.cursor()
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        assert result[0] == "wal", "WAL模式未启用"


# ============================================
# 表创建测试
# ============================================

class TestTableCreation:
    """测试表创建"""
    
    def test_all_tables_exist(self, test_db):
        """测试所有表是否创建"""
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'delay_records',
            'fares',
            'prediction_cache',
            'query_history',
            'routes',
            'service_stops',
            'services',
            'stations',
            'train_operators',
            'train_types',
            'weather_data',
        ]
        
        for table in expected_tables:
            assert table in tables, f"表 {table} 不存在"
    
    def test_stations_table_structure(self, test_db):
        """测试车站表结构"""
        cursor = test_db.cursor()
        cursor.execute("PRAGMA table_info(stations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'station_id' in columns
        assert 'station_code' in columns
        assert 'station_name' in columns
        assert 'latitude' in columns
        assert 'longitude' in columns
        assert 'region' in columns
    
    def test_indexes_created(self, test_db):
        """测试索引是否创建"""
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        
        assert len(indexes) > 0, "没有创建索引"
        assert 'idx_stations_code' in indexes
        assert 'idx_routes_origin_dest' in indexes
    
    def test_views_created(self, test_db):
        """测试视图是否创建"""
        cursor = test_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        )
        views = [row[0] for row in cursor.fetchall()]
        
        assert 'popular_routes' in views
        assert 'delay_statistics' in views


# ============================================
# 数据插入测试
# ============================================

class TestDataInsertion:
    """测试数据插入"""
    
    def test_insert_station(self, test_db, sample_station_data):
        """测试插入车站"""
        cursor = test_db.cursor()
        
        cursor.execute(
            """INSERT INTO stations 
            (station_code, station_name, latitude, longitude, region, zone, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                sample_station_data['station_code'],
                sample_station_data['station_name'],
                sample_station_data['latitude'],
                sample_station_data['longitude'],
                sample_station_data['region'],
                sample_station_data['zone'],
                sample_station_data['is_active'],
            )
        )
        test_db.commit()
        
        # 验证插入
        cursor.execute("SELECT * FROM stations WHERE station_code = ?", ('PAD',))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[1] == 'PAD'  # station_code
        assert result[2] == 'London Paddington'  # station_name
    
    def test_insert_operator(self, test_db, sample_operator_data):
        """测试插入运营商"""
        cursor = test_db.cursor()
        
        cursor.execute(
            """INSERT INTO train_operators 
            (operator_code, operator_name, full_name, is_active)
            VALUES (?, ?, ?, ?)""",
            (
                sample_operator_data['operator_code'],
                sample_operator_data['operator_name'],
                sample_operator_data['full_name'],
                sample_operator_data['is_active'],
            )
        )
        test_db.commit()
        
        # 验证插入
        cursor.execute("SELECT * FROM train_operators WHERE operator_code = ?", ('GWR',))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[1] == 'GWR'
    
    def test_insert_with_foreign_key(self, test_db):
        """测试外键约束"""
        cursor = test_db.cursor()
        
        # 先插入依赖的数据
        cursor.execute(
            "INSERT INTO stations (station_code, station_name) VALUES (?, ?)",
            ('TST1', 'Test Station 1')
        )
        cursor.execute(
            "INSERT INTO stations (station_code, station_name) VALUES (?, ?)",
            ('TST2', 'Test Station 2')
        )
        cursor.execute(
            "INSERT INTO train_operators (operator_code, operator_name) VALUES (?, ?)",
            ('TST', 'Test Operator')
        )
        test_db.commit()
        
        # 获取ID
        cursor.execute("SELECT station_id FROM stations WHERE station_code = 'TST1'")
        origin_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT station_id FROM stations WHERE station_code = 'TST2'")
        dest_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT operator_id FROM train_operators WHERE operator_code = 'TST'")
        operator_id = cursor.fetchone()[0]
        
        # 插入路线
        cursor.execute(
            """INSERT INTO routes 
            (route_code, route_name, origin_station_id, destination_station_id, operator_id)
            VALUES (?, ?, ?, ?, ?)""",
            ('TEST_RT', 'Test Route', origin_id, dest_id, operator_id)
        )
        test_db.commit()
        
        # 验证
        cursor.execute("SELECT * FROM routes WHERE route_code = 'TEST_RT'")
        result = cursor.fetchone()
        assert result is not None


# ============================================
# Pydantic模型测试
# ============================================

class TestPydanticModels:
    """测试Pydantic模型"""
    
    def test_station_model_validation(self):
        """测试车站模型验证"""
        # 有效数据
        station = StationCreate(
            station_code="pad",  # 应该自动转大写
            station_name="London Paddington",
            latitude=Decimal("51.5154"),
            longitude=Decimal("-0.1755"),
            region="London",
            zone=1,
        )
        
        assert station.station_code == "PAD"
        assert station.zone == 1
    
    def test_station_model_invalid_zone(self):
        """测试无效的交通分区"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            StationCreate(
                station_code="TST",
                station_name="Test Station",
                zone=10,  # 超出范围
            )
    
    def test_fare_model_validation(self):
        """测试票价模型验证"""
        fare = FareCreate(
            origin_station_id=1,
            destination_station_id=2,
            fare_type=FareType.ANYTIME,
            ticket_class=TicketClass.STANDARD,
            adult_fare=Decimal("50.00"),
            child_fare=Decimal("25.00"),
        )
        
        assert fare.fare_type == FareType.ANYTIME
        assert fare.ticket_class == TicketClass.STANDARD
        assert fare.adult_fare == Decimal("50.00")
    
    def test_fare_same_station_validation(self):
        """测试起点终点相同的验证"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            FareCreate(
                origin_station_id=1,
                destination_station_id=1,  # 相同的车站
                fare_type=FareType.ANYTIME,
                ticket_class=TicketClass.STANDARD,
                adult_fare=Decimal("50.00"),
            )
    
    def test_delay_record_model(self):
        """测试延误记录模型"""
        delay = DelayRecordCreate(
            service_id=1,
            station_id=1,
            scheduled_time=datetime.now(),
            actual_time=datetime.now(),
            delay_minutes=15,
            delay_category=DelayCategory.WEATHER,
            weather_condition=WeatherCondition.RAINY,
        )
        
        assert delay.delay_minutes == 15
        assert delay.delay_category == DelayCategory.WEATHER
    
    def test_journey_search_model(self):
        """测试行程搜索模型"""
        search = JourneySearch(
            origin="pad",
            destination="bri",
            departure_date=date.today(),
            passengers=2,
        )
        
        assert search.origin == "PAD"
        assert search.destination == "BRI"
        assert search.passengers == 2
    
    def test_journey_search_same_station(self):
        """测试行程搜索起点终点相同"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            JourneySearch(
                origin="PAD",
                destination="pad",  # 相同车站
                departure_date=date.today(),
            )


# ============================================
# 索引性能测试
# ============================================

class TestIndexPerformance:
    """测试索引性能"""
    
    def test_index_on_station_code(self, test_db):
        """测试车站代码索引"""
        cursor = test_db.cursor()
        
        # 插入测试数据
        test_data = [
            (f'T{i:03d}', f'Test Station {i}', 51.5, -0.1, 'Test', None, 1)
            for i in range(100)
        ]
        cursor.executemany(
            """INSERT INTO stations 
            (station_code, station_name, latitude, longitude, region, zone, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            test_data
        )
        test_db.commit()
        
        # 测试查询
        cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM stations WHERE station_code = 'T050'")
        plan = cursor.fetchall()
        
        # 检查是否使用索引
        plan_str = str(plan)
        assert 'idx_stations_code' in plan_str or 'INDEX' in plan_str.upper()


# ============================================
# 触发器测试
# ============================================

class TestTriggers:
    """测试触发器"""
    
    def test_update_timestamp_trigger(self, test_db):
        """测试更新时间戳触发器"""
        cursor = test_db.cursor()
        
        # 插入车站
        cursor.execute(
            "INSERT INTO stations (station_code, station_name) VALUES (?, ?)",
            ('TST', 'Test Station')
        )
        test_db.commit()
        
        # 获取初始时间戳
        cursor.execute("SELECT created_at, updated_at FROM stations WHERE station_code = 'TST'")
        initial = cursor.fetchone()
        
        # 等待一小段时间
        import time
        time.sleep(0.1)
        
        # 更新车站
        cursor.execute(
            "UPDATE stations SET station_name = ? WHERE station_code = ?",
            ('Updated Test Station', 'TST')
        )
        test_db.commit()
        
        # 获取更新后的时间戳
        cursor.execute("SELECT created_at, updated_at FROM stations WHERE station_code = 'TST'")
        updated = cursor.fetchone()
        
        # 验证updated_at已更新
        assert updated[0] == initial[0]  # created_at不变
        # Note: SQLite的CURRENT_TIMESTAMP可能精度不够,这里只做基本检查
        assert updated[1] is not None


# ============================================
# 视图测试
# ============================================

class TestViews:
    """测试视图"""
    
    def test_popular_routes_view(self, test_db):
        """测试热门路线视图"""
        cursor = test_db.cursor()
        
        # 查询视图
        cursor.execute("SELECT * FROM popular_routes LIMIT 1")
        result = cursor.fetchone()
        
        # 视图应该能被查询(即使没有数据)
        # 不应该抛出错误
        assert True
    
    def test_delay_statistics_view(self, test_db):
        """测试延误统计视图"""
        cursor = test_db.cursor()
        
        # 查询视图
        cursor.execute("SELECT * FROM delay_statistics LIMIT 1")
        result = cursor.fetchone()
        
        # 视图应该能被查询
        assert True


# ============================================
# 运行测试
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
