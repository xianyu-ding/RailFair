#!/usr/bin/env python3
"""
Verify actual route completion status by checking database
and comparing with expected tasks.

This script:
1. Reads the config to get expected routes and date ranges
2. Checks database for actual data collected
3. Calculates expected tasks per route
4. Verifies if routes are truly completed
5. Optionally cleans up progress file
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

from utils.date_utils import split_date_range


def load_config(config_path: str) -> Dict:
    """Load configuration file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_expected_tasks_per_route(config: Dict) -> Dict[str, int]:
    """Calculate expected number of tasks per route"""
    from_date = config['data_collection']['from_date']
    to_date = config['data_collection']['to_date']
    
    # Parse days
    days_str = config['data_collection'].get('days', 'WEEKDAY')
    day_types = []
    for day_type in days_str.split(','):
        day_type = day_type.strip().upper()
        if day_type == 'WEEKEND':
            day_types.extend(['SATURDAY', 'SUNDAY'])
        else:
            day_types.append(day_type)
    
    # Remove duplicates
    day_types = list(dict.fromkeys(day_types))
    
    # Split date range into chunks (≤7 days)
    date_chunks = split_date_range(from_date, to_date, chunk_days=7)
    
    # Expected tasks = date_chunks × day_types
    expected_tasks = len(date_chunks) * len(day_types)
    
    # Return for each route
    routes = config.get('routes', [])
    result = {}
    for route in routes:
        route_name = route['name']
        result[route_name] = expected_tasks
    
    return result, date_chunks, day_types


