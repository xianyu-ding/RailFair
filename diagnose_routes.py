#!/usr/bin/env python3
"""
路线数据诊断脚本
分析为什么某些路线数据量少或无数据
"""

import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
import json

# 目标路线配置（基于Day 4计划）
TARGET_ROUTES = {
    'EUS-MAN': {'from': 'EUS', 'to': 'MAN', 'name': 'London Euston → Manchester'},
    'KGX-EDB': {'from': 'KGX', 'to': 'EDB', 'name': 'London King\'s Cross → Edinburgh'},
    'PAD-BRI': {'from': 'PAD', 'to': 'BRI', 'name': 'London Paddington → Bristol'},
    'LST-NRW': {'from': 'LST', 'to': 'NRW', 'name': 'London Liverpool St → Norwich'},
    'MYB-BHM': {'from': 'MYB', 'to': 'BHM', 'name': 'London Marylebone → Birmingham'},
    'MAN-LIV': {'from': 'MAN', 'to': 'LIV', 'name': 'Manchester → Liverpool'},
    'BHM-MAN': {'from': 'BHM', 'to': 'MAN', 'name': 'Birmingham → Manchester'},
    'BRI-BHM': {'from': 'BRI', 'to': 'BHM', 'name': 'Bristol → Birmingham'},
    'EDB-GLC': {'from': 'EDB', 'to': 'GLC', 'name': 'Edinburgh → Glasgow'},
    'MAN-LDS': {'from': 'MAN', 'to': 'LDS', 'name': 'Manchester → Leeds'}
}

# 常见车站代码变体
STATION_ALIASES = {
    'EDR': 'EDB',  # Edinburgh
    'EDI': 'EDB',
    'MCO': 'MAN',  # Manchester
    'MCV': 'MAN',
    'LEE': 'LDS',  # Leeds
    'BHI': 'BHM',  # Birmingham
    'BHN': 'BHM',
    'GLA': 'GLC',  # Glasgow
    'GLQ': 'GLC',
    'BRS': 'BRI',  # Bristol
    'NRW': 'NRW',  # Norwich (正确)
    'LPY': 'LIV',  # Liverpool
}

def get_db_connection(db_path: str):
    """连接数据库"""
    return sqlite3.connect(db_path)

