"""
RailFair V1 - 票价系统测试套件
===================================

测试覆盖：
1. NRDP客户端认证测试
2. Fares数据解析测试
3. 价格缓存测试
4. 价格对比测试
5. 性能测试

作者: Vanessa @ RailFair
日期: Day 9
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from price_fetcher import (
    NRDPClient,
    FaresParser,
    FareCache,
    FareComparator,
    FareInfo,
    FareComparison,
    TicketType,
    TicketClass,
    initialize_fares_system
)


# ============================================
# 测试数据库fixture
# ============================================

@pytest.fixture
def test_db():
    """创建临时测试数据库"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    yield path
    
    # 清理
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_fares():
    """生成示例票价数据"""
    return [
        FareInfo(
            origin="EUS",
            destination="MAN",
            ticket_type=TicketType.ADVANCE,
            ticket_class=TicketClass.STANDARD,
            adult_fare=2500,
            child_fare=1250,
            valid_from=datetime.now(),
            valid_until=datetime.now() + timedelta(days=90),
            route_code=None,
            restriction_code="ADV",
            last_updated=datetime.now(),
            data_source="TEST"
        ),
        FareInfo(
            origin="EUS",
            destination="MAN",
            ticket_type=TicketType.OFF_PEAK,
            ticket_class=TicketClass.STANDARD,
            adult_fare=4500,
            child_fare=2250,
            valid_from=datetime.now(),
            valid_until=datetime.now() + timedelta(days=90),
            route_code=None,
            restriction_code="OPK",
            last_updated=datetime.now(),
            data_source="TEST"
        ),
        FareInfo(
            origin="EUS",
            destination="MAN",
            ticket_type=TicketType.ANYTIME,
            ticket_class=TicketClass.STANDARD,
            adult_fare=8900,
            child_fare=4450,
            valid_from=datetime.now(),
            valid_until=datetime.now() + timedelta(days=90),
            route_code=None,
            restriction_code="ANY",
            last_updated=datetime.now(),
            data_source="TEST"
        ),
    ]


# ============================================
# Fares解析器测试
# ============================================

class TestFaresParser:
    """测试Fares数据解析器"""
    
    def test_parser_initialization_simulated(self):
        """测试模拟数据模式初始化"""
        parser = FaresParser(b'')
        assert parser.zip_file is None
    
    def test_parse_simplified_fares(self):
        """测试简化票价解析"""
        parser = FaresParser(b'')
        fares = parser.parse_simplified_fares(limit=10)
        
        assert len(fares) > 0
        assert len(fares) <= 10
        
        # 验证数据结构
        fare = fares[0]
        assert isinstance(fare, FareInfo)
        assert fare.origin
        assert fare.destination
        assert fare.adult_fare > 0
    
    def test_parse_multiple_ticket_types(self):
        """测试生成多种票型"""
        parser = FaresParser(b'')
        fares = parser.parse_simplified_fares()
        
        # 应该包含不同票种
        ticket_types = set(f.ticket_type for f in fares)
        assert TicketType.ADVANCE in ticket_types
        assert TicketType.OFF_PEAK in ticket_types
        assert TicketType.ANYTIME in ticket_types
    
    def test_fares_price_order(self):
        """测试票价顺序（Advance < Off-Peak < Anytime）"""
        parser = FaresParser(b'')
        fares = parser.parse_simplified_fares()
        
        # 找同一路线的不同票种
        eus_man_fares = [f for f in fares if f.origin == 'EUS' and f.destination == 'MAN']
        
        if len(eus_man_fares) >= 3:
            prices = {f.ticket_type: f.adult_fare for f in eus_man_fares}
            assert prices[TicketType.ADVANCE] < prices[TicketType.OFF_PEAK]
            assert prices[TicketType.OFF_PEAK] < prices[TicketType.ANYTIME]


# ============================================
# 缓存系统测试
# ============================================

