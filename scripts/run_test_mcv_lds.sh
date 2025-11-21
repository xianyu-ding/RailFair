#!/bin/bash
# Test MCV-LDS Route
# Date Range: 2024-12-01 to 2024-12-07 (7 days, WEEKDAY only)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="configs/hsp_config_test_mcv_lds.yaml"
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/test_mcv_lds_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

echo "======================================================================"
echo "🧪 Testing MCV-LDS Route"
echo "======================================================================"
echo ""
echo "📋 Test Configuration:"
echo "   Route: MCV-LDS (Manchester Victoria → Leeds)"
echo "   Date Range: 2024-12-01 to 2024-12-07 (7 days)"
echo "   Day Types: WEEKDAY"
echo "   Time Window: 0600-2200"
echo ""
echo "📊 Estimated:"
echo "   Total Tasks: 1 task (1 route × 1 date chunk × 1 day type)"
echo "   Estimated Time: ~2-5 minutes"
echo ""

# Run test
echo "🚀 Starting route test..."
echo "   Config: $CONFIG_FILE"
echo "   Log file: $LOG_FILE"
echo ""

python3 fetch_hsp_batch.py \
  "$CONFIG_FILE" \
  --phase "TEST_MCV_LDS" \
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
STATS_FILE="data/stats_test_mcv_lds.json"
if [ -f "$STATS_FILE" ]; then
    echo ""
    echo "📈 Data collected for MCV-LDS:"
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