def analyze_stations_in_db(conn):
    """分析数据库中实际存在的车站代码"""
    print("\n" + "="*70)
    print("📊 数据库中的实际车站代码")
    print("="*70)
    
    # 从metrics表查询
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT origin, destination, COUNT(*) as count
        FROM hsp_service_metrics
        GROUP BY origin, destination
        ORDER BY count DESC
        LIMIT 50
    """)
    
    metrics_routes = cursor.fetchall()
    
    print("\n📈 HSP Metrics表中的路线（前50）：")
    print(f"{'起点':<8} {'终点':<8} {'记录数':>8}")
    print("-" * 26)
    for origin, dest, count in metrics_routes:
        print(f"{origin:<8} {dest:<8} {count:>8}")
    
    # 从details表查询
    cursor.execute("""
        SELECT location, COUNT(*) as count
        FROM hsp_service_details
        GROUP BY location
        ORDER BY count DESC
        LIMIT 30
    """)
    
    details_locations = cursor.fetchall()
    
    print("\n📍 HSP Details表中的车站（前30）：")
    print(f"{'车站代码':<10} {'记录数':>8}")
    print("-" * 20)
    for location, count in details_locations:
        print(f"{location:<10} {count:>8}")
    
    return metrics_routes, details_locations

def find_route_data(conn, route_key, route_info):
    """查找特定路线的数据"""
    from_code = route_info['from']
    to_code = route_info['to']
    
    # 尝试多种车站代码组合
    variants = []
    
    # 添加原始代码
    variants.append((from_code, to_code))
    
    # 添加别名
    if from_code in STATION_ALIASES:
        variants.append((STATION_ALIASES[from_code], to_code))
    if to_code in STATION_ALIASES:
        variants.append((from_code, STATION_ALIASES[to_code]))
    if from_code in STATION_ALIASES and to_code in STATION_ALIASES:
        variants.append((STATION_ALIASES[from_code], STATION_ALIASES[to_code]))
    
    results = {}
    cursor = conn.cursor()
    
    for from_var, to_var in variants:
        # 查询metrics表
        cursor.execute("""
            SELECT COUNT(*) 
            FROM hsp_service_metrics 
            WHERE origin = ? AND destination = ?
        """, (from_var, to_var))
        metrics_count = cursor.fetchone()[0]
        
        # 查询details表中的服务数
        cursor.execute("""
            SELECT COUNT(DISTINCT rid)
            FROM hsp_service_details
            WHERE rid IN (
                SELECT rid FROM hsp_service_details
                WHERE location = ?
            ) AND rid IN (
                SELECT rid FROM hsp_service_details
                WHERE location = ?
            )
        """, (from_var, to_var))
        details_count = cursor.fetchone()[0]
        
        if metrics_count > 0 or details_count > 0:
            results[f"{from_var}-{to_var}"] = {
                'metrics': metrics_count,
                'details': details_count
            }
    
    return results

def diagnose_all_routes(db_path: str):
    """诊断所有目标路线"""
    conn = get_db_connection(db_path)
    
    print("="*70)
    print("🔍 RailFair 路线数据诊断报告")
    print("="*70)
    
    # 分析数据库中的实际车站
    analyze_stations_in_db(conn)
    
    # 诊断每条目标路线
    print("\n" + "="*70)
    print("🛤️ 目标路线诊断")
    print("="*70)
    
    route_status = {}
    
    for route_key, route_info in TARGET_ROUTES.items():
        print(f"\n📍 {route_key}: {route_info['name']}")
        print("-" * 70)
        
        results = find_route_data(conn, route_key, route_info)
        
        if not results:
            print("   ❌ 无数据")
            print(f"   💡 尝试查询: {route_info['from']} → {route_info['to']}")
            route_status[route_key] = 'NO_DATA'
        else:
            total_metrics = sum(r['metrics'] for r in results.values())
            total_details = sum(r['details'] for r in results.values())
            
            print(f"   ✅ 找到数据变体:")
            for variant, counts in results.items():
                print(f"      {variant}: Metrics={counts['metrics']}, Details={counts['details']}")
            
            print(f"   📊 总计: Metrics={total_metrics}, Details={total_details}")
            
            if total_metrics < 50:
                route_status[route_key] = 'LOW_DATA'
            else:
                route_status[route_key] = 'OK'
    
    # 生成修复建议
    print("\n" + "="*70)
    print("💡 修复建议")
    print("="*70)
    
    no_data_routes = [k for k, v in route_status.items() if v == 'NO_DATA']
    low_data_routes = [k for k, v in route_status.items() if v == 'LOW_DATA']
    
    if no_data_routes:
        print(f"\n❌ 完全无数据的路线 ({len(no_data_routes)}):")
        for route in no_data_routes:
            info = TARGET_ROUTES[route]
            print(f"   • {route} ({info['from']} → {info['to']})")
        
        print("\n   修复方法:")
        print("   1. 检查车站代码是否正确")
        print("   2. 验证这些路线是否真实存在")
        print("   3. 检查HSP API查询参数（时间段、TOC等）")
        print("   4. 考虑替换为其他高流量路线")
    
    if low_data_routes:
        print(f"\n⚠️ 数据量不足的路线 ({len(low_data_routes)}):")
        for route in low_data_routes:
            info = TARGET_ROUTES[route]
            print(f"   • {route} ({info['from']} → {info['to']})")
        
        print("\n   改进方法:")
        print("   1. 扩大日期范围（3-6个月）")
        print("   2. 包含周末数据")
        print("   3. 检查TOC过滤条件")
        print("   4. 验证时间段设置（早晚高峰）")
    
    # 推荐替代路线
    print("\n" + "="*70)
    print("🔄 推荐替代路线")
    print("="*70)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT origin, destination, COUNT(*) as count
        FROM hsp_service_metrics
        WHERE origin != destination
        GROUP BY origin, destination
        HAVING count > 100
        ORDER BY count DESC
        LIMIT 15
    """)
    
    alternative_routes = cursor.fetchall()
    
    print("\n数据库中数据量最大的路线（可作为替代）：")
    print(f"{'起点':<8} {'终点':<8} {'记录数':>8}")
    print("-" * 26)
    for origin, dest, count in alternative_routes:
        print(f"{origin:<8} {dest:<8} {count:>8}")
    
    # 生成JSON报告
    report = {
        'generated_at': datetime.now().isoformat(),
        'route_status': route_status,
        'no_data_routes': no_data_routes,
        'low_data_routes': low_data_routes,
        'alternative_routes': [
            {'from': r[0], 'to': r[1], 'count': r[2]}
            for r in alternative_routes
        ]
    }
    
    report_path = 'data/route_diagnosis_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 详细报告已保存: {report_path}")
    
    conn.close()
    
    return route_status

if __name__ == '__main__':
    db_path = 'data/railfair.db'
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    try:
        diagnose_all_routes(db_path)
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
