#!/usr/bin/env python3
"""
RailFair Statistics Calculator - Day 6
计算并缓存路线统计数据，用于快速查询和预测
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import sys
import os

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message: str, color: str = Colors.END):
    """彩色打印"""
    print(f"{color}{message}{Colors.END}")

class StatisticsCalculator:
    """统计计算器"""
    
    def __init__(self, db_path: str = "data/railfair.db"):
        self.db_path = db_path
        self.conn = None
        self.calculation_date = date.today()
        
    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print_colored(f"✅ Connected to database: {self.db_path}", Colors.GREEN)
            return True
        except Exception as e:
            print_colored(f"❌ Database connection failed: {e}", Colors.FAIL)
            return False
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            print_colored("✅ Database connection closed", Colors.GREEN)
    
    def create_statistics_tables(self):
        """创建统计表（如果不存在）"""
        print_colored("\n📊 Creating statistics tables...", Colors.BLUE)
        
        sql_file = "create_statistics_tables.sql"
        if not os.path.exists(sql_file):
            print_colored(f"⚠️  SQL file not found: {sql_file}", Colors.WARNING)
            print_colored("   Please run this script from the project root directory", Colors.WARNING)
            return False
        
        try:
            with open(sql_file, 'r') as f:
                sql_script = f.read()
            
            self.conn.executescript(sql_script)
            self.conn.commit()
            print_colored("✅ Statistics tables created", Colors.GREEN)
            return True
        except Exception as e:
            print_colored(f"❌ Failed to create tables: {e}", Colors.FAIL)
            return False
    
    def get_data_summary(self) -> Dict:
        """获取数据概览"""
        print_colored("\n📊 Analyzing current data...", Colors.BLUE)
        
        cursor = self.conn.cursor()
        
        # 基础统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT rid) as unique_services,
                MIN(date_of_service) as earliest_date,
                MAX(date_of_service) as latest_date,
                COUNT(DISTINCT location) as unique_locations,
                COUNT(DISTINCT toc_code) as unique_tocs
            FROM hsp_service_details
        """)
        basic_stats = dict(cursor.fetchone())
        
        # 路线统计
        cursor.execute("""
            SELECT DISTINCT origin, destination
            FROM hsp_service_metrics
            ORDER BY origin, destination
        """)
        routes = [(r['origin'], r['destination']) for r in cursor.fetchall()]
        
        summary = {
            **basic_stats,
            'routes': routes,
            'route_count': len(routes)
        }
        
        print_colored(f"  📈 Total records: {summary['total_records']:,}", Colors.CYAN)
        print_colored(f"  🚂 Unique services: {summary['unique_services']:,}", Colors.CYAN)
        print_colored(f"  🛤️  Unique routes: {summary['route_count']}", Colors.CYAN)
        print_colored(f"  📅 Date range: {summary['earliest_date']} to {summary['latest_date']}", Colors.CYAN)
        print_colored(f"  🏢 TOCs: {summary['unique_tocs']}", Colors.CYAN)
        
        return summary
    
    def calculate_route_statistics(self, origin: str, destination: str) -> Optional[Dict]:
        """计算单条路线的统计数据"""
        cursor = self.conn.cursor()
        
        # 获取该路线的所有详细记录
        # 注意: hsp_service_details 包含所有停靠站的记录
        # 我们需要获取目的地站的到达延误数据
        cursor.execute("""
            SELECT DISTINCT
                sd.rid,
                sd.date_of_service,
                sd.toc_code,
                sd.location,
                sd.scheduled_arrival,
                sd.actual_arrival,
                sd.arrival_delay_minutes,
                sd.cancellation_reason,
                strftime('%w', sd.date_of_service) as day_of_week,
                strftime('%H', sd.scheduled_arrival) as hour_of_day
            FROM hsp_service_details sd
            WHERE sd.location = ?
              AND sd.arrival_delay_minutes IS NOT NULL
              AND sd.toc_code IN (
                  SELECT DISTINCT toc_code 
                  FROM hsp_service_metrics 
                  WHERE origin = ? AND destination = ?
              )
            ORDER BY sd.date_of_service, sd.scheduled_arrival
        """, (destination, origin, destination))
        
        records = cursor.fetchall()
        
        if not records:
            return None
        
        # 转换为字典列表
        records = [dict(r) for r in records]
        
        # 基础统计
        total_records = len(records)
        unique_services = len(set(r['rid'] for r in records))
        
        # 日期范围
        dates = [r['date_of_service'] for r in records if r['date_of_service']]
        data_start_date = min(dates) if dates else None
        data_end_date = max(dates) if dates else None
        data_days = (datetime.strptime(data_end_date, '%Y-%m-%d') - 
                     datetime.strptime(data_start_date, '%Y-%m-%d')).days + 1 if data_start_date else 0
        
        # 星期分布
        weekday_count = sum(1 for r in records if r['day_of_week'] not in ['0', '6'])  # 0=Sunday, 6=Saturday
        weekend_count = total_records - weekday_count
        
        # 延误统计
        delays = [r['arrival_delay_minutes'] for r in records if r['arrival_delay_minutes'] is not None]
        
        if not delays:
            return None
        
        # 准点率计算 (ORR标准)
        on_time_count = sum(1 for d in delays if d <= 1)
        time_to_3 = sum(1 for d in delays if d <= 3)
        time_to_5 = sum(1 for d in delays if d <= 5)
        time_to_10 = sum(1 for d in delays if d <= 10)
        time_to_15 = sum(1 for d in delays if d <= 15)
        time_to_30 = sum(1 for d in delays if d <= 30)
        
        on_time_pct = (on_time_count / len(delays)) * 100
        time_to_3_pct = (time_to_3 / len(delays)) * 100
        time_to_5_pct = (time_to_5 / len(delays)) * 100  # PPM-5
        time_to_10_pct = (time_to_10 / len(delays)) * 100  # PPM-10
        time_to_15_pct = (time_to_15 / len(delays)) * 100
        time_to_30_pct = (time_to_30 / len(delays)) * 100
        
        # 延误分布
        delays_0_5 = sum(1 for d in delays if 0 <= d <= 5)
        delays_5_15 = sum(1 for d in delays if 5 < d <= 15)
        delays_15_30 = sum(1 for d in delays if 15 < d <= 30)
        delays_30_60 = sum(1 for d in delays if 30 < d <= 60)
        delays_60_plus = sum(1 for d in delays if d > 60)
        
        # 取消统计
        cancelled_count = sum(1 for r in records if r['cancellation_reason'])
        cancelled_pct = (cancelled_count / total_records) * 100 if total_records > 0 else 0
        
        # 严重延误 (>60分钟)
        severe_delay_count = delays_60_plus
        
        # 平均延误
        avg_delay = sum(delays) / len(delays)
        
        # 中位数延误
        sorted_delays = sorted(delays)
        median_delay = sorted_delays[len(sorted_delays) // 2]
        
        # 最大延误
        max_delay = max(delays)
        
        # 标准差
        variance = sum((d - avg_delay) ** 2 for d in delays) / len(delays)
        std_delay = variance ** 0.5
        
        # 可靠性评分 (0-100)
        # 权重: PPM-5 (40%), PPM-10 (30%), 取消率 (20%), 严重延误率 (10%)
        severe_delay_rate = (severe_delay_count / len(delays)) * 100
        reliability_score = (
            time_to_5_pct * 0.4 +
            time_to_10_pct * 0.3 +
            (100 - cancelled_pct) * 0.2 +
            (100 - severe_delay_rate) * 0.1
        )
        
        # 可靠性评级
        if reliability_score >= 90:
            reliability_grade = 'A'
        elif reliability_score >= 80:
            reliability_grade = 'B'
        elif reliability_score >= 70:
            reliability_grade = 'C'
        elif reliability_score >= 60:
            reliability_grade = 'D'
        else:
            reliability_grade = 'F'
        
        # 按小时统计
        hourly_stats = defaultdict(lambda: {'count': 0, 'avg_delay': 0, 'delays': []})
        for r in records:
            if r['hour_of_day'] and r['arrival_delay_minutes'] is not None:
                hour = int(r['hour_of_day'])
                hourly_stats[hour]['count'] += 1
                hourly_stats[hour]['delays'].append(r['arrival_delay_minutes'])
        
        for hour in hourly_stats:
            delays_list = hourly_stats[hour]['delays']
            hourly_stats[hour]['avg_delay'] = sum(delays_list) / len(delays_list)
            del hourly_stats[hour]['delays']  # 不需要保存原始延误列表
        
        # 按星期统计
        dow_stats = defaultdict(lambda: {'count': 0, 'avg_delay': 0, 'delays': []})
        for r in records:
            if r['day_of_week'] and r['arrival_delay_minutes'] is not None:
                dow = int(r['day_of_week'])
                dow_stats[dow]['count'] += 1
                dow_stats[dow]['delays'].append(r['arrival_delay_minutes'])
        
        for dow in dow_stats:
            delays_list = dow_stats[dow]['delays']
            dow_stats[dow]['avg_delay'] = sum(delays_list) / len(delays_list)
            del dow_stats[dow]['delays']
        
        # 数据质量评分
        null_count = sum(1 for r in records if r['arrival_delay_minutes'] is None)
        data_quality_score = ((total_records - null_count) / total_records) * 100 if total_records > 0 else 0
        
        return {
            'origin': origin,
            'destination': destination,
            'route_name': f"{origin}-{destination}",
            'calculation_date': self.calculation_date.isoformat(),
            'data_start_date': data_start_date,
            'data_end_date': data_end_date,
            'data_days_count': data_days,
            'total_services': unique_services,
            'total_records': total_records,
            'weekday_services': weekday_count,
            'weekend_services': weekend_count,
            'on_time_count': on_time_count,
            'on_time_percentage': round(on_time_pct, 2),
            'time_to_3_percentage': round(time_to_3_pct, 2),
            'time_to_5_percentage': round(time_to_5_pct, 2),
            'time_to_10_percentage': round(time_to_10_pct, 2),
            'time_to_15_percentage': round(time_to_15_pct, 2),
            'time_to_30_percentage': round(time_to_30_pct, 2),
            'avg_delay_minutes': round(avg_delay, 2),
            'median_delay_minutes': median_delay,
            'max_delay_minutes': max_delay,
            'std_delay_minutes': round(std_delay, 2),
            'delays_0_5_count': delays_0_5,
            'delays_5_15_count': delays_5_15,
            'delays_15_30_count': delays_15_30,
            'delays_30_60_count': delays_30_60,
            'delays_60_plus_count': delays_60_plus,
            'cancelled_count': cancelled_count,
            'cancelled_percentage': round(cancelled_pct, 2),
            'severe_delay_count': severe_delay_count,
            'reliability_score': round(reliability_score, 2),
            'reliability_grade': reliability_grade,
            'hourly_stats': json.dumps(dict(hourly_stats)),
            'day_of_week_stats': json.dumps(dict(dow_stats)),
            'sample_size': len(delays),
            'data_quality_score': round(data_quality_score, 2)
        }
    
    def save_route_statistics(self, stats: Dict):
        """保存路线统计到数据库"""
        cursor = self.conn.cursor()
        
        # 删除旧的统计记录（如果存在）
        cursor.execute("""
            DELETE FROM route_statistics 
            WHERE origin = ? 
              AND destination = ? 
              AND calculation_date = ?
        """, (stats['origin'], stats['destination'], stats['calculation_date']))
        
        # 插入新记录
        columns = ', '.join(stats.keys())
        placeholders = ', '.join(['?' for _ in stats])
        
        cursor.execute(f"""
            INSERT INTO route_statistics ({columns})
            VALUES ({placeholders})
        """, list(stats.values()))
        
        self.conn.commit()
    
    def calculate_toc_statistics(self, toc_code: str) -> Optional[Dict]:
        """计算TOC运营商统计"""
        cursor = self.conn.cursor()
        
        # 获取该TOC的所有记录
        cursor.execute("""
            SELECT 
                arrival_delay_minutes,
                cancellation_reason,
                date_of_service
            FROM hsp_service_details
            WHERE toc_code = ?
              AND arrival_delay_minutes IS NOT NULL
        """, (toc_code,))
        
        records = [dict(r) for r in cursor.fetchall()]
        
        if not records:
            return None
        
        # 获取服务的路线数
        cursor.execute("""
            SELECT COUNT(DISTINCT origin || '-' || destination) as route_count
            FROM hsp_service_metrics
            WHERE toc_code = ?
        """, (toc_code,))
        route_count = cursor.fetchone()['route_count']
        
        # 日期范围
        dates = [r['date_of_service'] for r in records if r['date_of_service']]
        data_start_date = min(dates) if dates else None
        data_end_date = max(dates) if dates else None
        data_days = (datetime.strptime(data_end_date, '%Y-%m-%d') - 
                     datetime.strptime(data_start_date, '%Y-%m-%d')).days + 1 if data_start_date else 0
        
        # 延误统计
        delays = [r['arrival_delay_minutes'] for r in records]
        
        on_time_count = sum(1 for d in delays if d <= 1)
        ppm_5_count = sum(1 for d in delays if d <= 5)
        ppm_10_count = sum(1 for d in delays if d <= 10)
        
        on_time_pct = (on_time_count / len(delays)) * 100
        ppm_5_pct = (ppm_5_count / len(delays)) * 100
        ppm_10_pct = (ppm_10_count / len(delays)) * 100
        
        avg_delay = sum(delays) / len(delays)
        sorted_delays = sorted(delays)
        median_delay = sorted_delays[len(sorted_delays) // 2]
        
        # 取消率
        cancelled_count = sum(1 for r in records if r['cancellation_reason'])
        cancelled_pct = (cancelled_count / len(records)) * 100
        
        # 可靠性评分
        severe_delay_count = sum(1 for d in delays if d > 60)
        severe_delay_rate = (severe_delay_count / len(delays)) * 100
        
        reliability_score = (
            ppm_5_pct * 0.4 +
            ppm_10_pct * 0.3 +
            (100 - cancelled_pct) * 0.2 +
            (100 - severe_delay_rate) * 0.1
        )
        
        if reliability_score >= 90:
            reliability_grade = 'A'
        elif reliability_score >= 80:
            reliability_grade = 'B'
        elif reliability_score >= 70:
            reliability_grade = 'C'
        elif reliability_score >= 60:
            reliability_grade = 'D'
        else:
            reliability_grade = 'F'
        
        return {
            'toc_code': toc_code,
            'toc_name': None,  # 从元数据获取
            'calculation_date': self.calculation_date.isoformat(),
            'data_start_date': data_start_date,
            'data_end_date': data_end_date,
            'data_days_count': data_days,
            'total_services': len(records),
            'total_routes_served': route_count,
            'on_time_percentage': round(on_time_pct, 2),
            'ppm_5_percentage': round(ppm_5_pct, 2),
            'ppm_10_percentage': round(ppm_10_pct, 2),
            'avg_delay_minutes': round(avg_delay, 2),
            'median_delay_minutes': median_delay,
            'cancelled_percentage': round(cancelled_pct, 2),
            'reliability_score': round(reliability_score, 2),
            'reliability_grade': reliability_grade,
            'route_performance': None  # 详细路线性能
        }
    
    def save_toc_statistics(self, stats: Dict):
        """保存TOC统计"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            DELETE FROM toc_statistics 
            WHERE toc_code = ? 
              AND calculation_date = ?
        """, (stats['toc_code'], stats['calculation_date']))
        
        columns = ', '.join(stats.keys())
        placeholders = ', '.join(['?' for _ in stats])
        
        cursor.execute(f"""
            INSERT INTO toc_statistics ({columns})
            VALUES ({placeholders})
        """, list(stats.values()))
        
        self.conn.commit()
    
    def calculate_all_statistics(self):
        """计算所有统计数据"""
        print_colored("\n" + "="*60, Colors.HEADER)
        print_colored("🚂 RailFair Statistics Calculator", Colors.HEADER + Colors.BOLD)
        print_colored("="*60, Colors.HEADER)
        
        # 获取数据概览
        summary = self.get_data_summary()
        
        if summary['total_records'] == 0:
            print_colored("\n⚠️  No data found in database", Colors.WARNING)
            return
        
        # 计算路线统计
        print_colored(f"\n🛤️  Calculating statistics for {summary['route_count']} routes...", Colors.BLUE)
        
        route_stats_list = []
        for i, (origin, dest) in enumerate(summary['routes'], 1):
            print_colored(f"\n  📍 Route {i}/{summary['route_count']}: {origin}-{dest}", Colors.CYAN)
            
            stats = self.calculate_route_statistics(origin, dest)
            if stats:
                self.save_route_statistics(stats)
                route_stats_list.append(stats)
                
                print_colored(f"     ✅ PPM-5: {stats['time_to_5_percentage']:.1f}%", Colors.GREEN)
                print_colored(f"     ✅ PPM-10: {stats['time_to_10_percentage']:.1f}%", Colors.GREEN)
                print_colored(f"     ✅ Avg delay: {stats['avg_delay_minutes']:.1f} min", Colors.GREEN)
                print_colored(f"     ✅ Grade: {stats['reliability_grade']}", Colors.GREEN)
            else:
                print_colored(f"     ⚠️  No valid data", Colors.WARNING)
        
        # 计算TOC统计
        print_colored(f"\n🏢 Calculating statistics for {summary['unique_tocs']} TOCs...", Colors.BLUE)
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT toc_code FROM hsp_service_details WHERE toc_code IS NOT NULL")
        tocs = [r['toc_code'] for r in cursor.fetchall()]
        
        toc_stats_list = []
        for i, toc in enumerate(tocs, 1):
            print_colored(f"\n  🚂 TOC {i}/{len(tocs)}: {toc}", Colors.CYAN)
            
            stats = self.calculate_toc_statistics(toc)
            if stats:
                self.save_toc_statistics(stats)
                toc_stats_list.append(stats)
                
                print_colored(f"     ✅ PPM-5: {stats['ppm_5_percentage']:.1f}%", Colors.GREEN)
                print_colored(f"     ✅ Grade: {stats['reliability_grade']}", Colors.GREEN)
            else:
                print_colored(f"     ⚠️  No valid data", Colors.WARNING)
        
        # 打印总结
        self.print_summary(route_stats_list, toc_stats_list)
    
    def print_summary(self, route_stats: List[Dict], toc_stats: List[Dict]):
        """打印统计总结"""
        print_colored("\n" + "="*60, Colors.HEADER)
        print_colored("📊 STATISTICS SUMMARY", Colors.HEADER + Colors.BOLD)
        print_colored("="*60, Colors.HEADER)
        
        if route_stats:
            print_colored(f"\n🛤️  ROUTE STATISTICS ({len(route_stats)} routes)", Colors.BLUE)
            print_colored("-" * 60, Colors.BLUE)
            
            # 按可靠性排序
            sorted_routes = sorted(route_stats, key=lambda x: x['reliability_score'], reverse=True)
            
            print(f"\n{'Route':<15} {'PPM-5':<8} {'PPM-10':<8} {'Avg Delay':<12} {'Grade':<6}")
            print("-" * 60)
            for s in sorted_routes:
                print(f"{s['route_name']:<15} {s['time_to_5_percentage']:>6.1f}% {s['time_to_10_percentage']:>7.1f}% "
                      f"{s['avg_delay_minutes']:>10.1f}m {s['reliability_grade']:>5}")
        
        if toc_stats:
            print_colored(f"\n🏢 TOC STATISTICS ({len(toc_stats)} operators)", Colors.BLUE)
            print_colored("-" * 60, Colors.BLUE)
            
            sorted_tocs = sorted(toc_stats, key=lambda x: x['reliability_score'], reverse=True)
            
            print(f"\n{'TOC':<8} {'PPM-5':<8} {'PPM-10':<8} {'Cancel':<8} {'Grade':<6}")
            print("-" * 60)
            for s in sorted_tocs:
                print(f"{s['toc_code']:<8} {s['ppm_5_percentage']:>6.1f}% {s['ppm_10_percentage']:>7.1f}% "
                      f"{s['cancelled_percentage']:>6.1f}% {s['reliability_grade']:>5}")
        
        print_colored("\n✅ Statistics calculation completed!", Colors.GREEN)
        print_colored(f"📅 Calculation date: {self.calculation_date}", Colors.CYAN)

def main():
    """主函数"""
    # 检查数据库路径
    db_path = "data/railfair.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    if not os.path.exists(db_path):
        print_colored(f"❌ Database not found: {db_path}", Colors.FAIL)
        print_colored("   Usage: python3 calculate_stats.py [path/to/railfair.db]", Colors.WARNING)
        sys.exit(1)
    
    # 创建计算器
    calc = StatisticsCalculator(db_path)
    
    try:
        # 连接数据库
        if not calc.connect():
            sys.exit(1)
        
        # 创建统计表
        if not calc.create_statistics_tables():
            sys.exit(1)
        
        # 计算所有统计
        calc.calculate_all_statistics()
        
    except KeyboardInterrupt:
        print_colored("\n\n⚠️  Interrupted by user", Colors.WARNING)
    except Exception as e:
        print_colored(f"\n❌ Error: {e}", Colors.FAIL)
        import traceback
        traceback.print_exc()
    finally:
        calc.close()

if __name__ == "__main__":
    main()
