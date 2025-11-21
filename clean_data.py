#!/usr/bin/env python3
"""
数据清洗脚本
处理异常值、缺失数据和不一致的数据
"""

import sqlite3
import argparse
from datetime import datetime
from typing import Dict, List, Tuple


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self, db_path: str, dry_run: bool = True):
        self.db_path = db_path
        self.dry_run = dry_run
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.stats = {
            'extreme_delays_removed': 0,
            'time_inconsistencies_fixed': 0,
            'missing_delays_recalculated': 0,
            'invalid_records_removed': 0,
            'total_records_processed': 0
        }
    
    def clean_extreme_delays(self, max_delay_minutes: int = 180) -> int:
        """
        处理极端延迟值
        
        Args:
            max_delay_minutes: 最大允许延迟（分钟），超过此值的记录将被标记或删除
        
        Returns:
            处理的记录数
        """
        print(f"\n🔍 检查极端延迟值（> {max_delay_minutes} 分钟）...")
        
        # 查找极端延迟的记录
        extreme_records = self.cursor.execute("""
            SELECT id, rid, location, arrival_delay_minutes, 
                   scheduled_arrival, actual_arrival
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
              AND ABS(arrival_delay_minutes) > ?
        """, (max_delay_minutes,)).fetchall()
        
        count = len(extreme_records)
        print(f"   找到 {count} 条极端延迟记录")
        
        if count > 0 and not self.dry_run:
            # 对于极端延迟，我们有几个选择：
            # 1. 删除记录
            # 2. 设置为 NULL（标记为缺失）
            # 3. 重新计算延迟（如果时间数据存在）
            
            fixed = 0
            removed = 0
            
            for record in extreme_records:
                rid = record['rid']
                location = record['location']
                delay = record['arrival_delay_minutes']
                scheduled = record['scheduled_arrival']
                actual = record['actual_arrival']
                
                # 如果时间数据存在，尝试重新计算延迟
                if scheduled and actual:
                    try:
                        # 重新计算延迟
                        scheduled_dt = datetime.fromisoformat(scheduled.replace('Z', '+00:00'))
                        actual_dt = datetime.fromisoformat(actual.replace('Z', '+00:00'))
                        
                        # 检查日期是否合理（actual 不应该比 scheduled 早超过 1 天）
                        # 如果 actual 的日期比 scheduled 早，可能是跨午夜处理错误
                        if actual_dt.date() < scheduled_dt.date():
                            # 检查是否是跨午夜的情况（scheduled 很晚，actual 很早）
                            if scheduled_dt.hour >= 22 and actual_dt.hour < 6:
                                # 跨午夜，actual 应该是第二天
                                from datetime import timedelta
                                actual_dt = actual_dt + timedelta(days=1)
                            else:
                                # 日期错误，设置为 NULL
                                self.cursor.execute("""
                                    UPDATE hsp_service_details
                                    SET arrival_delay_minutes = NULL,
                                        actual_arrival = NULL
                                    WHERE id = ?
                                """, (record['id'],))
                                removed += 1
                                continue
                        
                        delta = actual_dt - scheduled_dt
                        new_delay = int(delta.total_seconds() / 60)
                        
                        # 如果重新计算后的延迟合理，更新它
                        if abs(new_delay) <= max_delay_minutes:
                            self.cursor.execute("""
                                UPDATE hsp_service_details
                                SET arrival_delay_minutes = ?,
                                    actual_arrival = ?
                                WHERE id = ?
                            """, (new_delay, actual_dt.isoformat(), record['id']))
                            fixed += 1
                        else:
                            # 重新计算后仍然极端，设置为 NULL
                            self.cursor.execute("""
                                UPDATE hsp_service_details
                                SET arrival_delay_minutes = NULL
                                WHERE id = ?
                            """, (record['id'],))
                            removed += 1
                    except Exception as e:
                        # 解析失败，设置为 NULL
                        self.cursor.execute("""
                            UPDATE hsp_service_details
                            SET arrival_delay_minutes = NULL
                            WHERE id = ?
                        """, (record['id'],))
                        removed += 1
                else:
                    # 没有时间数据，设置为 NULL
                    self.cursor.execute("""
                        UPDATE hsp_service_details
                        SET arrival_delay_minutes = NULL
                        WHERE id = ?
                    """, (record['id'],))
                    removed += 1
            
            self.conn.commit()
            print(f"   ✅ 修复了 {fixed} 条记录")
            print(f"   ⚠️  移除了 {removed} 条记录的延迟数据（设置为 NULL）")
            self.stats['extreme_delays_removed'] = removed
            return fixed + removed
        
        return 0
    
    def fix_time_inconsistencies(self) -> int:
        """修复时间不一致的记录"""
        print(f"\n🔍 检查时间不一致的记录...")
        
        # 查找时间不一致的记录（departure < arrival 且时间差 > 1 分钟）
        inconsistent = self.cursor.execute("""
            SELECT id, rid, location, actual_departure, actual_arrival,
                   scheduled_departure, scheduled_arrival
            FROM hsp_service_details
            WHERE actual_departure IS NOT NULL 
              AND actual_arrival IS NOT NULL
              AND actual_departure < actual_arrival
              AND (julianday(actual_arrival) - julianday(actual_departure)) * 1440 > 1
        """).fetchall()
        
        count = len(inconsistent)
        print(f"   找到 {count} 条时间不一致记录")
        
        if count > 0 and not self.dry_run:
            fixed = 0
            for record in inconsistent:
                # 检查是否是跨午夜的情况
                dep = datetime.fromisoformat(record['actual_departure'].replace('Z', '+00:00'))
                arr = datetime.fromisoformat(record['actual_arrival'].replace('Z', '+00:00'))
                
                # 如果时间差超过 12 小时，可能是跨午夜或数据错误
                time_diff_hours = (arr - dep).total_seconds() / 3600
                
                if time_diff_hours > 12:
                    # 可能是跨午夜，检查日期
                    if dep.hour >= 22 and arr.hour < 6:
                        # 跨午夜，调整日期
                        from datetime import timedelta
                        if arr.date() == dep.date():
                            # 到达时间应该是第二天
                            new_arr = arr + timedelta(days=1)
                            self.cursor.execute("""
                                UPDATE hsp_service_details
                                SET actual_arrival = ?
                                WHERE id = ?
                            """, (new_arr.isoformat(), record['id']))
                            fixed += 1
                    else:
                        # 数据错误，设置为 NULL
                        self.cursor.execute("""
                            UPDATE hsp_service_details
                            SET actual_arrival = NULL, arrival_delay_minutes = NULL
                            WHERE id = ?
                        """, (record['id'],))
                else:
                    # 时间差合理，但顺序错误，交换它们
                    self.cursor.execute("""
                        UPDATE hsp_service_details
                        SET actual_departure = ?,
                            actual_arrival = ?
                        WHERE id = ?
                    """, (record['actual_arrival'], record['actual_departure'], record['id']))
                    fixed += 1
            
            self.conn.commit()
            print(f"   ✅ 修复了 {fixed} 条记录")
            self.stats['time_inconsistencies_fixed'] = fixed
            return fixed
        
        return 0
    
    def recalculate_missing_delays(self) -> int:
        """重新计算缺失的延迟值"""
        print(f"\n🔍 检查缺失的延迟值...")
        
        # 查找有时间数据但没有延迟数据的记录
        missing_delays = self.cursor.execute("""
            SELECT id, scheduled_arrival, actual_arrival, 
                   scheduled_departure, actual_departure
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NULL
              AND scheduled_arrival IS NOT NULL
              AND actual_arrival IS NOT NULL
        """).fetchall()
        
        count = len(missing_delays)
        print(f"   找到 {count} 条缺失延迟值的记录（有时间数据）")
        
        if count > 0 and not self.dry_run:
            calculated = 0
            for record in missing_delays:
                try:
                    scheduled = datetime.fromisoformat(record['scheduled_arrival'].replace('Z', '+00:00'))
                    actual = datetime.fromisoformat(record['actual_arrival'].replace('Z', '+00:00'))
                    delta = actual - scheduled
                    delay_minutes = int(delta.total_seconds() / 60)
                    
                    # 只更新合理的延迟值
                    if abs(delay_minutes) <= 180:
                        self.cursor.execute("""
                            UPDATE hsp_service_details
                            SET arrival_delay_minutes = ?
                            WHERE id = ?
                        """, (delay_minutes, record['id']))
                        calculated += 1
                except Exception as e:
                    # 解析失败，跳过
                    continue
            
            # 同样处理 departure_delay_minutes
            missing_dep_delays = self.cursor.execute("""
                SELECT id, scheduled_departure, actual_departure
                FROM hsp_service_details
                WHERE departure_delay_minutes IS NULL
                  AND scheduled_departure IS NOT NULL
                  AND actual_departure IS NOT NULL
            """).fetchall()
            
            for record in missing_dep_delays:
                try:
                    scheduled = datetime.fromisoformat(record['scheduled_departure'].replace('Z', '+00:00'))
                    actual = datetime.fromisoformat(record['actual_departure'].replace('Z', '+00:00'))
                    delta = actual - scheduled
                    delay_minutes = int(delta.total_seconds() / 60)
                    
                    if abs(delay_minutes) <= 180:
                        self.cursor.execute("""
                            UPDATE hsp_service_details
                            SET departure_delay_minutes = ?
                            WHERE id = ?
                        """, (delay_minutes, record['id']))
                        calculated += 1
                except Exception as e:
                    continue
            
            self.conn.commit()
            print(f"   ✅ 重新计算了 {calculated} 条记录的延迟值")
            self.stats['missing_delays_recalculated'] = calculated
            return calculated
        
        return 0
    
    def remove_invalid_records(self) -> int:
        """删除无效记录（缺少关键字段）"""
        print(f"\n🔍 检查无效记录...")
        
        # 查找缺少所有关键字段的记录
        invalid = self.cursor.execute("""
            SELECT COUNT(*) as count
            FROM hsp_service_details
            WHERE scheduled_departure IS NULL
              AND scheduled_arrival IS NULL
              AND actual_departure IS NULL
              AND actual_arrival IS NULL
              AND arrival_delay_minutes IS NULL
              AND departure_delay_minutes IS NULL
        """).fetchone()['count']
        
        print(f"   找到 {invalid} 条完全无效的记录（所有关键字段都缺失）")
        
        if invalid > 0 and not self.dry_run:
            self.cursor.execute("""
                DELETE FROM hsp_service_details
                WHERE scheduled_departure IS NULL
                  AND scheduled_arrival IS NULL
                  AND actual_departure IS NULL
                  AND actual_arrival IS NULL
                  AND arrival_delay_minutes IS NULL
                  AND departure_delay_minutes IS NULL
            """)
            self.conn.commit()
            print(f"   ✅ 删除了 {invalid} 条无效记录")
            self.stats['invalid_records_removed'] = invalid
            return invalid
        
        return 0
    
    def run_all_cleaning(self) -> Dict:
        """运行所有清洗步骤"""
        print("=" * 70)
        print("数据清洗开始")
        print("=" * 70)
        if self.dry_run:
            print("⚠️  运行模式：DRY RUN（不会修改数据）")
        else:
            print("⚠️  运行模式：实际执行（将修改数据）")
        print("=" * 70)
        
        # 获取清洗前的记录数
        before_count = self.cursor.execute("SELECT COUNT(*) FROM hsp_service_details").fetchone()[0]
        print(f"\n📊 清洗前总记录数: {before_count:,}")
        
        # 执行清洗步骤
        self.clean_extreme_delays(max_delay_minutes=180)
        self.fix_time_inconsistencies()
        self.recalculate_missing_delays()
        self.remove_invalid_records()
        
        # 获取清洗后的记录数
        after_count = self.cursor.execute("SELECT COUNT(*) FROM hsp_service_details").fetchone()[0]
        print(f"\n📊 清洗后总记录数: {after_count:,}")
        print(f"📊 删除记录数: {before_count - after_count:,}")
        
        print("\n" + "=" * 70)
        print("数据清洗完成")
        print("=" * 70)
        print("\n📋 清洗统计:")
        for key, value in self.stats.items():
            print(f"   {key}: {value:,}")
        
        return self.stats
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='清洗 HSP 数据')
    parser.add_argument('--db', default='data/railfair.db', help='数据库路径')
    parser.add_argument('--execute', action='store_true', help='实际执行清洗（默认是 dry run）')
    args = parser.parse_args()
    
    cleaner = DataCleaner(args.db, dry_run=not args.execute)
    try:
        cleaner.run_all_cleaning()
    finally:
        cleaner.close()


if __name__ == '__main__':
    main()