class TestFareCache:
    """测试票价缓存系统"""
    
    def test_cache_initialization(self, test_db):
        """测试缓存初始化"""
        cache = FareCache(test_db)
        
        # 验证数据库文件存在
        assert os.path.exists(test_db)
        
        # 验证表结构
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert 'fare_cache' in tables
        conn.close()
    
    def test_cache_fares(self, test_db, sample_fares):
        """测试批量缓存票价"""
        cache = FareCache(test_db)
        cache.cache_fares(sample_fares)
        
        # 验证缓存记录数
        stats = cache.get_cache_stats()
        assert stats['total_records'] == len(sample_fares)
    
    def test_get_fare_exists(self, test_db, sample_fares):
        """测试获取存在的票价"""
        cache = FareCache(test_db)
        cache.cache_fares(sample_fares)
        
        # 查询Advance票
        fare = cache.get_fare("EUS", "MAN", TicketType.ADVANCE)
        
        assert fare is not None
        assert fare.origin == "EUS"
        assert fare.destination == "MAN"
        assert fare.ticket_type == TicketType.ADVANCE
        assert fare.adult_fare == 2500
    
    def test_get_fare_not_exists(self, test_db):
        """测试获取不存在的票价"""
        cache = FareCache(test_db)
        
        fare = cache.get_fare("XXX", "YYY", TicketType.ADVANCE)
        assert fare is None
    
    def test_cache_hit_counting(self, test_db, sample_fares):
        """测试缓存命中计数"""
        cache = FareCache(test_db)
        cache.cache_fares(sample_fares)
        
        # 第一次查询
        cache.get_fare("EUS", "MAN", TicketType.ADVANCE)
        stats1 = cache.get_cache_stats()
        
        # 第二次查询
        cache.get_fare("EUS", "MAN", TicketType.ADVANCE)
        stats2 = cache.get_cache_stats()
        
        # 命中数应该增加
        assert stats2['total_hits'] > stats1['total_hits']
    
    def test_cache_stats(self, test_db, sample_fares):
        """测试缓存统计"""
        cache = FareCache(test_db)
        cache.cache_fares(sample_fares)
        
        stats = cache.get_cache_stats()
        
        assert 'total_records' in stats
        assert 'total_hits' in stats
        assert 'by_ticket_type' in stats
        assert stats['total_records'] == 3
    
    def test_cache_unique_constraint(self, test_db, sample_fares):
        """测试缓存唯一性约束（重复插入应替换）"""
        cache = FareCache(test_db)
        
        # 第一次缓存
        cache.cache_fares(sample_fares)
        
        # 第二次缓存（应该替换而不是重复）
        cache.cache_fares(sample_fares)
        
        stats = cache.get_cache_stats()
        assert stats['total_records'] == len(sample_fares)  # 仍然是3条


# ============================================
# 价格对比引擎测试
# ============================================

class TestFareComparator:
    """测试价格对比引擎"""
    
    def test_comparator_initialization(self, test_db):
        """测试对比引擎初始化"""
        cache = FareCache(test_db)
        comparator = FareComparator(cache)
        
        assert comparator.cache is not None
    
    def test_compare_fares_all_types(self, test_db, sample_fares):
        """测试完整票价对比"""
        cache = FareCache(test_db)
        cache.cache_fares(sample_fares)
        
        comparator = FareComparator(cache)
        result = comparator.compare_fares("EUS", "MAN", datetime.now())
        
        # 验证结果
        assert result.origin == "EUS"
        assert result.destination == "MAN"
        assert result.advance_price == 2500
        assert result.off_peak_price == 4500
        assert result.anytime_price == 8900
    
    def test_cheapest_identification(self, test_db, sample_fares):
        """测试最便宜票种识别"""
        cache = FareCache(test_db)
        cache.cache_fares(sample_fares)
        
        comparator = FareComparator(cache)
        result = comparator.compare_fares("EUS", "MAN", datetime.now())
        
        assert result.cheapest_type == TicketType.ADVANCE
        assert result.cheapest_price == 2500
    
    def test_savings_calculation(self, test_db, sample_fares):
        """测试节省金额计算"""
        cache = FareCache(test_db)
        cache.cache_fares(sample_fares)
        
        comparator = FareComparator(cache)
        result = comparator.compare_fares("EUS", "MAN", datetime.now())
        
        # Anytime (8900) - Advance (2500) = 6400
        assert result.savings_amount == 6400
        
        # 6400 / 8900 ≈ 71.9%
        assert 71.0 < result.savings_percentage < 72.0
    
    def test_compare_no_data(self, test_db):
        """测试无数据时的对比"""
        cache = FareCache(test_db)
        comparator = FareComparator(cache)
        
        result = comparator.compare_fares("XXX", "YYY", datetime.now())
        
        assert result.advance_price is None
        assert result.off_peak_price is None
        assert result.anytime_price is None
        assert not result.cached
    
    def test_format_price(self, test_db):
        """测试价格格式化"""
        cache = FareCache(test_db)
        comparator = FareComparator(cache)
        
        # 2500便士 = £25.00
        assert comparator.format_price(2500) == "£25.00"
        assert comparator.format_price(8900) == "£89.00"
        assert comparator.format_price(100) == "£1.00"
        assert comparator.format_price(50) == "£0.50"


