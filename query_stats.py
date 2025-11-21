#!/usr/bin/env python3
"""
RailFair Statistics Query Interface - Day 6
提供快速的统计查询接口，支持缓存
"""

import sqlite3
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import hashlib

class StatisticsQuery:
    """统计查询接口"""
    
    def __init__(self, db_path: str = "data/railfair.db"):
        self.db_path = db_path
        self.conn = None
        self.cache_hits = 0
        self.cache_misses = 0
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    # ============================================================================
    # 路线统计查询
    # ============================================================================
    
    def get_route_stats(self, origin: str, destination: str, 
                       use_latest: bool = True) -> Optional[Dict]:
        """
        获取路线统计
        
        Args:
            origin: 出发站代码
            destination: 到达站代码
            use_latest: 是否使用最新统计（True）或指定日期
        
        Returns:
            统计字典或None
        """
        cursor = self.conn.cursor()
        
        if use_latest:
            cursor.execute("""
                SELECT * FROM route_statistics
                WHERE origin = ? AND destination = ?
                ORDER BY calculation_date DESC
                LIMIT 1
            """, (origin, destination))
        else:
            cursor.execute("""
                SELECT * FROM route_statistics
                WHERE origin = ? AND destination = ?
                ORDER BY calculation_date DESC
            """, (origin, destination))
        
        result = cursor.fetchone()
        
        if result:
            stats = dict(result)
            # 解析JSON字段
            if stats.get('hourly_stats'):
                stats['hourly_stats'] = json.loads(stats['hourly_stats'])
            if stats.get('day_of_week_stats'):
                stats['day_of_week_stats'] = json.loads(stats['day_of_week_stats'])
            return stats
        
        return None
    
    def get_all_routes_stats(self, order_by: str = 'reliability_score') -> List[Dict]:
        """
        获取所有路线的最新统计
        
        Args:
            order_by: 排序字段 (reliability_score, on_time_percentage, avg_delay_minutes)
        
        Returns:
            统计列表
        """
        cursor = self.conn.cursor()
        
        valid_orders = ['reliability_score', 'on_time_percentage', 'avg_delay_minutes']
        if order_by not in valid_orders:
            order_by = 'reliability_score'
        
        order_direction = 'DESC' if order_by != 'avg_delay_minutes' else 'ASC'
        
        cursor.execute(f"""
            SELECT * FROM v_latest_route_stats
            ORDER BY {order_by} {order_direction}
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_best_routes(self, limit: int = 5) -> List[Dict]:
        """获取最可靠的路线"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM v_latest_route_stats
            ORDER BY reliability_score DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_worst_routes(self, limit: int = 5) -> List[Dict]:
        """获取最不可靠的路线"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM v_latest_route_stats
            ORDER BY reliability_score ASC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ============================================================================
    # TOC统计查询
    # ============================================================================
    
    def get_toc_stats(self, toc_code: str, use_latest: bool = True) -> Optional[Dict]:
        """获取TOC运营商统计"""
        cursor = self.conn.cursor()
        
        if use_latest:
            cursor.execute("""
                SELECT * FROM toc_statistics
                WHERE toc_code = ?
                ORDER BY calculation_date DESC
                LIMIT 1
            """, (toc_code,))
        else:
            cursor.execute("""
                SELECT * FROM toc_statistics
                WHERE toc_code = ?
                ORDER BY calculation_date DESC
            """, (toc_code,))
        
        result = cursor.fetchone()
        
        if result:
            stats = dict(result)
            if stats.get('route_performance'):
                stats['route_performance'] = json.loads(stats['route_performance'])
            return stats
        
        return None
    
    def get_all_tocs_stats(self, order_by: str = 'reliability_score') -> List[Dict]:
        """获取所有TOC统计"""
        cursor = self.conn.cursor()
        
        valid_orders = ['reliability_score', 'ppm_5_percentage', 'cancelled_percentage']
        if order_by not in valid_orders:
            order_by = 'reliability_score'
        
        order_direction = 'DESC' if order_by != 'cancelled_percentage' else 'ASC'
        
        cursor.execute(f"""
            SELECT * FROM v_latest_toc_stats
            ORDER BY {order_by} {order_direction}
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_best_tocs(self, limit: int = 5) -> List[Dict]:
        """获取最可靠的运营商"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM v_latest_toc_stats
            ORDER BY reliability_score DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ============================================================================
    # 时段统计查询
    # ============================================================================
    
    def get_time_slot_stats(self, origin: str, destination: str, 
                           hour: int, day_of_week: Optional[int] = None) -> Optional[Dict]:
        """
        获取特定时段的统计
        
        Args:
            origin: 出发站
            destination: 到达站
            hour: 小时 (0-23)
            day_of_week: 星期 (0=Monday, 6=Sunday, None=所有)
        """
        cursor = self.conn.cursor()
        
        if day_of_week is not None:
            cursor.execute("""
                SELECT * FROM time_slot_statistics
                WHERE origin = ? AND destination = ?
                  AND hour_of_day = ? AND day_of_week = ?
                ORDER BY calculation_date DESC
                LIMIT 1
            """, (origin, destination, hour, day_of_week))
        else:
            cursor.execute("""
                SELECT * FROM time_slot_statistics
                WHERE origin = ? AND destination = ?
                  AND hour_of_day = ? AND day_of_week IS NULL
                ORDER BY calculation_date DESC
                LIMIT 1
            """, (origin, destination, hour))
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    # ============================================================================
    # 预测缓存查询
    # ============================================================================
    
    def generate_cache_key(self, origin: str, destination: str, 
                          departure_date: str, departure_time: str) -> str:
        """生成缓存键"""
        key_str = f"{origin}|{destination}|{departure_date}|{departure_time}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_prediction_cache(self, origin: str, destination: str,
                            departure_date: str, departure_time: str) -> Optional[Dict]:
        """
        从缓存获取预测结果
        
        Returns:
            预测字典或None（缓存未命中或已过期）
        """
        cache_key = self.generate_cache_key(origin, destination, departure_date, departure_time)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM prediction_cache
            WHERE cache_key = ?
              AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (cache_key,))
        
        result = cursor.fetchone()
        
        if result:
            self.cache_hits += 1
            
            # 更新访问次数和时间
            cursor.execute("""
                UPDATE prediction_cache
                SET hit_count = hit_count + 1,
                    last_accessed = datetime('now')
                WHERE cache_key = ?
            """, (cache_key,))
            self.conn.commit()
            
            stats = dict(result)
            if stats.get('alternative_suggestions'):
                stats['alternative_suggestions'] = json.loads(stats['alternative_suggestions'])
            
            return stats
        else:
            self.cache_misses += 1
            return None
    
    def save_prediction_cache(self, prediction: Dict, ttl_hours: int = 24):
        """
        保存预测到缓存
        
        Args:
            prediction: 预测字典
            ttl_hours: 缓存存活时间（小时）
        """
        cache_key = self.generate_cache_key(
            prediction['origin'],
            prediction['destination'],
            prediction['departure_date'],
            prediction['departure_time']
        )
        
        cursor = self.conn.cursor()
        
        # 计算过期时间
        expires_at = datetime.now().replace(microsecond=0)
        from datetime import timedelta
        expires_at += timedelta(hours=ttl_hours)
        
        # 准备数据
        data = {
            'cache_key': cache_key,
            'origin': prediction['origin'],
            'destination': prediction['destination'],
            'departure_date': prediction['departure_date'],
            'departure_time': prediction['departure_time'],
            'predicted_delay_minutes': prediction.get('predicted_delay_minutes'),
            'on_time_probability': prediction.get('on_time_probability'),
            'delay_5_probability': prediction.get('delay_5_probability'),
            'delay_15_probability': prediction.get('delay_15_probability'),
            'severe_delay_probability': prediction.get('severe_delay_probability'),
            'confidence_level': prediction.get('confidence_level'),
            'confidence_score': prediction.get('confidence_score'),
            'recommendation': prediction.get('recommendation'),
            'alternative_suggestions': json.dumps(prediction.get('alternative_suggestions', [])),
            'model_version': prediction.get('model_version', 'v1-statistical'),
            'expires_at': expires_at.isoformat()
        }
        
        # 删除旧缓存（如果存在）
        cursor.execute("DELETE FROM prediction_cache WHERE cache_key = ?", (cache_key,))
        
        # 插入新缓存
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        
        cursor.execute(f"""
            INSERT INTO prediction_cache ({columns})
            VALUES ({placeholders})
        """, list(data.values()))
        
        self.conn.commit()
    
    def clean_expired_cache(self) -> int:
        """清理过期缓存，返回清理数量"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            DELETE FROM prediction_cache
            WHERE expires_at < datetime('now')
        """)
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        return deleted
    
    # ============================================================================
    # 数据质量查询
    # ============================================================================
    
    def get_data_quality_metrics(self, metric_date: Optional[str] = None) -> Optional[Dict]:
        """获取数据质量指标"""
        cursor = self.conn.cursor()
        
        if metric_date:
            cursor.execute("""
                SELECT * FROM data_quality_metrics
                WHERE metric_date = ?
            """, (metric_date,))
        else:
            cursor.execute("""
                SELECT * FROM data_quality_metrics
                ORDER BY metric_date DESC
                LIMIT 1
            """)
        
        result = cursor.fetchone()
        return dict(result) if result else None
    
    # ============================================================================
    # 分析和比较
    # ============================================================================
    
    def compare_routes(self, routes: List[Tuple[str, str]]) -> List[Dict]:
        """
        比较多条路线
        
        Args:
            routes: [(origin1, dest1), (origin2, dest2), ...]
        
        Returns:
            对比列表
        """
        results = []
        
        for origin, dest in routes:
            stats = self.get_route_stats(origin, dest)
            if stats:
                results.append({
                    'route': f"{origin}-{dest}",
                    'reliability_score': stats['reliability_score'],
                    'reliability_grade': stats['reliability_grade'],
                    'ppm_5': stats['time_to_5_percentage'],
                    'ppm_10': stats['time_to_10_percentage'],
                    'avg_delay': stats['avg_delay_minutes'],
                    'cancelled_pct': stats['cancelled_percentage']
                })
        
        return sorted(results, key=lambda x: x['reliability_score'], reverse=True)
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        cursor = self.conn.cursor()
        
        # 总缓存数
        cursor.execute("SELECT COUNT(*) as total FROM prediction_cache")
        total = cursor.fetchone()['total']
        
        # 有效缓存数
        cursor.execute("""
            SELECT COUNT(*) as valid 
            FROM prediction_cache
            WHERE expires_at > datetime('now')
        """)
        valid = cursor.fetchone()['valid']
        
        # 过期缓存数
        expired = total - valid
        
        # 平均命中次数
        cursor.execute("""
            SELECT AVG(hit_count) as avg_hits
            FROM prediction_cache
            WHERE expires_at > datetime('now')
        """)
        avg_hits = cursor.fetchone()['avg_hits'] or 0
        
        # 缓存命中率
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_entries': total,
            'valid_entries': valid,
            'expired_entries': expired,
            'avg_hits_per_entry': round(avg_hits, 2),
            'cache_hit_rate': round(hit_rate, 2),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses
        }
    
    def print_route_stats(self, origin: str, destination: str):
        """打印路线统计（格式化）"""
        stats = self.get_route_stats(origin, destination)
        
        if not stats:
            print(f"❌ No statistics found for route {origin}-{destination}")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 Route Statistics: {stats['route_name']}")
        print(f"{'='*60}")
        
        print(f"\n📈 Performance Metrics:")
        print(f"  Reliability Grade:    {stats['reliability_grade']} ({stats['reliability_score']:.1f}/100)")
        print(f"  On Time (≤1 min):     {stats['on_time_percentage']:.1f}%")
        print(f"  PPM-5 (≤5 min):       {stats['time_to_5_percentage']:.1f}%")
        print(f"  PPM-10 (≤10 min):     {stats['time_to_10_percentage']:.1f}%")
        print(f"  Average Delay:        {stats['avg_delay_minutes']:.1f} minutes")
        print(f"  Cancellation Rate:    {stats['cancelled_percentage']:.1f}%")
        
        print(f"\n📊 Data Coverage:")
        print(f"  Date Range:           {stats['data_start_date']} to {stats['data_end_date']}")
        print(f"  Total Services:       {stats['total_services']:,}")
        print(f"  Sample Size:          {stats['sample_size']:,}")
        print(f"  Data Quality:         {stats['data_quality_score']:.1f}/100")
        
        print(f"\n⏱️  Delay Distribution:")
        print(f"  0-5 min:              {stats['delays_0_5_count']:,} ({stats['delays_0_5_count']/stats['sample_size']*100:.1f}%)")
        print(f"  5-15 min:             {stats['delays_5_15_count']:,} ({stats['delays_5_15_count']/stats['sample_size']*100:.1f}%)")
        print(f"  15-30 min:            {stats['delays_15_30_count']:,} ({stats['delays_15_30_count']/stats['sample_size']*100:.1f}%)")
        print(f"  30-60 min:            {stats['delays_30_60_count']:,} ({stats['delays_30_60_count']/stats['sample_size']*100:.1f}%)")
        print(f"  >60 min:              {stats['delays_60_plus_count']:,} ({stats['delays_60_plus_count']/stats['sample_size']*100:.1f}%)")
        
        print(f"\n📅 Last Updated:        {stats['last_updated']}")


def main():
    """演示查询功能"""
    import sys
    
    db_path = "data/railfair.db" if len(sys.argv) == 1 else sys.argv[1]
    
    with StatisticsQuery(db_path) as query:
        print("🔍 RailFair Statistics Query Demo\n")
        
        # 获取所有路线
        print("📊 All Routes (by reliability):")
        print("-" * 60)
        routes = query.get_all_routes_stats()
        
        if routes:
            for r in routes:
                print(f"{r['route_name']:<15} Grade: {r['reliability_grade']:<3} "
                      f"PPM-5: {r['ppm_5']:>5.1f}% PPM-10: {r['ppm_10']:>5.1f}%")
            
            # 详细显示第一条路线
            first_route = routes[0]
            query.print_route_stats(first_route['origin'], first_route['destination'])
        else:
            print("  No statistics available yet. Run calculate_stats.py first.")
        
        # TOC统计
        print(f"\n\n🏢 All TOCs (by reliability):")
        print("-" * 60)
        tocs = query.get_all_tocs_stats()
        
        if tocs:
            for t in tocs:
                print(f"{t['toc_code']:<8} Grade: {t['reliability_grade']:<3} "
                      f"PPM-5: {t['ppm_5']:>5.1f}% Cancel: {t['cancelled_percentage']:>5.1f}%")
        
        # 缓存统计
        print(f"\n\n💾 Cache Statistics:")
        print("-" * 60)
        cache_stats = query.get_cache_stats()
        print(f"  Total Entries:        {cache_stats['total_entries']}")
        print(f"  Valid Entries:        {cache_stats['valid_entries']}")
        print(f"  Expired Entries:      {cache_stats['expired_entries']}")
        print(f"  Avg Hits per Entry:   {cache_stats['avg_hits_per_entry']:.1f}")

if __name__ == "__main__":
    main()
