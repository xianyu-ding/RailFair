#!/bin/bash
# Check Phase 1 collection progress and missing data
# Usage: ./check_phase1_progress.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATA_DIR="data"
DB_FILE="${DATA_DIR}/railfair.db"
PROGRESS_FILE="${DATA_DIR}/progress_phase1.json"
LOG_DIR="logs"

echo "📊 Phase 1 Collection Progress Report"
echo "======================================"
echo ""

# Check database
if [ ! -f "$DB_FILE" ]; then
    echo "❌ Database file not found: $DB_FILE"
    exit 1
fi

# Get database stats
if command -v sqlite3 > /dev/null 2>&1; then
    echo "💾 Database Statistics:"
    echo "───────────────────────"
    
    METRICS_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM hsp_service_metrics;" 2>/dev/null || echo "0")
    DETAILS_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM hsp_service_details;" 2>/dev/null || echo "0")
    
    echo "   Service Metrics: $METRICS_COUNT records"
    echo "   Service Details: $DETAILS_COUNT records"
    echo ""
    
    # Get unique routes in database
    echo "📈 Routes in Database:"
    echo "──────────────────────"
    sqlite3 "$DB_FILE" << EOF
SELECT 
    origin || '-' || destination as route,
    COUNT(*) as records,
    MIN(fetch_timestamp) as first_collected,
    MAX(fetch_timestamp) as last_collected
FROM hsp_service_metrics
GROUP BY origin, destination
ORDER BY records DESC;
EOF
    echo ""
    
    # Get date range in database (from service_details table which has date_of_service)
    echo "📅 Date Range in Database:"
    echo "───────────────────────────"
    sqlite3 "$DB_FILE" << EOF
SELECT 
    MIN(date_of_service) as earliest_date,
    MAX(date_of_service) as latest_date,
    COUNT(DISTINCT date_of_service) as unique_dates
FROM hsp_service_details
WHERE date_of_service IS NOT NULL;
EOF
    echo ""
    
    # Also show time range from metrics (these are HHMM times, not dates)
    echo "⏰ Time Range in Metrics (HHMM format):"
    echo "────────────────────────────────────────"
    sqlite3 "$DB_FILE" << EOF
SELECT 
    MIN(scheduled_departure) as earliest_time,
    MAX(scheduled_departure) as latest_time
FROM hsp_service_metrics
WHERE scheduled_departure IS NOT NULL;
EOF
    echo ""
    
else
    echo "⚠️  sqlite3 not found. Install it to see detailed statistics."
    echo ""
fi

# Check progress file
if [ -f "$PROGRESS_FILE" ]; then
    echo "📋 Progress File:"
    echo "─────────────────"
    if command -v python3 > /dev/null 2>&1; then
        python3 << EOF
import json
from datetime import datetime

try:
    with open("$PROGRESS_FILE", 'r') as f:
        progress = json.load(f)
    
    completed_routes = progress.get('completed_routes', [])
    failed_routes = progress.get('failed_routes', [])
    total_records = progress.get('total_records', 0)
    started_at = progress.get('started_at')
    last_updated = progress.get('last_updated')
    
    print(f"   Started: {started_at}")
    print(f"   Last updated: {last_updated}")
    print(f"   Total records: {total_records:,}")
    print(f"   Completed routes: {len(completed_routes)}/10")
    print(f"   Failed routes: {len(failed_routes)}")
    print("")
    
    if completed_routes:
        print("   ✅ Completed routes:")
        for route in completed_routes:
            print(f"      • {route}")
    
    if failed_routes:
        print("")
        print("   ❌ Failed routes:")
        for route_info in failed_routes:
            route_name = route_info.get('route', 'Unknown')
            error = route_info.get('error', 'Unknown error')
            timestamp = route_info.get('timestamp', '')
            print(f"      • {route_name}")
            print(f"        Error: {error[:80]}...")
            if timestamp:
                print(f"        Time: {timestamp}")
    
except Exception as e:
    print(f"   Error reading progress file: {e}")