# ============================================
# 系统集成测试
# ============================================

class TestSystemIntegration:
    """测试系统集成"""
    
    def test_initialize_simulated_system(self, test_db):
        """测试初始化模拟数据系统"""
        cache, comparator = initialize_fares_system(
            test_db,
            use_simulated_data=True
        )
        
        assert cache is not None
        assert comparator is not None
        
        # 验证数据已加载
        stats = cache.get_cache_stats()
        assert stats['total_records'] > 0
    
    def test_end_to_end_fare_query(self, test_db):
        """测试端到端票价查询"""
        cache, comparator = initialize_fares_system(
            test_db,
            use_simulated_data=True
        )
        
        # 执行查询
        result = comparator.compare_fares("EUS", "MAN", datetime.now())
        
        # 验证结果
        assert result.cheapest_price > 0
        assert result.savings_percentage >= 0
    
    def test_multiple_queries_hit_cache(self, test_db):
        """测试多次查询命中缓存"""
        cache, comparator = initialize_fares_system(
            test_db,
            use_simulated_data=True
        )
        
        # 第一次查询
        result1 = comparator.compare_fares("EUS", "MAN", datetime.now())
        stats1 = cache.get_cache_stats()
        
        # 第二次查询（应该命中缓存）
        result2 = comparator.compare_fares("EUS", "MAN", datetime.now())
        stats2 = cache.get_cache_stats()
        
        # 命中数增加
        assert stats2['total_hits'] > stats1['total_hits']
        
        # 结果应该一致
        assert result1.cheapest_price == result2.cheapest_price


# ============================================
# 性能测试
# ============================================

class TestPerformance:
    """测试性能要求"""
    
    def test_cache_query_speed(self, test_db):
        """测试缓存查询速度"""
        import time
        
        cache, comparator = initialize_fares_system(
            test_db,
            use_simulated_data=True
        )
        
        # 测试100次查询
        start = time.time()
        for _ in range(100):
            comparator.compare_fares("EUS", "MAN", datetime.now())
        elapsed = (time.time() - start) * 1000  # 毫秒
        
        avg_time = elapsed / 100
        
        # 单次查询应该 <50ms（包含日志开销）
        assert avg_time < 50, f"平均查询时间 {avg_time:.2f}ms 超过50ms"
    
    def test_batch_caching_performance(self, test_db):
        """测试批量缓存性能"""
        import time
        
        cache = FareCache(test_db)
        
        # 生成1000条测试数据
        parser = FaresParser(b'')
        fares = parser.parse_simplified_fares(limit=1000)
        
        # 测试批量缓存
        start = time.time()
        cache.cache_fares(fares)
        elapsed = (time.time() - start) * 1000
        
        # 1000条记录应该在1秒内完成
        assert elapsed < 1000, f"批量缓存耗时 {elapsed:.0f}ms 超过1秒"


# ============================================
# 数据模型测试
# ============================================

class TestDataModels:
    """测试数据模型"""
    
    def test_fare_info_creation(self):
        """测试FareInfo创建"""
        fare = FareInfo(
            origin="EUS",
            destination="MAN",
            ticket_type=TicketType.ADVANCE,
            ticket_class=TicketClass.STANDARD,
            adult_fare=2500,
            child_fare=1250,
            valid_from=datetime.now(),
            valid_until=datetime.now() + timedelta(days=90),
            route_code=None,
            restriction_code="ADV",
            last_updated=datetime.now(),
            data_source="TEST"
        )
        
        assert fare.origin == "EUS"
        assert fare.adult_fare == 2500
        assert fare.ticket_type == TicketType.ADVANCE
    
    def test_ticket_type_enum(self):
        """测试票种枚举"""
        assert TicketType.ADVANCE.value == "advance"
        assert TicketType.OFF_PEAK.value == "off_peak"
        assert TicketType.ANYTIME.value == "anytime"
    
    def test_ticket_class_enum(self):
        """测试等级枚举"""
        assert TicketClass.STANDARD.value == "standard"
        assert TicketClass.FIRST.value == "first"


# ============================================
# 运行测试
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
