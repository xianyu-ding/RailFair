#!/bin/bash
# Test New Routes: MYB-BMO, MYB-OXF, MAN-NCL, MAN-SHF
# Date Range: 2024-12-01 to 2024-12-07 (7 days, WEEKDAY only)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="configs/hsp_config_test_new_routes.yaml"
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/test_new_routes_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

echo "======================================================================"
echo "🧪 Testing New Routes"
echo "======================================================================"
echo ""
echo "📋 Test Configuration:"
echo "   Routes: MYB-BMO, MYB-OXF, MAN-NCL, MAN-SHF"
echo "   Date Range: 2024-12-01 to 2024-12-07 (7 days)"
echo "   Day Types: WEEKDAY"
echo "   Time Window: 0600-2200"
echo ""
echo "📊 Estimated:"
echo "   Total Tasks: ~4 tasks (4 routes × 1 date chunk × 1 day type)"
echo "   Estimated Time: ~5-10 minutes"
echo ""

# Run test
echo "🚀 Starting route test..."
echo "   Config: $CONFIG_FILE"
echo "   Log file: $LOG_FILE"
echo ""

python3 fetch_hsp_batch.py \
  "$CONFIG_FILE" \
  --phase "TEST_NEW_ROUTES" \
  2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "======================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test completed!"
else
    echo "❌ Test failed with exit code: $EXIT_CODE"
fi
echo "======================================================================"
echo ""
echo "📊 Checking results..."

# Check results from statistics file
STATS_FILE="data/stats_test_new_routes.json"
if [ -f "$STATS_FILE" ]; then
    echo ""
    echo "📈 Data collected for test routes:"
    python3 << EOF
import json
import sys

try:
    with open('$STATS_FILE', 'r') as f:
        stats = json.load(f)
    
    routes = stats.get('routes', {})
    if routes:
        for route, data in routes.items():
            records = data.get('records', 0)
            status = "✅" if records > 0 else "❌"
            print(f"   {status} {route}: {records} records")
    else:
        print("   No route data found in statistics")
except Exception as e:
    print(f"   Error reading statistics: {e}")
EOF
else
    echo "   Statistics file not found: $STATS_FILE"
fi

echo ""
echo "======================================================================"
echo "📄 Full log: $LOG_FILE"
echo "======================================================================"

exit $EXIT_CODE