EOF
    else
        cat "$PROGRESS_FILE" | python3 -m json.tool 2>/dev/null || cat "$PROGRESS_FILE"
    fi
    echo ""
else
    echo "⚠️  Progress file not found: $PROGRESS_FILE"
    echo ""
fi

# Analyze missing data
echo "🔍 Missing Data Analysis:"
echo "─────────────────────────"
if command -v python3 > /dev/null 2>&1; then
    python3 << 'PYTHON_EOF'
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Expected configuration
EXPECTED_ROUTES = [
    "EUS-MAN", "KGX-EDR", "PAD-BRI", "LST-NRW", "VIC-BHM",
    "MAN-LIV", "BHM-MAN", "BRI-BHM", "EDR-GLC", "MAN-LEE"
]

EXPECTED_DATE_FROM = "2024-12-01"
EXPECTED_DATE_TO = "2025-01-31"
EXPECTED_DAY_TYPES = ["WEEKDAY", "SATURDAY", "SUNDAY"]

# Connect to database
db_file = Path("data/railfair.db")
if not db_file.exists():
    print("   ❌ Database not found")
    exit(1)

conn = sqlite3.connect(str(db_file))
cursor = conn.cursor()

# Get routes in database
cursor.execute("""
    SELECT DISTINCT origin || '-' || destination as route
    FROM hsp_service_metrics
    ORDER BY route
""")
routes_in_db = [row[0] for row in cursor.fetchall()]

# Find missing routes
missing_routes = [r for r in EXPECTED_ROUTES if r not in routes_in_db]

print(f"   Expected routes: {len(EXPECTED_ROUTES)}")
print(f"   Routes in database: {len(routes_in_db)}")
print(f"   Missing routes: {len(missing_routes)}")
print("")

if missing_routes:
    print("   ❌ Missing routes:")
    for route in missing_routes:
        print(f"      • {route}")
else:
    print("   ✅ All routes present in database")
print("")

# Check date coverage (from service_details table)
cursor.execute("""
    SELECT 
        MIN(date_of_service) as min_date,
        MAX(date_of_service) as max_date,
        COUNT(DISTINCT date_of_service) as unique_dates
    FROM hsp_service_details
    WHERE date_of_service IS NOT NULL
""")
result = cursor.fetchone()
if result and result[0]:
    min_date = result[0]
    max_date = result[1]
    unique_dates = result[2] or 0
    
    print(f"   Expected date range: {EXPECTED_DATE_FROM} to {EXPECTED_DATE_TO}")
    if min_date and max_date:
        print(f"   Date range in database: {min_date} to {max_date}")
        print(f"   Unique dates: {unique_dates}")
        
        # Calculate expected days
        start = datetime.strptime(EXPECTED_DATE_FROM, "%Y-%m-%d")
        end = datetime.strptime(EXPECTED_DATE_TO, "%Y-%m-%d")
        expected_days = (end - start).days + 1
        
        if unique_dates < expected_days:
            print(f"   ⚠️  Missing dates: {expected_days - unique_dates} days")
        else:
            print(f"   ✅ Date coverage looks complete")
    else:
        print("   ⚠️  No date information in database")
else:
    print("   ⚠️  No date information found")
    print("   Note: Date information comes from hsp_service_details table")

print("")

# Check route-date combinations
print("   📊 Route Coverage Details:")
for route in EXPECTED_ROUTES:
    origin, dest = route.split('-')
    cursor.execute("""
        SELECT COUNT(*) 
        FROM hsp_service_metrics 
        WHERE origin = ? AND destination = ?
    """, (origin, dest))
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"      ✅ {route}: {count:,} records")
    else:
        print(f"      ❌ {route}: 0 records (MISSING)")

conn.close()
PYTHON_EOF
else
    echo "   ⚠️  python3 not found. Cannot analyze missing data."
fi

echo ""
echo "💡 To resume collection:"
echo "   ./run_phase1_background.sh"
echo ""
echo "   (It will automatically skip completed routes if skip_completed is enabled)"

