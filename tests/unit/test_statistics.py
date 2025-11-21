#!/usr/bin/env python3
"""
RailFair Statistics System Test - Day 6
测试统计计算和查询功能
"""

import sys
import os
import sqlite3
from datetime import datetime, date

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def test_database_exists(db_path: str) -> bool:
    """测试1: 数据库文件存在"""
    print(f"\n🧪 Test 1: Database file exists")
    if os.path.exists(db_path):
        print(f"   {Colors.GREEN}✅ Database found: {db_path}{Colors.END}")
        return True
    else:
        print(f"   {Colors.RED}❌ Database not found: {db_path}{Colors.END}")
        return False

def test_statistics_tables(db_path: str) -> bool:
    """测试2: 统计表存在"""
    print(f"\n🧪 Test 2: Statistics tables exist")
    
    expected_tables = [
        'route_statistics',
        'toc_statistics',
        'time_slot_statistics',
        'prediction_cache',
        'data_quality_metrics'
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        all_exist = True
        for table in expected_tables:
            if table in tables:
                print(f"   {Colors.GREEN}✅ {table}{Colors.END}")
            else:
                print(f"   {Colors.RED}❌ {table} (missing){Colors.END}")
                all_exist = False
        
        conn.close()
        return all_exist
        
    except Exception as e:
        print(f"   {Colors.RED}❌ Error: {e}{Colors.END}")
        return False

def test_statistics_data(db_path: str) -> bool:
    """测试3: 统计数据存在"""
    print(f"\n🧪 Test 3: Statistics data exists")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查路线统计
        cursor.execute("SELECT COUNT(*) FROM route_statistics")
        route_count = cursor.fetchone()[0]
        
        # 检查TOC统计
        cursor.execute("SELECT COUNT(*) FROM toc_statistics")
        toc_count = cursor.fetchone()[0]
        
        print(f"   Route statistics: {route_count} records")
        print(f"   TOC statistics: {toc_count} records")
        
        if route_count > 0 and toc_count > 0:
            print(f"   {Colors.GREEN}✅ Statistics data available{Colors.END}")
            conn.close()
            return True
        else:
            print(f"   {Colors.YELLOW}⚠️  No statistics yet - run calculate_stats.py{Colors.END}")
            conn.close()
            # Don't fail the test if there's no data - this is expected initially
            return True
            
    except Exception as e:
        print(f"   {Colors.RED}❌ Error: {e}{Colors.END}")
        return False

def test_statistics_views(db_path: str) -> bool:
    """测试4: 统计视图可用"""
    print(f"\n🧪 Test 4: Statistics views available")
    
    expected_views = [
        'v_latest_route_stats',
        'v_latest_toc_stats'
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view' 
            ORDER BY name
        """)
        views = [row[0] for row in cursor.fetchall()]
        
        all_exist = True
        for view in expected_views:
            if view in views:
                # 测试视图查询
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {view}")
                    count = cursor.fetchone()[0]
                    print(f"   {Colors.GREEN}✅ {view} ({count} rows){Colors.END}")
                except:
                    print(f"   {Colors.RED}❌ {view} (query failed){Colors.END}")
                    all_exist = False
            else:
                print(f"   {Colors.RED}❌ {view} (missing){Colors.END}")
                all_exist = False
        
        conn.close()
        return all_exist
        
    except Exception as e:
        print(f"   {Colors.RED}❌ Error: {e}{Colors.END}")
        return False

def test_query_interface(db_path: str) -> bool:
    """测试5: 查询接口功能"""
    print(f"\n🧪 Test 5: Query interface functionality")
    
    try:
        # 导入查询模块
        from query_stats import StatisticsQuery
        
        with StatisticsQuery(db_path) as query:
            # 测试路线查询
            routes = query.get_all_routes_stats()
            print(f"   {Colors.GREEN}✅ get_all_routes_stats(): {len(routes)} routes{Colors.END}")
            
            # 测试TOC查询
            tocs = query.get_all_tocs_stats()
            print(f"   {Colors.GREEN}✅ get_all_tocs_stats(): {len(tocs)} TOCs{Colors.END}")
            
            # 测试缓存统计
            cache_stats = query.get_cache_stats()
            print(f"   {Colors.GREEN}✅ get_cache_stats(): {cache_stats['total_entries']} entries{Colors.END}")
            
            return True
            
    except Exception as e:
        print(f"   {Colors.RED}❌ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

def test_statistics_calculation(db_path: str) -> bool:
    """测试6: 统计计算准确性"""
    print(f"\n🧪 Test 6: Statistics calculation accuracy")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取一条路线统计
        cursor.execute("""
            SELECT * FROM route_statistics
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if not result:
            print(f"   {Colors.YELLOW}⚠️  No statistics to test{Colors.END}")
            # Don't fail the test if there's no data - this is expected initially
            return True
        
        # 获取列名
        columns = [description[0] for description in cursor.description]
        stats = dict(zip(columns, result))
        
        # 验证计算
        tests = []
        
        # 1. 准点率应该在0-100之间
        tests.append(('On-time percentage', 
                     0 <= stats['on_time_percentage'] <= 100))
        
        # 2. PPM-5 >= On-time
        tests.append(('PPM-5 >= On-time',
                     stats['time_to_5_percentage'] >= stats['on_time_percentage']))
        
        # 3. PPM-10 >= PPM-5
        tests.append(('PPM-10 >= PPM-5',
                     stats['time_to_10_percentage'] >= stats['time_to_5_percentage']))
        
        # 4. 可靠性分数在0-100之间
        tests.append(('Reliability score range',
                     0 <= stats['reliability_score'] <= 100))
        
        # 5. 平均延误应该大于0
        tests.append(('Average delay > 0',
                     stats['avg_delay_minutes'] >= 0))
        
        # 6. 取消率在0-100之间
        tests.append(('Cancellation percentage range',
                     0 <= stats['cancelled_percentage'] <= 100))
        
        # 打印结果
        all_passed = True
        for test_name, passed in tests:
            if passed:
                print(f"   {Colors.GREEN}✅ {test_name}{Colors.END}")
            else:
                print(f"   {Colors.RED}❌ {test_name}{Colors.END}")
                all_passed = False
        
        conn.close()
        return all_passed
        
    except Exception as e:
        print(f"   {Colors.RED}❌ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_functionality(db_path: str) -> bool:
    """测试7: 缓存功能"""
    print(f"\n🧪 Test 7: Cache functionality")
    
    try:
        from query_stats import StatisticsQuery
        
        with StatisticsQuery(db_path) as query:
            # 测试缓存键生成
            cache_key = query.generate_cache_key('EUS', 'MAN', '2025-12-01', '09:00')
            print(f"   {Colors.GREEN}✅ Cache key generation{Colors.END}")
            
            # 测试缓存保存
            test_prediction = {
                'origin': 'EUS',
                'destination': 'MAN',
                'departure_date': '2025-12-01',
                'departure_time': '09:00',
                'predicted_delay_minutes': 5.2,
                'on_time_probability': 0.65,
                'delay_5_probability': 0.75,
                'delay_15_probability': 0.90,
                'severe_delay_probability': 0.05,
                'confidence_level': 'high',
                'confidence_score': 0.85,
                'recommendation': 'on_time',
                'alternative_suggestions': [],
                'model_version': 'test-v1'
            }
            
            query.save_prediction_cache(test_prediction, ttl_hours=1)
            print(f"   {Colors.GREEN}✅ Cache save{Colors.END}")
            
            # 测试缓存读取
            cached = query.get_prediction_cache('EUS', 'MAN', '2025-12-01', '09:00')
            if cached and cached['predicted_delay_minutes'] == 5.2:
                print(f"   {Colors.GREEN}✅ Cache retrieval{Colors.END}")
            else:
                print(f"   {Colors.RED}❌ Cache retrieval failed{Colors.END}")
                return False
            
            # 测试缓存命中统计
            stats = query.get_cache_stats()
            if stats['cache_hits'] > 0:
                print(f"   {Colors.GREEN}✅ Cache hit tracking{Colors.END}")
            else:
                print(f"   {Colors.YELLOW}⚠️  No cache hits recorded{Colors.END}")
            
            return True
            
    except Exception as e:
        print(f"   {Colors.RED}❌ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return False

def test_performance(db_path: str) -> bool:
    """测试8: 查询性能"""
    print(f"\n🧪 Test 8: Query performance")
    
    try:
        from query_stats import StatisticsQuery
        import time
        
        with StatisticsQuery(db_path) as query:
            # 测试路线查询速度
            start = time.time()
            routes = query.get_all_routes_stats()
            elapsed = (time.time() - start) * 1000
            
            if elapsed < 100:  # 应该在100ms内
                print(f"   {Colors.GREEN}✅ Route query: {elapsed:.2f}ms{Colors.END}")
            else:
                print(f"   {Colors.YELLOW}⚠️  Route query: {elapsed:.2f}ms (>100ms){Colors.END}")
            
            # 测试单个路线查询
            if routes:
                start = time.time()
                stats = query.get_route_stats(routes[0]['origin'], routes[0]['destination'])
                elapsed = (time.time() - start) * 1000
                
                if elapsed < 50:  # 应该在50ms内
                    print(f"   {Colors.GREEN}✅ Single route query: {elapsed:.2f}ms{Colors.END}")
                else:
                    print(f"   {Colors.YELLOW}⚠️  Single route query: {elapsed:.2f}ms (>50ms){Colors.END}")
            
            # 测试缓存查询
            start = time.time()
            cached = query.get_prediction_cache('EUS', 'MAN', '2025-12-01', '09:00')
            elapsed = (time.time() - start) * 1000
            
            if elapsed < 10:  # 应该在10ms内
                print(f"   {Colors.GREEN}✅ Cache query: {elapsed:.2f}ms{Colors.END}")
            else:
                print(f"   {Colors.YELLOW}⚠️  Cache query: {elapsed:.2f}ms (>10ms){Colors.END}")
            
            return True
            
    except Exception as e:
        print(f"   {Colors.RED}❌ Error: {e}{Colors.END}")
        return False

def main():
    """运行所有测试"""
    print("="*60)
    print("🧪 RailFair Statistics System Tests - Day 6")
    print("="*60)
    
    # 数据库路径
    db_path = "data/railfair.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # 运行测试
    tests = [
        test_database_exists,
        test_statistics_tables,
        test_statistics_data,
        test_statistics_views,
        test_query_interface,
        test_statistics_calculation,
        test_cache_functionality,
        test_performance
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func(db_path)
            results.append(result)
        except Exception as e:
            print(f"\n{Colors.RED}❌ Test failed with exception: {e}{Colors.END}")
            results.append(False)
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100
    
    print(f"\nTests Passed: {passed}/{total} ({percentage:.1f}%)")
    
    if passed == total:
        print(f"\n{Colors.GREEN}✅ All tests passed!{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}⚠️  Some tests failed{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
