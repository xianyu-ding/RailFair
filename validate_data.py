#!/usr/bin/env python3
"""
Day 5: 数据验证主脚本
用于验证已收集的HSP数据质量，交叉验证，生成综合报告
"""

import sqlite3
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
import statistics
from typing import Dict, List, Tuple, Optional, Any

class DataValidator:
    """综合数据验证器"""
    
    def __init__(self, db_path: str = "data/railfair.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.validation_results = {
            "summary": {},
            "quality_checks": {},
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
    def run_all_validations(self) -> Dict:
        """运行所有验证检查"""
        print("🔍 Starting comprehensive data validation...")
        print("=" * 60)
        
        # 1. 基础数据统计
        self._validate_basic_stats()
        
        # 2. 数据完整性检查
        self._validate_data_completeness()
        
        # 3. 数据一致性检查
        self._validate_data_consistency()
        
        # 4. 延误数据质量
        self._validate_delay_quality()
        
        # 5. PPM (Public Performance Measure) 计算
        self._validate_ppm()
        
        # 6. 路线覆盖检查
        self._validate_route_coverage()
        
        # 6. 时间分布检查
        self._validate_temporal_distribution()
        
        # 7. TOC数据验证
        self._validate_toc_data()
        
        # 8. 异常值检测
        self._detect_anomalies()
        
        # 9. 数据新鲜度检查
        self._validate_data_freshness()
        
        # 10. 生成建议
        self._generate_recommendations()
        
        return self.validation_results
    
    def _validate_basic_stats(self):
        """基础数据统计"""
        print("\n📊 Basic Statistics:")
        print("-" * 40)
        
        # Metrics表统计
        metrics_count = self.cursor.execute(
            "SELECT COUNT(*) FROM hsp_service_metrics"
        ).fetchone()[0]
        
        # Details表统计
        details_count = self.cursor.execute(
            "SELECT COUNT(*) FROM hsp_service_details"
        ).fetchone()[0]
        
        # 唯一路线数
        unique_routes = self.cursor.execute("""
            SELECT COUNT(DISTINCT origin || '-' || destination) 
            FROM hsp_service_metrics
        """).fetchone()[0]
        
        # 唯一RID数
        unique_rids = self.cursor.execute(
            "SELECT COUNT(DISTINCT rid) FROM hsp_service_details"
        ).fetchone()[0]
        
        # 日期范围
        date_range = self.cursor.execute("""
            SELECT MIN(date_of_service), MAX(date_of_service)
            FROM hsp_service_details
        """).fetchone()
        
        # TOC数量
        toc_count = self.cursor.execute(
            "SELECT COUNT(DISTINCT toc_code) FROM hsp_service_details"
        ).fetchone()[0]
        
        # 站点数量
        location_count = self.cursor.execute(
            "SELECT COUNT(DISTINCT location) FROM hsp_service_details"
        ).fetchone()[0]
        
        self.validation_results["summary"] = {
            "metrics_records": metrics_count,
            "details_records": details_count,
            "unique_routes": unique_routes,
            "unique_services": unique_rids,
            "date_range": {
                "start": date_range[0],
                "end": date_range[1]
            },
            "toc_count": toc_count,
            "location_count": location_count
        }
        
        print(f"✅ Metrics records: {metrics_count:,}")
        print(f"✅ Details records: {details_count:,}")
        print(f"✅ Unique routes: {unique_routes}")
        print(f"✅ Unique services (RIDs): {unique_rids:,}")
        print(f"✅ Date range: {date_range[0]} to {date_range[1]}")
        print(f"✅ TOCs: {toc_count}")
        print(f"✅ Locations: {location_count}")
        
        # 检查是否达到Week 1目标
        if details_count >= 10000:
            print(f"🎯 Week 1 target achieved: {details_count:,} > 10,000 ✅")
        else:
            print(f"⚠️ Below Week 1 target: {details_count:,} < 10,000")
            self.validation_results["warnings"].append(
                f"Data volume below target: {details_count} < 10,000"
            )
    
    def _validate_data_completeness(self):
        """数据完整性检查"""
        print("\n🔍 Data Completeness Check:")
        print("-" * 40)
        
        # 检查NULL值
        null_checks = [
            ("scheduled_departure", "hsp_service_details"),
            ("scheduled_arrival", "hsp_service_details"),
            ("actual_departure", "hsp_service_details"),
            ("actual_arrival", "hsp_service_details"),
            ("departure_delay_minutes", "hsp_service_details"),
            ("arrival_delay_minutes", "hsp_service_details")
        ]
        
        completeness = {}
        for field, table in null_checks:
            total = self.cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            non_null = self.cursor.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {field} IS NOT NULL"
            ).fetchone()[0]
            
            if total > 0:
                percentage = (non_null / total) * 100
                completeness[field] = {
                    "non_null": non_null,
                    "total": total,
                    "percentage": round(percentage, 2)
                }
                
                status = "✅" if percentage > 80 else "⚠️" if percentage > 50 else "❌"
                print(f"{status} {field}: {percentage:.1f}% complete ({non_null:,}/{total:,})")
                
                if percentage < 50:
                    self.validation_results["warnings"].append(
                        f"Low completeness for {field}: {percentage:.1f}%"
                    )
        
        self.validation_results["quality_checks"]["completeness"] = completeness
    
    def _validate_data_consistency(self):
        """数据一致性检查"""
        print("\n🔍 Data Consistency Check:")
        print("-" * 40)
        
        # 检查时间逻辑一致性
        # 注意：在 hsp_service_details 中，每条记录代表一个站点
        # 对于中间站，到达时间 < 出发时间是正常的（列车先到达，然后出发）
        # 我们需要检查的是：同一站点内，出发时间应该 >= 到达时间（如果两者都存在）
        # 或者检查跨站点的时间顺序（这需要更复杂的逻辑）
        
        # 检查同一站点内的时间逻辑：出发时间应该 >= 到达时间（如果两者都存在）
        # 如果出发时间 < 到达时间，这是错误的（除非是跨午夜，但我们已经处理了日期）
        inconsistent_times = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE actual_departure IS NOT NULL 
            AND actual_arrival IS NOT NULL
            AND actual_departure < actual_arrival
            AND CAST(strftime('%s', actual_departure) AS INTEGER) < 
                CAST(strftime('%s', actual_arrival) AS INTEGER) - 60
        """).fetchone()[0]
        
        # 检查跨午夜的情况（出发时间 < 到达时间，但时间差 > 12小时，可能是日期错误）
        cross_midnight_errors = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE actual_departure IS NOT NULL 
            AND actual_arrival IS NOT NULL
            AND actual_departure < actual_arrival
            AND (CAST(strftime('%s', actual_arrival) AS INTEGER) - 
                 CAST(strftime('%s', actual_departure) AS INTEGER)) > 43200
        """).fetchone()[0]
        
        if inconsistent_times > 0:
            print(f"❌ Found {inconsistent_times} records with departure < arrival (time gap > 1 min)")
            self.validation_results["errors"].append(
                f"Time inconsistency: {inconsistent_times} records with departure < arrival"
            )
        else:
            print("✅ All time sequences are consistent")
        
        if cross_midnight_errors > 0:
            print(f"⚠️ Found {cross_midnight_errors} records with potential cross-midnight date issues")
            self.validation_results["warnings"].append(
                f"Potential cross-midnight date issues: {cross_midnight_errors} records"
            )
        
        # 检查延误计算一致性
        delay_check = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE scheduled_arrival IS NOT NULL
            AND actual_arrival IS NOT NULL
            AND arrival_delay_minutes IS NOT NULL
            AND ABS(
                (CAST(strftime('%s', actual_arrival) AS INTEGER) - 
                 CAST(strftime('%s', scheduled_arrival) AS INTEGER)) / 60
                - arrival_delay_minutes
            ) > 2
        """).fetchone()[0]
        
        if delay_check > 0:
            print(f"⚠️ Found {delay_check} records with inconsistent delay calculations")
            self.validation_results["warnings"].append(
                f"Delay calculation inconsistency: {delay_check} records"
            )
        else:
            print("✅ Delay calculations are consistent")
        
        self.validation_results["quality_checks"]["consistency"] = {
            "time_sequence_errors": inconsistent_times,
            "delay_calculation_errors": delay_check
        }
    
    def _validate_delay_quality(self):
        """延误数据质量分析（ORR标准）"""
        print("\n📈 Delay Data Quality (ORR Standards):")
        print("-" * 40)
        
        # 使用SQL聚合计算，避免加载所有记录到内存
        # 注意：cancellation_reason 是 location 级别的，不是服务级别的
        # 只有当整个服务都没有实际时间时，才算作取消
        
        # 获取总记录数
        total_all = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
        """).fetchone()[0]
        
        if total_all == 0:
            print("⚠️ No delay records found")
            return
        
        # 计算取消记录数（没有实际时间和延迟数据）
        cancelled_count = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE actual_departure IS NULL 
            AND actual_arrival IS NULL 
            AND arrival_delay_minutes IS NULL
        """).fetchone()[0]
        
        # 获取有延迟数据的记录数
        total_with_delay = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
        """).fetchone()[0]
        
        if total_with_delay == 0:
            print("⚠️ No delay data available for analysis")
            return
        
        # 使用SQL计算基础统计（均值）
        mean_delay = self.cursor.execute("""
            SELECT AVG(arrival_delay_minutes)
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
        """).fetchone()[0] or 0
        
        # 计算中位数（使用OFFSET方法，对于大数据集可能较慢但更准确）
        # 先获取总数
        delay_count = total_with_delay
        offset = delay_count // 2
        
        median_result = self.cursor.execute("""
            SELECT arrival_delay_minutes
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
            ORDER BY arrival_delay_minutes
            LIMIT 1 OFFSET ?
        """, (offset,)).fetchone()
        median_delay = median_result[0] if median_result else 0
        
        # 计算标准差
        variance = self.cursor.execute("""
            SELECT AVG((arrival_delay_minutes - ?) * (arrival_delay_minutes - ?))
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
        """, (mean_delay, mean_delay)).fetchone()[0]
        stdev_delay = (variance ** 0.5) if variance is not None and variance >= 0 else 0
        
        # ORR 标准分布统计（使用SQL聚合）
        orr_stats = self.cursor.execute("""
            SELECT 
                SUM(CASE WHEN arrival_delay_minutes <= 1 THEN 1 ELSE 0 END) as on_time,
                SUM(CASE WHEN arrival_delay_minutes <= 3 THEN 1 ELSE 0 END) as time_to_3,
                SUM(CASE WHEN arrival_delay_minutes <= 15 THEN 1 ELSE 0 END) as time_to_15,
                SUM(CASE WHEN arrival_delay_minutes <= 30 THEN 1 ELSE 0 END) as time_to_30,
                SUM(CASE WHEN arrival_delay_minutes <= 60 THEN 1 ELSE 0 END) as time_to_60,
                SUM(CASE WHEN arrival_delay_minutes > 60 THEN 1 ELSE 0 END) as over_60
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
        """).fetchone()
        
        on_time = orr_stats[0] or 0
        time_to_3 = orr_stats[1] or 0
        time_to_15 = orr_stats[2] or 0
        time_to_30 = orr_stats[3] or 0
        time_to_60 = orr_stats[4] or 0
        over_60 = orr_stats[5] or 0
        
        # 计算百分比（基于所有非取消记录）
        print(f"📊 Total records: {total_all:,}")
        if cancelled_count > 0:
            print(f"🚫 Cancelled services: {cancelled_count:,} ({cancelled_count/total_all*100:.1f}%)")
        print(f"📊 Records with delay data: {total_with_delay:,}")
        print(f"📊 Mean delay: {mean_delay:.1f} minutes")
        print(f"📊 Median delay: {median_delay:.1f} minutes")
        print(f"📊 Std deviation: {stdev_delay:.1f} minutes")
        print(f"\n📊 ORR Performance Metrics:")
        print(f"  ✅ On Time (≤1 min): {on_time:,} ({on_time/total_with_delay*100:.1f}%)")
        print(f"  ⏱️  Time to 3 min (≤3 min): {time_to_3:,} ({time_to_3/total_with_delay*100:.1f}%)")
        print(f"  ⏱️  Time to 15 min (≤15 min): {time_to_15:,} ({time_to_15/total_with_delay*100:.1f}%)")
        print(f"  ⏱️  Time to 30 min (≤30 min): {time_to_30:,} ({time_to_30/total_with_delay*100:.1f}%)")
        print(f"  ⏱️  Time to 60 min (≤60 min): {time_to_60:,} ({time_to_60/total_with_delay*100:.1f}%)")
        print(f"  ❌ Over 60 min: {over_60:,} ({over_60/total_with_delay*100:.1f}%)")
        
        if cancelled_count > 0:
            print(f"  🚫 Cancelled: {cancelled_count:,} ({cancelled_count/total_all*100:.1f}%)")
        
        # 极端值检测
        if over_60 > 0:
            print(f"\n⚠️ Found {over_60} extreme delays (>60 min)")
            self.validation_results["warnings"].append(
                f"Extreme delays detected: {over_60} records"
            )
        
        self.validation_results["quality_checks"]["delay_quality"] = {
            "total_records": total_all,
            "cancelled_count": cancelled_count,
            "records_with_delay": total_with_delay,
            "mean_delay": round(mean_delay, 2),
            "median_delay": round(median_delay, 2),
            "std_deviation": round(stdev_delay, 2),
            "orr_metrics": {
                "on_time": on_time,
                "on_time_rate": round(on_time/total_with_delay*100, 2) if total_with_delay > 0 else 0,
                "time_to_3": time_to_3,
                "time_to_3_rate": round(time_to_3/total_with_delay*100, 2) if total_with_delay > 0 else 0,
                "time_to_15": time_to_15,
                "time_to_15_rate": round(time_to_15/total_with_delay*100, 2) if total_with_delay > 0 else 0,
                "time_to_30": time_to_30,
                "time_to_30_rate": round(time_to_30/total_with_delay*100, 2) if total_with_delay > 0 else 0,
                "time_to_60": time_to_60,
                "time_to_60_rate": round(time_to_60/total_with_delay*100, 2) if total_with_delay > 0 else 0,
                "over_60": over_60,
                "over_60_rate": round(over_60/total_with_delay*100, 2) if total_with_delay > 0 else 0
            },
            "cancelled_rate": round(cancelled_count/total_all*100, 2) if total_all > 0 else 0
        }
    
    def _validate_ppm(self):
        """计算 PPM (Public Performance Measure) - 终点站准点率"""
        print("\n🎯 PPM (Public Performance Measure) Analysis:")
        print("-" * 40)
        
        # 获取每个服务的终点站（最后一个 location，按 scheduled_arrival 排序）
        terminal_stations = self.cursor.execute("""
            WITH service_terminals AS (
                SELECT 
                    rid,
                    location,
                    arrival_delay_minutes,
                    scheduled_arrival,
                    actual_arrival,
                    actual_departure,
                    actual_arrival as actual_arr,
                    cancellation_reason,
                    ROW_NUMBER() OVER (
                        PARTITION BY rid 
                        ORDER BY scheduled_arrival DESC
                    ) as rn
                FROM hsp_service_details
                WHERE scheduled_arrival IS NOT NULL
            )
            SELECT 
                rid,
                location,
                arrival_delay_minutes,
                scheduled_arrival,
                actual_arrival,
                cancellation_reason
            FROM service_terminals
            WHERE rn = 1
        """).fetchall()
        
        if not terminal_stations:
            print("⚠️ No terminal station data found")
            return
        
        total_services = len(terminal_stations)
        
        # 排除取消的服务（没有实际到达时间）
        valid_services = [
            s for s in terminal_stations
            if s['actual_arrival'] is not None
        ]
        
        cancelled_services = total_services - len(valid_services)
        
        # 计算 PPM-5 (5分钟内) 和 PPM-10 (10分钟内)
        ppm_5_count = sum(
            1 for s in valid_services
            if s['arrival_delay_minutes'] is not None and s['arrival_delay_minutes'] <= 5
        )
        ppm_10_count = sum(
            1 for s in valid_services
            if s['arrival_delay_minutes'] is not None and s['arrival_delay_minutes'] <= 10
        )
        
        # 计算百分比（基于所有有效服务，不包括取消的）
        valid_count = len(valid_services)
        ppm_5_rate = (ppm_5_count / valid_count * 100) if valid_count > 0 else 0
        ppm_10_rate = (ppm_10_count / valid_count * 100) if valid_count > 0 else 0
        
        print(f"📊 Total services: {total_services:,}")
        if cancelled_services > 0:
            print(f"🚫 Cancelled services: {cancelled_services:,} ({cancelled_services/total_services*100:.1f}%)")
        print(f"📊 Valid services (with arrival data): {valid_count:,}")
        print(f"\n📊 PPM Metrics:")
        print(f"  ✅ PPM-5 (≤5 min): {ppm_5_count:,} ({ppm_5_rate:.1f}%)")
        print(f"  ✅ PPM-10 (≤10 min): {ppm_10_count:,} ({ppm_10_rate:.1f}%)")
        
        # 按 TOC 分组计算 PPM
        print(f"\n📊 PPM by TOC:")
        toc_ppm = self.cursor.execute("""
            WITH service_terminals AS (
                SELECT 
                    d.rid,
                    d.toc_code,
                    d.location,
                    d.arrival_delay_minutes,
                    d.actual_arrival,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.rid 
                        ORDER BY d.scheduled_arrival DESC
                    ) as rn
                FROM hsp_service_details d
                WHERE d.scheduled_arrival IS NOT NULL
            )
            SELECT 
                toc_code,
                COUNT(*) as total_services,
                SUM(CASE WHEN actual_arrival IS NULL THEN 1 ELSE 0 END) as cancelled,
                SUM(CASE WHEN actual_arrival IS NOT NULL AND arrival_delay_minutes <= 5 THEN 1 ELSE 0 END) as ppm_5,
                SUM(CASE WHEN actual_arrival IS NOT NULL AND arrival_delay_minutes <= 10 THEN 1 ELSE 0 END) as ppm_10,
                COUNT(CASE WHEN actual_arrival IS NOT NULL THEN 1 END) as valid_services
            FROM service_terminals
            WHERE rn = 1
            GROUP BY toc_code
            ORDER BY total_services DESC
            LIMIT 10
        """).fetchall()
        
        for toc, total, cancelled, ppm5, ppm10, valid in toc_ppm:
            if valid > 0:
                ppm5_rate = (ppm5 / valid * 100)
                ppm10_rate = (ppm10 / valid * 100)
                cancelled_str = f", {cancelled:,} cancelled" if cancelled > 0 else ""
                print(f"  {toc}: {total:,} services{cancelled_str}, PPM-5: {ppm5_rate:.1f}%, PPM-10: {ppm10_rate:.1f}%")
        
        # 保存到结果
        self.validation_results["quality_checks"]["ppm"] = {
            "total_services": total_services,
            "cancelled_services": cancelled_services,
            "valid_services": valid_count,
            "ppm_5": {
                "count": ppm_5_count,
                "rate": round(ppm_5_rate, 2)
            },
            "ppm_10": {
                "count": ppm_10_count,
                "rate": round(ppm_10_rate, 2)
            },
            "toc_breakdown": {
                toc: {
                    "total_services": total,
                    "cancelled": cancelled,
                    "valid_services": valid,
                    "ppm_5_rate": round((ppm5 / valid * 100), 2) if valid > 0 else 0,
                    "ppm_10_rate": round((ppm10 / valid * 100), 2) if valid > 0 else 0
                }
                for toc, total, cancelled, ppm5, ppm10, valid in toc_ppm
            }
        }
    
    def _validate_route_coverage(self):
        """路线覆盖检查"""
        print("\n🛤️ Route Coverage Analysis:")
        print("-" * 40)
        
        # 预期的10条路线（使用正确的车站代码）
        # 注意：已修复的路线（MYB-BHM→EUS-BHM, MAN-LIV→MCV-LIV, MAN-LDS→MCV-LDS）
        expected_routes = [
            ("EUS", "MAN"),  # London Euston → Manchester
            ("KGX", "EDB"),  # King's Cross → Edinburgh (EDB, not EDR)
            ("PAD", "BRI"),  # Paddington → Bristol
            ("LST", "NRW"),  # Liverpool St → Norwich
            ("EUS", "BHM"),  # London Euston → Birmingham (replaces MYB-BHM)
            ("MCV", "LIV"),  # Manchester Victoria → Liverpool (replaces MAN-LIV)
            ("BHM", "MAN"),  # Birmingham → Manchester
            ("BRI", "BHM"),  # Bristol → Birmingham
            ("EDB", "GLC"),  # Edinburgh → Glasgow (EDB, not EDR)
            ("MCV", "LDS")   # Manchester Victoria → Leeds (replaces MAN-LDS)
        ]
        
        # 检查每条路线的数据量
        route_coverage = {}
        missing_routes = []
        low_data_routes = []
        
        for origin, destination in expected_routes:
            # Query from hsp_service_metrics which has origin and destination
            count = self.cursor.execute("""
                SELECT COUNT(*) 
                FROM hsp_service_metrics
                WHERE origin = ? AND destination = ?
            """, (origin, destination)).fetchone()[0]
            
            route_name = f"{origin}-{destination}"
            route_coverage[route_name] = count
            
            if count == 0:
                missing_routes.append(route_name)
                print(f"❌ {route_name}: No data")
            elif count < 100:
                low_data_routes.append(route_name)
                print(f"⚠️ {route_name}: {count} services (low)")
            else:
                print(f"✅ {route_name}: {count} services")
        
        if missing_routes:
            self.validation_results["errors"].append(
                f"Missing routes: {', '.join(missing_routes)}"
            )
        
        if low_data_routes:
            self.validation_results["warnings"].append(
                f"Low data routes: {', '.join(low_data_routes)}"
            )
        
        self.validation_results["quality_checks"]["route_coverage"] = route_coverage
        
        # 覆盖率统计
        covered_routes = len([r for r in route_coverage.values() if r > 0])
        coverage_rate = (covered_routes / len(expected_routes)) * 100
        print(f"\n📊 Route coverage: {covered_routes}/{len(expected_routes)} ({coverage_rate:.0f}%)")
    
    def _validate_temporal_distribution(self):
        """时间分布检查"""
        print("\n📅 Temporal Distribution:")
        print("-" * 40)
        
        # 按日期分布
        daily_distribution = self.cursor.execute("""
            SELECT date_of_service, COUNT(*) as count
            FROM hsp_service_details
            GROUP BY date_of_service
            ORDER BY date_of_service
        """).fetchall()
        
        if daily_distribution:
            dates = [d[0] for d in daily_distribution]
            counts = [d[1] for d in daily_distribution]
            
            avg_daily = statistics.mean(counts)
            min_daily = min(counts)
            max_daily = max(counts)
            
            print(f"📊 Date range: {dates[0]} to {dates[-1]}")
            print(f"📊 Total days: {len(dates)}")
            print(f"📊 Avg records/day: {avg_daily:.0f}")
            print(f"📊 Min records/day: {min_daily}")
            print(f"📊 Max records/day: {max_daily}")
            
            # 检查数据空缺
            from datetime import datetime
            date_set = set(dates)
            start_date = datetime.strptime(dates[0], "%Y-%m-%d")
            end_date = datetime.strptime(dates[-1], "%Y-%m-%d")
            
            expected_days = (end_date - start_date).days + 1
            missing_days = expected_days - len(dates)
            
            if missing_days > 0:
                print(f"⚠️ Missing data for {missing_days} days")
                self.validation_results["warnings"].append(
                    f"Missing data for {missing_days} days"
                )
            
            # 按星期分布
            weekday_dist = self.cursor.execute("""
                SELECT 
                    CASE cast(strftime('%w', date_of_service) as integer)
                        WHEN 0 THEN 'Sunday'
                        WHEN 1 THEN 'Monday'
                        WHEN 2 THEN 'Tuesday'
                        WHEN 3 THEN 'Wednesday'
                        WHEN 4 THEN 'Thursday'
                        WHEN 5 THEN 'Friday'
                        WHEN 6 THEN 'Saturday'
                    END as weekday,
                    COUNT(*) as count
                FROM hsp_service_details
                GROUP BY weekday
                ORDER BY 
                    CASE weekday
                        WHEN 'Monday' THEN 1
                        WHEN 'Tuesday' THEN 2
                        WHEN 'Wednesday' THEN 3
                        WHEN 'Thursday' THEN 4
                        WHEN 'Friday' THEN 5
                        WHEN 'Saturday' THEN 6
                        WHEN 'Sunday' THEN 7
                    END
            """).fetchall()
            
            print("\n📊 Weekday distribution:")
            for day, count in weekday_dist:
                print(f"  {day}: {count:,} records")
            
            self.validation_results["quality_checks"]["temporal_distribution"] = {
                "total_days": len(dates),
                "missing_days": missing_days,
                "avg_daily_records": round(avg_daily, 0),
                "weekday_distribution": dict(weekday_dist)
            }
    
    def _validate_toc_data(self):
        """TOC数据验证"""
        print("\n🚂 TOC (Train Operating Company) Analysis:")
        print("-" * 40)
        
        # TOC 统计（使用 ORR 标准：≤1 min 为准点）
        # 注意：cancellation_reason 是 location 级别的，不是服务级别的
        # 只有完全没有实际时间的记录才算取消
        toc_stats = self.cursor.execute("""
            SELECT 
                toc_code,
                COUNT(*) as total_services,
                SUM(CASE WHEN actual_departure IS NULL AND actual_arrival IS NULL AND arrival_delay_minutes IS NULL THEN 1 ELSE 0 END) as cancelled,
                COUNT(CASE WHEN arrival_delay_minutes IS NOT NULL THEN 1 END) as services_with_delay,
                AVG(arrival_delay_minutes) as avg_delay,
                SUM(CASE WHEN arrival_delay_minutes <= 1 THEN 1 ELSE 0 END) * 100.0 / 
                    NULLIF(COUNT(CASE WHEN arrival_delay_minutes IS NOT NULL THEN 1 END), 0) as on_time_rate
            FROM hsp_service_details
            GROUP BY toc_code
            ORDER BY total_services DESC
        """).fetchall()
        
        toc_analysis = {}
        for toc, total_services, cancelled, services_with_delay, avg_delay, on_time_rate in toc_stats[:10]:  # Top 10 TOCs
            cancelled_str = f", {cancelled:,} cancelled" if cancelled > 0 else ""
            print(f"  {toc}: {total_services:,} services{cancelled_str}, {avg_delay:.1f}min avg delay, {on_time_rate:.1f}% on-time (≤1 min)")
            toc_analysis[toc] = {
                "total_services": total_services,
                "cancelled": cancelled,
                "services_with_delay": services_with_delay,
                "avg_delay": round(avg_delay, 2) if avg_delay else None,
                "on_time_rate": round(on_time_rate, 2) if on_time_rate else None
            }
        
        self.validation_results["quality_checks"]["toc_analysis"] = toc_analysis
        
        # 检查是否有未知TOC
        unknown_tocs = self.cursor.execute("""
            SELECT DISTINCT toc_code
            FROM hsp_service_details
            WHERE toc_code IS NULL OR toc_code = ''
        """).fetchall()
        
        if unknown_tocs:
            print(f"\n⚠️ Found {len(unknown_tocs)} records with unknown TOC")
            self.validation_results["warnings"].append(
                f"Unknown TOC codes: {len(unknown_tocs)} records"
            )
    
    def _detect_anomalies(self):
        """异常值检测"""
        print("\n🔍 Anomaly Detection:")
        print("-" * 40)
        
        anomalies = []
        
        # 1. 极端延误 (>180分钟)
        extreme_delays = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE ABS(arrival_delay_minutes) > 180
        """).fetchone()[0]
        
        if extreme_delays > 0:
            print(f"⚠️ Extreme delays (>3 hours): {extreme_delays} records")
            anomalies.append(f"Extreme delays: {extreme_delays}")
        
        # 2. 重复记录
        duplicates = self.cursor.execute("""
            SELECT rid, location, COUNT(*) as count
            FROM hsp_service_details
            GROUP BY rid, location
            HAVING count > 1
        """).fetchall()
        
        if duplicates:
            print(f"⚠️ Duplicate records: {len(duplicates)} combinations")
            anomalies.append(f"Duplicates: {len(duplicates)}")
        
        # 3. 未来日期
        future_dates = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE date_of_service > date('now')
        """).fetchone()[0]
        
        if future_dates > 0:
            print(f"❌ Future dates: {future_dates} records")
            anomalies.append(f"Future dates: {future_dates}")
            self.validation_results["errors"].append(
                f"Data contains future dates: {future_dates} records"
            )
        
        # 4. 无效CRS代码（非3字母）
        invalid_crs = self.cursor.execute("""
            SELECT COUNT(*) FROM hsp_service_details
            WHERE LENGTH(location) != 3
        """).fetchone()[0]
        
        if invalid_crs > 0:
            print(f"⚠️ Invalid CRS codes: {invalid_crs} records")
            anomalies.append(f"Invalid CRS: {invalid_crs}")
        
        if not anomalies:
            print("✅ No significant anomalies detected")
        
        self.validation_results["quality_checks"]["anomalies"] = anomalies
    
    def _validate_data_freshness(self):
        """数据新鲜度检查"""
        print("\n🕐 Data Freshness Check:")
        print("-" * 40)
        
        # 服务日期范围（实际数据的时间范围）
        service_date_range = self.cursor.execute("""
            SELECT MIN(date_of_service) as min_date,
                   MAX(date_of_service) as max_date
            FROM hsp_service_details
        """).fetchone()
        
        # 数据收集时间（fetch_timestamp）
        fetch_time_range = self.cursor.execute("""
            SELECT MAX(fetch_timestamp) as latest,
                   MIN(fetch_timestamp) as earliest
            FROM hsp_service_details
        """).fetchone()
        
        if service_date_range and service_date_range['min_date']:
            print(f"📅 Service date range: {service_date_range['min_date']} to {service_date_range['max_date']}")
        
        if fetch_time_range and fetch_time_range['latest']:
            latest = datetime.fromisoformat(fetch_time_range['latest'].replace('Z', '+00:00'))
            earliest = datetime.fromisoformat(fetch_time_range['earliest'].replace('Z', '+00:00'))
            now = datetime.now()
            
            age_hours = (now - latest).total_seconds() / 3600
            collection_span = (latest - earliest).total_seconds() / 3600
            
            print(f"📊 Latest fetch time: {fetch_time_range['latest']}")
            print(f"📊 Earliest fetch time: {fetch_time_range['earliest']}")
            print(f"📊 Data age: {age_hours:.1f} hours")
            print(f"📊 Collection span: {collection_span:.1f} hours")
            
            if age_hours < 24:
                print("✅ Data is fresh (< 24 hours old)")
            elif age_hours < 72:
                print("⚠️ Data is relatively fresh (< 72 hours old)")
            else:
                print("❌ Data is stale (> 72 hours old)")
                self.validation_results["warnings"].append(
                    f"Stale data: {age_hours:.1f} hours old"
                )
            
            freshness_data = {
                "service_date_range": {
                    "min": service_date_range['min_date'] if service_date_range and service_date_range['min_date'] else None,
                    "max": service_date_range['max_date'] if service_date_range and service_date_range['max_date'] else None
                },
                "fetch_time_range": {
                    "latest": fetch_time_range['latest'],
                    "earliest": fetch_time_range['earliest']
                },
                "age_hours": round(age_hours, 1),
                "collection_span_hours": round(collection_span, 1)
            }
            self.validation_results["quality_checks"]["freshness"] = freshness_data
    
    def _generate_recommendations(self):
        """生成改进建议"""
        print("\n💡 Recommendations:")
        print("-" * 40)
        
        recommendations = []
        
        # 基于验证结果生成建议
        if self.validation_results["summary"]["details_records"] < 10000:
            recommendations.append(
                "📈 Collect more data: Current volume is below 10,000 records target"
            )
        
        if self.validation_results["summary"]["unique_routes"] < 10:
            recommendations.append(
                "🛤️ Expand route coverage: Less than 10 routes have data"
            )
        
        completeness = self.validation_results.get("quality_checks", {}).get("completeness", {})
        for field, stats in completeness.items():
            if stats.get("percentage", 100) < 50:
                recommendations.append(
                    f"🔧 Improve {field} data collection: Only {stats['percentage']}% complete"
                )
        
        if len(self.validation_results.get("errors", [])) > 0:
            recommendations.append(
                "❌ Address critical errors before proceeding with modeling"
            )
        
        if len(self.validation_results.get("warnings", [])) > 3:
            recommendations.append(
                "⚠️ Review and address data quality warnings"
            )
        
        # 额外建议
        recommendations.extend([
            "📊 Consider collecting weekend data for better coverage",
            "🔄 Implement incremental data updates for freshness",
            "📝 Add metadata collection for TOC and station information",
            "🎯 Focus on high-traffic routes for initial predictions"
        ])
        
        for i, rec in enumerate(recommendations[:5], 1):  # Top 5 recommendations
            print(f"{i}. {rec}")
        
        self.validation_results["recommendations"] = recommendations
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 70)
        report.append("DATA VALIDATION REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        
        # Summary
        report.append("\n📊 SUMMARY")
        report.append("-" * 40)
        summary = self.validation_results["summary"]
        report.append(f"Total Records: {summary.get('details_records', 0):,}")
        report.append(f"Unique Routes: {summary.get('unique_routes', 0)}")
        report.append(f"Unique Services: {summary.get('unique_services', 0):,}")
        report.append(f"Date Range: {summary.get('date_range', {}).get('start')} to {summary.get('date_range', {}).get('end')}")
        report.append(f"TOCs: {summary.get('toc_count', 0)}")
        report.append(f"Locations: {summary.get('location_count', 0)}")
        
        # Quality Score
        report.append("\n📈 QUALITY SCORE")
        report.append("-" * 40)
        
        # Calculate quality score
        score = 100
        score -= len(self.validation_results.get("errors", [])) * 10
        score -= len(self.validation_results.get("warnings", [])) * 2
        score = max(0, score)
        
        report.append(f"Overall Quality Score: {score}/100")
        report.append(f"Critical Errors: {len(self.validation_results.get('errors', []))}")
        report.append(f"Warnings: {len(self.validation_results.get('warnings', []))}")
        
        # Errors
        if self.validation_results.get("errors"):
            report.append("\n❌ CRITICAL ERRORS")
            report.append("-" * 40)
            for error in self.validation_results["errors"]:
                report.append(f"• {error}")
        
        # Warnings
        if self.validation_results.get("warnings"):
            report.append("\n⚠️  WARNINGS")
            report.append("-" * 40)
            for warning in self.validation_results["warnings"]:
                report.append(f"• {warning}")
        
        # Recommendations
        if self.validation_results.get("recommendations"):
            report.append("\n💡 RECOMMENDATIONS")
            report.append("-" * 40)
            for i, rec in enumerate(self.validation_results["recommendations"][:5], 1):
                report.append(f"{i}. {rec}")
        
        # Success Criteria
        report.append("\n✅ WEEK 1 SUCCESS CRITERIA")
        report.append("-" * 40)
        
        criteria_met = 0
        criteria_total = 3
        
        if summary.get("details_records", 0) >= 10000:
            report.append("✅ Data volume: ≥10,000 records")
            criteria_met += 1
        else:
            report.append(f"❌ Data volume: {summary.get('details_records', 0):,} < 10,000 records")
        
        if summary.get("unique_routes", 0) >= 10:
            report.append("✅ Route coverage: ≥10 routes")
            criteria_met += 1
        else:
            report.append(f"❌ Route coverage: {summary.get('unique_routes', 0)} < 10 routes")
        
        if score >= 70:
            report.append(f"✅ Quality validation: {score}/100 ≥ 70")
            criteria_met += 1
        else:
            report.append(f"❌ Quality validation: {score}/100 < 70")
        
        report.append(f"\n📊 Success Rate: {criteria_met}/{criteria_total} ({criteria_met/criteria_total*100:.0f}%)")
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\n📄 Report saved to: {output_file}")
        
        return report_text
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="Validate collected HSP data")
    parser.add_argument(
        "--db",
        default="data/railfair.db",
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--output",
        default="data/validation_report.txt",
        help="Output report file"
    )
    parser.add_argument(
        "--json",
        default="data/validation_results.json",
        help="Output JSON file"
    )
    
    args = parser.parse_args()
    
    # 确保数据目录存在
    Path("data").mkdir(exist_ok=True)
    
    # 运行验证
    validator = DataValidator(args.db)
    
    try:
        results = validator.run_all_validations()
        report = validator.generate_report(args.output)
        print("\n" + "=" * 60)
        print("📋 VALIDATION COMPLETE")
        print("=" * 60)
        
        # 打印总结
        score = 100 - len(results.get("errors", [])) * 10 - len(results.get("warnings", [])) * 2
        score = max(0, score)
        
        if score >= 80:
            print(f"✅ Data quality is GOOD ({score}/100)")
        elif score >= 60:
            print(f"⚠️ Data quality is ACCEPTABLE ({score}/100)")
        else:
            print(f"❌ Data quality is POOR ({score}/100)")
        
        # 保存 JSON 文件（如果指定了）
        if args.json:
            import json
            with open(args.json, 'w') as f:
                json.dump(validator.validation_results, f, indent=2, default=str)
            print(f"\n📄 Full report saved to: {args.output}")
            print(f"📊 JSON results saved to: {args.json}")
        else:
            print(f"\n📄 Full report saved to: {args.output}")
        
    finally:
        validator.close()


if __name__ == "__main__":
    main()
