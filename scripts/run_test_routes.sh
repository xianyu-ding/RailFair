#!/bin/bash
# Test New Routes - Run test for EUS-BHM, MCV-LIV, MCV-LDS
# Date Range: 2024-12-01 to 2024-12-07 (First week of Phase 1)

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
CONFIG_FILE="configs/hsp_config_test_routes.yaml"
LOG_DIR="logs"
OUTPUT_DIR="data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/test_routes_${TIMESTAMP}.log"

# Create necessary directories
mkdir -p "$LOG_DIR" "$OUTPUT_DIR" "data/raw/hsp/test_routes"

# Check if Python script exists
if [ ! -f "fetch_hsp_batch.py" ]; then
    echo "❌ Error: fetch_hsp_batch.py not found in current directory"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Check for environment variables (attempt to source .env when missing)
if [ -z "$HSP_EMAIL" ] && [ -z "$HSP_USERNAME" ]; then
    if [ -f ".env" ]; then
        set -a
        # shellcheck disable=SC1091
        source .env
        set +a
    fi

    if [ -z "$HSP_EMAIL" ] && [ -z "$HSP_USERNAME" ]; then
        echo "⚠️  Warning: HSP_EMAIL or HSP_USERNAME not set"
        echo "   Make sure .env file exists or export environment variables"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo "======================================================================"
echo "🧪 Testing New Routes"
echo "======================================================================"
echo ""
echo "📋 Test Configuration:"
echo "   Routes: LST-BHM, PIC-LDS, BRI-BMO, BRI-BSW"
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

# Run with unbuffered output
PYTHONUNBUFFERED=1 python3 -u "$SCRIPT_DIR/fetch_hsp_batch.py" "$CONFIG_FILE" --phase "TEST_ROUTES" 2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "======================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test completed successfully!"
    echo ""
    echo "📊 Checking results..."
    
    # Quick check of results
    if command -v sqlite3 > /dev/null 2>&1 && [ -f "$OUTPUT_DIR/railfair.db" ]; then
        echo ""
        echo "📈 Data collected for test routes:"
        sqlite3 "$OUTPUT_DIR/railfair.db" << 'SQL'
SELECT 
    origin || '-' || destination as route,
    COUNT(*) as services
FROM hsp_service_metrics
WHERE (origin = 'EUS' AND destination = 'BHM')
   OR (origin = 'MCV' AND destination = 'LIV')
   OR (origin = 'MCV' AND destination = 'LDS')
GROUP BY origin, destination
ORDER BY services DESC;
SQL
    fi
else
    echo "❌ Test failed with exit code: $EXIT_CODE"
    echo "   Check log file: $LOG_FILE"
fi

echo "======================================================================"
echo ""
echo "📄 Full log: $LOG_FILE"
echo ""

exit $EXIT_CODE

