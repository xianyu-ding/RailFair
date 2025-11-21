#!/usr/bin/env python3
"""
HSP Data Validation and Statistics Report
Purpose: Validate collected data and generate comprehensive statistics
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import json

class HSPDataAnalyzer:
    """Analyze and validate HSP collected data"""
    
    def __init__(self, db_path: str = "data/railfair.db"):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def get_basic_stats(self) -> Dict:
        """Get basic statistics about collected data"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Service metrics count
        cursor.execute("SELECT COUNT(*) as count FROM hsp_service_metrics")
        stats['metrics_count'] = cursor.fetchone()['count']
        
        # Service details count
        cursor.execute("SELECT COUNT(*) as count FROM hsp_service_details")
        stats['details_count'] = cursor.fetchone()['count']
        
        # Unique routes
        cursor.execute("""
            SELECT COUNT(DISTINCT origin || '-' || destination) as count 
            FROM hsp_service_metrics
        """)
        stats['unique_routes'] = cursor.fetchone()['count']
        
        # Date range
        cursor.execute("""
            SELECT 
                MIN(date_of_service) as min_date,
                MAX(date_of_service) as max_date
            FROM hsp_service_details
        """)
        row = cursor.fetchone()
        stats['date_range'] = {
            'min': row['min_date'],
            'max': row['max_date']
        }
        
        # Unique TOCs
        cursor.execute("""
            SELECT COUNT(DISTINCT toc_code) as count 
            FROM hsp_service_metrics
        """)
        stats['unique_tocs'] = cursor.fetchone()['count']
        
        return stats
    
    def get_route_statistics(self) -> List[Dict]:
        """Get statistics per route"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                origin || '-' || destination as route,
                origin,
                destination,
                COUNT(*) as service_count,
                COUNT(DISTINCT toc_code) as toc_count,
                MIN(fetch_timestamp) as first_fetch,
                MAX(fetch_timestamp) as last_fetch
            FROM hsp_service_metrics
            GROUP BY origin, destination
            ORDER BY service_count DESC
        """)
        
        routes = []
        for row in cursor.fetchall():
            routes.append(dict(row))
        
        return routes
    
    def get_delay_statistics(self) -> Dict:
        """Get delay statistics"""
        cursor = self.conn.cursor()
        
        # Overall delay stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(arrival_delay_minutes) as records_with_delay,
                AVG(arrival_delay_minutes) as avg_delay,
                MIN(arrival_delay_minutes) as min_delay,
                MAX(arrival_delay_minutes) as max_delay,
                SUM(CASE WHEN arrival_delay_minutes > 0 THEN 1 ELSE 0 END) as delayed_count,
                SUM(CASE WHEN arrival_delay_minutes <= 0 THEN 1 ELSE 0 END) as on_time_count
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
        """)
        
        row = cursor.fetchone()
        
        stats = {
            'total_records': row['total_records'],
            'records_with_delay': row['records_with_delay'],
            'avg_delay_minutes': round(row['avg_delay'], 2) if row['avg_delay'] else 0,
            'min_delay_minutes': row['min_delay'],
            'max_delay_minutes': row['max_delay'],
            'delayed_count': row['delayed_count'],
            'on_time_count': row['on_time_count']
        }
        
        # Calculate on-time percentage
        if stats['records_with_delay'] > 0:
            stats['on_time_percentage'] = round(
                (stats['on_time_count'] / stats['records_with_delay']) * 100, 2
            )
        else:
            stats['on_time_percentage'] = 0
        
        # Delay distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN arrival_delay_minutes <= 0 THEN 'On Time'
                    WHEN arrival_delay_minutes <= 5 THEN '1-5 min'
                    WHEN arrival_delay_minutes <= 15 THEN '6-15 min'
                    WHEN arrival_delay_minutes <= 30 THEN '16-30 min'
                    ELSE '>30 min'
                END as delay_bucket,
                COUNT(*) as count
            FROM hsp_service_details
            WHERE arrival_delay_minutes IS NOT NULL
            GROUP BY delay_bucket
            ORDER BY 
                CASE delay_bucket
                    WHEN 'On Time' THEN 1
                    WHEN '1-5 min' THEN 2
                    WHEN '6-15 min' THEN 3
                    WHEN '16-30 min' THEN 4
                    WHEN '>30 min' THEN 5
                END
        """)
        
        distribution = []
        for row in cursor.fetchall():
            distribution.append(dict(row))
        
        stats['delay_distribution'] = distribution
        
        return stats
    
    def get_toc_statistics(self) -> List[Dict]:
        """Get statistics per Train Operating Company"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.toc_code,
                COUNT(DISTINCT m.id) as service_count,
                COUNT(DISTINCT d.id) as detail_count,
                AVG(d.arrival_delay_minutes) as avg_delay,
                SUM(CASE WHEN d.arrival_delay_minutes <= 0 THEN 1 ELSE 0 END) as on_time_count,
                COUNT(d.arrival_delay_minutes) as total_with_delay
            FROM hsp_service_metrics m
            LEFT JOIN hsp_service_details d ON m.toc_code = d.toc_code
            GROUP BY m.toc_code
            ORDER BY service_count DESC
        """)
        
        tocs = []
        for row in cursor.fetchall():
            toc_data = dict(row)
            if toc_data['total_with_delay'] > 0:
                toc_data['on_time_percentage'] = round(
                    (toc_data['on_time_count'] / toc_data['total_with_delay']) * 100, 2
                )
            else:
                toc_data['on_time_percentage'] = 0
            tocs.append(toc_data)
        
        return tocs
    
    def get_temporal_statistics(self) -> Dict:
        """Get temporal distribution statistics"""
        cursor = self.conn.cursor()
        
        # By day of week (if date_of_service is in YYYY-MM-DD format)
        cursor.execute("""
            SELECT 
                strftime('%w', date_of_service) as day_of_week,
                COUNT(*) as count
            FROM hsp_service_details
            WHERE date_of_service IS NOT NULL
            GROUP BY day_of_week
            ORDER BY day_of_week
        """)
        
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        by_day = []
        for row in cursor.fetchall():
            day_num = int(row['day_of_week'])
            by_day.append({
                'day_of_week': day_names[day_num],
                'count': row['count']
            })
        
        # By month
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', date_of_service) as month,
                COUNT(*) as count
            FROM hsp_service_details
            WHERE date_of_service IS NOT NULL
            GROUP BY month
            ORDER BY month
        """)
        
        by_month = []
        for row in cursor.fetchall():
            by_month.append(dict(row))
        
        return {
            'by_day_of_week': by_day,
            'by_month': by_month
        }
    
    def check_data_quality(self) -> Dict:
        """Check data quality issues"""
        cursor = self.conn.cursor()
        
        issues = {}
        
        # Missing TOC codes
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM hsp_service_metrics 
            WHERE toc_code IS NULL OR toc_code = ''
        """)
        issues['missing_toc_codes'] = cursor.fetchone()['count']
        
        # Missing timestamps
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM hsp_service_details 
            WHERE scheduled_arrival IS NULL AND scheduled_departure IS NULL
        """)
        issues['missing_timestamps'] = cursor.fetchone()['count']
        
        # Unrealistic delays (>180 minutes)
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM hsp_service_details 
            WHERE arrival_delay_minutes > 180
        """)
        issues['extreme_delays'] = cursor.fetchone()['count']
        
        # Duplicate RID+location combinations
        cursor.execute("""
            SELECT rid, location, COUNT(*) as count
            FROM hsp_service_details
            GROUP BY rid, location
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        issues['duplicate_entries'] = len(duplicates)
        
        return issues
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate comprehensive analysis report"""
        self.connect()
        
        try:
            # Collect all statistics
            basic_stats = self.get_basic_stats()
            route_stats = self.get_route_statistics()
            delay_stats = self.get_delay_statistics()
            toc_stats = self.get_toc_statistics()
            temporal_stats = self.get_temporal_statistics()
            quality_issues = self.check_data_quality()
            
            # Build report
            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append("HSP DATA COLLECTION REPORT")
            report_lines.append("=" * 80)
            report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"Database: {self.db_path}")
            
            # Basic Statistics
            report_lines.append("\n" + "=" * 80)
            report_lines.append("BASIC STATISTICS")
            report_lines.append("=" * 80)
            report_lines.append(f"\n📊 Data Overview:")
            report_lines.append(f"   Service Metrics:  {basic_stats['metrics_count']:,} records")
            report_lines.append(f"   Service Details:  {basic_stats['details_count']:,} records")
            report_lines.append(f"   Unique Routes:    {basic_stats['unique_routes']}")
            report_lines.append(f"   Unique TOCs:      {basic_stats['unique_tocs']}")
            
            if basic_stats['date_range']['min']:
                report_lines.append(f"\n📅 Date Coverage:")
                report_lines.append(f"   From: {basic_stats['date_range']['min']}")
                report_lines.append(f"   To:   {basic_stats['date_range']['max']}")
            
            # Route Statistics
            report_lines.append("\n" + "=" * 80)
            report_lines.append("ROUTE STATISTICS")
            report_lines.append("=" * 80)
            report_lines.append(f"\n{'Route':<15} {'Services':<10} {'TOCs':<8} {'First Fetch':<20} {'Last Fetch':<20}")
            report_lines.append("-" * 80)
            for route in route_stats[:15]:  # Top 15 routes
                report_lines.append(
                    f"{route['route']:<15} {route['service_count']:<10} {route['toc_count']:<8} "
                    f"{route['first_fetch'][:19]:<20} {route['last_fetch'][:19]:<20}"
                )
            
            # Delay Statistics
            report_lines.append("\n" + "=" * 80)
            report_lines.append("DELAY ANALYSIS")
            report_lines.append("=" * 80)
            report_lines.append(f"\n📈 Overall Performance:")
            report_lines.append(f"   Total Records:        {delay_stats['total_records']:,}")
            report_lines.append(f"   Records with Data:    {delay_stats['records_with_delay']:,}")
            report_lines.append(f"   On-Time Count:        {delay_stats['on_time_count']:,}")
            report_lines.append(f"   Delayed Count:        {delay_stats['delayed_count']:,}")
            report_lines.append(f"   On-Time Percentage:   {delay_stats['on_time_percentage']:.1f}%")
            report_lines.append(f"   Average Delay:        {delay_stats['avg_delay_minutes']:.1f} minutes")
            report_lines.append(f"   Min Delay:            {delay_stats['min_delay_minutes']} minutes")
            report_lines.append(f"   Max Delay:            {delay_stats['max_delay_minutes']} minutes")
            
            report_lines.append(f"\n📊 Delay Distribution:")
            for bucket in delay_stats['delay_distribution']:
                percentage = (bucket['count'] / delay_stats['records_with_delay']) * 100
                bar = '█' * int(percentage / 2)
                report_lines.append(f"   {bucket['delay_bucket']:<12} {bucket['count']:>6} ({percentage:>5.1f}%) {bar}")
            
            # TOC Statistics
            report_lines.append("\n" + "=" * 80)
            report_lines.append("TRAIN OPERATING COMPANY STATISTICS")
            report_lines.append("=" * 80)
            report_lines.append(f"\n{'TOC':<8} {'Services':<10} {'Details':<10} {'Avg Delay':<12} {'On-Time %':<10}")
            report_lines.append("-" * 80)
            for toc in toc_stats[:10]:  # Top 10 TOCs
                avg_delay = f"{toc['avg_delay']:.1f}m" if toc['avg_delay'] else "N/A"
                report_lines.append(
                    f"{toc['toc_code']:<8} {toc['service_count']:<10} {toc['detail_count']:<10} "
                    f"{avg_delay:<12} {toc['on_time_percentage']:.1f}%"
                )
            
            # Temporal Distribution
            report_lines.append("\n" + "=" * 80)
            report_lines.append("TEMPORAL DISTRIBUTION")
            report_lines.append("=" * 80)
            
            if temporal_stats['by_day_of_week']:
                report_lines.append(f"\n📅 By Day of Week:")
                for day in temporal_stats['by_day_of_week']:
                    report_lines.append(f"   {day['day_of_week']:<10} {day['count']:>6} records")
            
            if temporal_stats['by_month']:
                report_lines.append(f"\n📅 By Month:")
                for month in temporal_stats['by_month']:
                    report_lines.append(f"   {month['month']:<10} {month['count']:>6} records")
            
            # Data Quality
            report_lines.append("\n" + "=" * 80)
            report_lines.append("DATA QUALITY CHECKS")
            report_lines.append("=" * 80)
            report_lines.append(f"\n⚠️  Issues Found:")
            report_lines.append(f"   Missing TOC codes:     {quality_issues['missing_toc_codes']}")
            report_lines.append(f"   Missing timestamps:    {quality_issues['missing_timestamps']}")
            report_lines.append(f"   Extreme delays (>3h):  {quality_issues['extreme_delays']}")
            report_lines.append(f"   Duplicate entries:     {quality_issues['duplicate_entries']}")
            
            total_issues = sum(quality_issues.values())
            if total_issues == 0:
                report_lines.append(f"\n✅ No data quality issues detected!")
            else:
                report_lines.append(f"\n⚠️  Total issues: {total_issues}")
            
            # Success Criteria Check
            report_lines.append("\n" + "=" * 80)
            report_lines.append("WEEK 1 SUCCESS CRITERIA CHECK")
            report_lines.append("=" * 80)
            
            criteria_met = []
            criteria_failed = []
            
            # Check >10,000 records
            if basic_stats['details_count'] >= 10000:
                criteria_met.append(f"✅ Historical records ≥ 10,000: {basic_stats['details_count']:,}")
            else:
                criteria_failed.append(f"❌ Historical records < 10,000: {basic_stats['details_count']:,}")
            
            # Check ≥10 routes
            if basic_stats['unique_routes'] >= 10:
                criteria_met.append(f"✅ Route coverage ≥ 10: {basic_stats['unique_routes']}")
            else:
                criteria_failed.append(f"❌ Route coverage < 10: {basic_stats['unique_routes']}")
            
            # Check data quality
            if total_issues < 100:
                criteria_met.append(f"✅ Data quality acceptable: {total_issues} issues")
            else:
                criteria_failed.append(f"❌ Data quality issues: {total_issues} problems")
            
            report_lines.append("\n✅ Criteria Met:")
            for item in criteria_met:
                report_lines.append(f"   {item}")
            
            if criteria_failed:
                report_lines.append("\n❌ Criteria Not Met:")
                for item in criteria_failed:
                    report_lines.append(f"   {item}")
            
            report_lines.append("\n" + "=" * 80)
            
            # Save report
            report = "\n".join(report_lines)
            
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(report)
                print(f"📄 Report saved to: {output_file}")
            
            return report
            
        finally:
            self.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HSP Data Validation and Statistics')
    parser.add_argument('--db', default='data/railfair.db', help='Database path')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--json', help='Export statistics as JSON')
    args = parser.parse_args()
    
    try:
        analyzer = HSPDataAnalyzer(args.db)
        report = analyzer.generate_report(args.output)
        print(report)
        
        # Export JSON if requested
        if args.json:
            analyzer.connect()
            stats = {
                'basic': analyzer.get_basic_stats(),
                'routes': analyzer.get_route_statistics(),
                'delays': analyzer.get_delay_statistics(),
                'tocs': analyzer.get_toc_statistics(),
                'temporal': analyzer.get_temporal_statistics(),
                'quality': analyzer.check_data_quality()
            }
            analyzer.close()
            
            with open(args.json, 'w') as f:
                json.dump(stats, indent=2, fp=f)
            print(f"\n📊 JSON statistics saved to: {args.json}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
