#!/bin/bash
# Check actual route completion status by verifying database data
# Usage: ./check_route_status.sh [phase1|phase2]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PHASE="${1:-phase1}"
DB_FILE="data/railfair.db"
PROGRESS_FILE="data/progress_${PHASE}.json"

echo "📊 Route Completion Status Check (${PHASE})"
echo "=============================================="
echo ""

# Check database
if [ ! -f "$DB_FILE" ]; then
    echo "❌ Database file not found: $DB_FILE"
    exit 1
fi

# Get routes from database
echo "📈 Routes in Database:"
echo "──────────────────────"
sqlite3 "$DB_FILE" << 'EOF'
SELECT 
    origin || '-' || destination as route,
    COUNT(*) as metrics_count,
    COUNT(DISTINCT DATE(fetch_timestamp)) as unique_days
FROM hsp_service_metrics
GROUP BY origin, destination
ORDER BY route;
EOF
echo ""

# Get date coverage
echo "📅 Date Coverage:"
echo "────────────────"
sqlite3 "$DB_FILE" << 'EOF'
SELECT 
    COUNT(DISTINCT date_of_service) as unique_dates,
    MIN(date_of_service) as earliest,
    MAX(date_of_service) as latest
FROM hsp_service_details
WHERE date_of_service IS NOT NULL;
EOF
echo ""

# Check progress file
if [ -f "$PROGRESS_FILE" ]; then
    echo "📋 Progress File Status:"
    echo "───────────────────────"
    
    # Use Python to parse JSON (more reliable than jq)
    python3 << PYTHON_EOF
import json
import os

progress_file = "$PROGRESS_FILE"
if os.path.exists(progress_file):
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    completed = progress.get('completed_routes', [])
    failed = progress.get('failed_routes', [])
    
    print(f"   Marked as completed: {len(completed)} routes")
    print(f"   Marked as failed: {len(failed)} routes")
    print("")
    
    if completed:
        print("   ✅ Completed routes in file:")
        for route in completed:
            print(f"      • {route}")
    print("")
    
    if failed:
        print("   ❌ Failed routes in file:")
        for route_info in failed[:5]:  # Show first 5
            if isinstance(route_info, dict):
                print(f"      • {route_info.get('route', 'Unknown')}: {route_info.get('error', 'Unknown error')}")
            else:
                print(f"      • {route_info}")
        if len(failed) > 5:
            print(f"      ... and {len(failed) - 5} more")
PYTHON_EOF
else
    echo "   ⚠️  Progress file not found: $PROGRESS_FILE"
fi

echo ""
echo "💡 Note:"
echo "   - Routes marked as 'completed' in progress file may not be fully complete"
echo "   - Check database records above to verify actual data coverage"
echo "   - If collection was interrupted, some routes may be partially complete"
echo ""
echo "🔍 To verify actual completion, check:"
echo "   1. Database has records for all expected routes"
echo "   2. Date coverage matches expected date range"
echo "   3. Each route has sufficient records (varies by route)"
echo ""

