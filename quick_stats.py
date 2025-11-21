#!/usr/bin/env python3
"""
快速数据统计脚本 - 了解当前数据库状态
"""

import sqlite3
from pathlib import Path

def quick_stats(db_path="data/railfair.db"):
    """快速统计当前数据"""
    
    if not Path(db_path).exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("📊 QUICK DATABASE STATISTICS")
    print("=" * 60)
    
    # 检查主要表
    tables_to_check = [
        "hsp_service_metrics",
        "hsp_service_details",
        "toc_metadata",
        "station_metadata",
        "route_metadata",
        "compensation_rules"
    ]
    
    print("\n📋 Table Record Counts:")
    print("-" * 40)
    for table in tables_to_check:
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:25} : {count:,} records")
        except:
            print(f"  {table:25} : ❌ Table not found")
    
    # 路线统计
    try:
        routes = cursor.execute("""
            SELECT DISTINCT origin || '-' || destination as route, COUNT(*) as count
            FROM hsp_service_metrics
            GROUP BY route
            ORDER BY count DESC
        """).fetchall()
        
        print("\n🛤️ Routes with Data:")
        print("-" * 40)
        for route, count in routes[:10]:
            print(f"  {route:10} : {count:,} services")
        if len(routes) > 10:
            print(f"  ... and {len(routes)-10} more routes")
            
        print(f"\n  Total unique routes: {len(routes)}")
        
    except Exception as e:
        print(f"  Error getting routes: {e}")
    
    # TOC统计
    try:
        tocs = cursor.execute("""
            SELECT toc_code, COUNT(*) as count
            FROM hsp_service_details
            WHERE toc_code IS NOT NULL
            GROUP BY toc_code
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()
        
        print("\n🚂 Top TOCs by Service Count:")
        print("-" * 40)
        for toc, count in tocs:
            print(f"  {toc:5} : {count:,} records")
            
    except Exception as e:
        print(f"  Error getting TOCs: {e}")
    
    # 日期范围
    try:
        date_range = cursor.execute("""
            SELECT MIN(date_of_service), MAX(date_of_service), 
                   COUNT(DISTINCT date_of_service)
            FROM hsp_service_details
        """).fetchone()
        
        print("\n📅 Date Range:")
        print("-" * 40)
        if date_range[0]:
            print(f"  From: {date_range[0]}")
            print(f"  To:   {date_range[1]}")
            print(f"  Days: {date_range[2]}")
            
    except Exception as e:
        print(f"  Error getting date range: {e}")
    
    # 延误统计
    try:
        delay_stats = cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(arrival_delay_minutes) as avg_delay,
                MIN(arrival_delay_minutes) as min_delay,
                MAX(arrival_delay_minutes) as max_delay,
                SUM(CASE WHEN arrival_delay_minutes <= 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as on_time_pct
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
        """).fetchone()
        
        print("\n⏱️ Delay Statistics:")
        print("-" * 40)
        if delay_stats[0] > 0:
            print(f"  Records with delay data: {delay_stats[0]:,}")
            print(f"  Average delay: {delay_stats[1]:.1f} minutes")
            print(f"  On-time rate: {delay_stats[4]:.1f}%")
            print(f"  Min delay: {delay_stats[2]:.0f} min")
            print(f"  Max delay: {delay_stats[3]:.0f} min")
            
    except Exception as e:
        print(f"  Error getting delay stats: {e}")
    
    # 数据完整性
    try:
        completeness = cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN scheduled_departure IS NOT NULL THEN 1 ELSE 0 END) as has_sched_dep,
                SUM(CASE WHEN actual_departure IS NOT NULL THEN 1 ELSE 0 END) as has_actual_dep,
                SUM(CASE WHEN arrival_delay_minutes IS NOT NULL THEN 1 ELSE 0 END) as has_delay
            FROM hsp_service_details
        """).fetchone()
        
        print("\n📊 Data Completeness:")
        print("-" * 40)
        if completeness[0] > 0:
            total = completeness[0]
            print(f"  Scheduled departure: {completeness[1]/total*100:.1f}%")
            print(f"  Actual departure: {completeness[2]/total*100:.1f}%")
            print(f"  Delay data: {completeness[3]/total*100:.1f}%")
            
    except Exception as e:
        print(f"  Error checking completeness: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Quick stats complete!")
    print("=" * 60)
    
    conn.close()

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/railfair.db"
    quick_stats(db_path)