def check_route_data_in_db(db_path: str, route: Dict, date_chunks: List[Tuple[str, str]], 
                          day_types: List[str]) -> Dict:
    """Check actual data in database for a route"""
    if not os.path.exists(db_path):
        return {
            'metrics_count': 0,
            'details_count': 0,
            'unique_dates': 0,
            'date_coverage': {},
            'has_data': False
        }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    origin = route['from_loc']
    destination = route['to_loc']
    
    try:
        # Count metrics for this route
        cursor.execute("""
            SELECT COUNT(*) 
            FROM hsp_service_metrics
            WHERE origin = ? AND destination = ?
        """, (origin, destination))
        metrics_count = cursor.fetchone()[0]
        
        # Count details (we can't directly link to route, so count all)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM hsp_service_details
        """)
        details_count = cursor.fetchone()[0]
        
        # Get unique dates in database for this date range
        all_dates = set()
        date_coverage = {}
        for chunk_from, chunk_to in date_chunks:
            cursor.execute("""
                SELECT DISTINCT date_of_service
                FROM hsp_service_details
                WHERE date_of_service BETWEEN ? AND ?
            """, (chunk_from, chunk_to))
            dates = [row[0] for row in cursor.fetchall() if row[0]]
            all_dates.update(dates)
            date_coverage[f"{chunk_from}_to_{chunk_to}"] = len(dates)
        
        return {
            'metrics_count': metrics_count,
            'details_count': details_count,
            'unique_dates': len(all_dates),
            'date_coverage': date_coverage,
            'has_data': metrics_count > 0
        }
    finally:
        conn.close()


def verify_routes(config_path: str, db_path: str, progress_path: str = None) -> Dict:
    """Verify route completion status"""
    config = load_config(config_path)
    routes = config.get('routes', [])
    
    expected_tasks, date_chunks, day_types = get_expected_tasks_per_route(config)
    
    print("📊 Route Completion Verification")
    print("=" * 70)
    print(f"Config: {config_path}")
    print(f"Database: {db_path}")
    print(f"Expected tasks per route: {expected_tasks.get(list(expected_tasks.keys())[0], 0)}")
    print(f"  (Date chunks: {len(date_chunks)}, Day types: {len(day_types)})")
    print("")
    
    results = {}
    for route in routes:
        route_name = route['name']
        route_data = check_route_data_in_db(db_path, route, date_chunks, day_types)
        
        # Estimate completion based on data
        # This is approximate - we can't know exact task completion from DB alone
        # But we can check if there's reasonable data coverage
        expected = expected_tasks[route_name]
        
        # Heuristic: If we have data for most date chunks, route is likely complete
        # But this is not 100% accurate
        has_sufficient_data = route_data['metrics_count'] > 0 and route_data['unique_dates'] >= len(date_chunks) * 0.5
        
        results[route_name] = {
            'expected_tasks': expected,
            'metrics_count': route_data['metrics_count'],
            'unique_dates': route_data['unique_dates'],
            'has_data': route_data['has_data'],
            'has_sufficient_data': has_sufficient_data,
            'date_coverage': route_data['date_coverage']
        }
        
        status = "✅" if has_sufficient_data else "⚠️"
        print(f"{status} {route_name}:")
        print(f"   Metrics: {route_data['metrics_count']:,} records")
        print(f"   Unique dates: {route_data['unique_dates']} (expected: ~{len(date_chunks)} chunks)")
        print(f"   Status: {'Has data' if route_data['has_data'] else 'No data'}")
        print("")
    
    # Check progress file if provided
    if progress_path and os.path.exists(progress_path):
        print("📋 Progress File Status:")
        print("=" * 70)
        with open(progress_path, 'r') as f:
            progress = json.load(f)
        
        completed_in_file = progress.get('completed_routes', [])
        failed_in_file = progress.get('failed_routes', [])
        
        print(f"   Marked as completed in file: {len(completed_in_file)} routes")
        print(f"   Marked as failed in file: {len(failed_in_file)} routes")
        print("")
        
        # Compare with actual data
        print("🔍 Verification:")
        print("-" * 70)
        for route_name in completed_in_file:
            route_result = results.get(route_name, {})
            if route_result.get('has_sufficient_data'):
                print(f"   ✅ {route_name}: Correctly marked as completed (has data)")
            else:
                print(f"   ⚠️  {route_name}: Marked as completed but has insufficient data")
                print(f"      Metrics: {route_result.get('metrics_count', 0)}, "
                      f"Dates: {route_result.get('unique_dates', 0)}")
        
        # Check routes with data but not marked as completed
        for route_name, route_result in results.items():
            if route_name not in completed_in_file and route_result.get('has_sufficient_data'):
                print(f"   ℹ️  {route_name}: Has data but not marked as completed in file")
    
    return results


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify route completion status')
    parser.add_argument('--config', default='configs/hsp_config_phase1.yaml',
                       help='Config file path')
    parser.add_argument('--db', default='data/railfair.db',
                       help='Database file path')
    parser.add_argument('--progress', default='data/progress_phase1.json',
                       help='Progress file path (optional)')
    parser.add_argument('--clean', action='store_true',
                       help='Clean up progress file (remove incorrectly marked routes)')
    
    args = parser.parse_args()
    
    results = verify_routes(args.config, args.db, args.progress)
    
    if args.clean and args.progress and os.path.exists(args.progress):
        print("\n🧹 Cleaning Progress File:")
        print("=" * 70)
        
        with open(args.progress, 'r') as f:
            progress = json.load(f)
        
        # Remove routes that don't have sufficient data
        completed_routes = progress.get('completed_routes', [])
        cleaned_routes = []
        removed_routes = []
        
        for route_name in completed_routes:
            route_result = results.get(route_name, {})
            if route_result.get('has_sufficient_data'):
                cleaned_routes.append(route_name)
            else:
                removed_routes.append(route_name)
                print(f"   ❌ Removed {route_name} (insufficient data)")
        
        progress['completed_routes'] = cleaned_routes
        progress['last_updated'] = datetime.now().isoformat()
        
        # Backup original
        backup_path = args.progress + '.backup'
        import shutil
        shutil.copy2(args.progress, backup_path)
        print(f"   💾 Backup saved to: {backup_path}")
        
        # Save cleaned version
        with open(args.progress, 'w') as f:
            json.dump(progress, f, indent=2)
        
        print(f"   ✅ Cleaned progress file: {len(cleaned_routes)} routes remain, "
              f"{len(removed_routes)} removed")
        print(f"   📝 Updated: {args.progress}")


if __name__ == '__main__':
    main()

