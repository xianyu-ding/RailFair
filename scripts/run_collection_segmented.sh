#!/bin/bash
# Segmented Collection Runner
# Splits large date ranges into smaller chunks and runs them sequentially in background

set -e

CONFIG_FILE="${1:-configs/hsp_config_phase1.yaml}"
PHASE_NAME="${2:-Phase 1}"
CHUNK_DAYS="${3:-14}"  # Default: 14 days per chunk (2 weeks)
LOG_DIR="logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "======================================================================"
echo "  Segmented HSP Data Collection"
echo "======================================================================"
echo ""
echo "Config: $CONFIG_FILE"
echo "Phase: $PHASE_NAME"
echo "Chunk size: $CHUNK_DAYS days"
echo ""

# Load date range from config (requires python)
START_DATE=$(python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
    print(config['data_collection']['from_date'])
")

END_DATE=$(python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
    print(config['data_collection']['to_date'])
")

echo "Original date range: $START_DATE to $END_DATE"
echo ""

# Generate date chunks
CHUNKS=$(python3 <<EOF
from datetime import datetime, timedelta

def split_date_range(start_date, end_date, chunk_days):
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    chunks = []
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((current.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        current = chunk_end + timedelta(days=1)
    return chunks

chunks = split_date_range('$START_DATE', '$END_DATE', $CHUNK_DAYS)
for i, (from_date, to_date) in enumerate(chunks, 1):
    print(f"{i}|{from_date}|{to_date}")
EOF
)

TOTAL_CHUNKS=$(echo "$CHUNKS" | wc -l | tr -d ' ')
echo "Split into $TOTAL_CHUNKS chunks:"
echo ""

# Display chunks
echo "$CHUNKS" | while IFS='|' read -r num from_date to_date; do
    echo "  Chunk $num: $from_date to $to_date"
done

echo ""
read -p "Continue with segmented collection? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Run each chunk sequentially
CHUNK_NUM=1
echo "$CHUNKS" | while IFS='|' read -r num from_date to_date; do
    LOG_FILE="$LOG_DIR/phase1_chunk${num}.log"
    
    echo ""
    echo "======================================================================"
    echo "  Starting Chunk $num/$TOTAL_CHUNKS: $from_date to $to_date"
    echo "======================================================================"
    echo "Log file: $LOG_FILE"
    echo ""
    
    # Run in background with nohup
    nohup python3 fetch_hsp_batch.py "$CONFIG_FILE" \
        --phase "$PHASE_NAME - Chunk $num" \
        --date-from "$from_date" \
        --date-to "$to_date" \
        > "$LOG_FILE" 2>&1 &
    
    PID=$!
    echo "Started with PID: $PID"
    echo "Waiting for chunk $num to complete..."
    
    # Wait for this chunk to finish
    wait $PID
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Chunk $num completed successfully"
    else
        echo "❌ Chunk $num failed with exit code $EXIT_CODE"
        echo "Check log: $LOG_FILE"
    fi
    
    # Random delay between chunks (30-90 seconds) to prevent rate limiting
    if [ $num -lt $TOTAL_CHUNKS ]; then
        DELAY=$((30 + RANDOM % 60))
        echo "⏸️  Waiting ${DELAY}s before next chunk (random delay)..."
        sleep $DELAY
    fi
done

echo ""
echo "======================================================================"
echo "  All chunks completed!"
echo "======================================================================"
echo ""
echo "Log files:"
ls -lh "$LOG_DIR"/phase1_chunk*.log 2>/dev/null || echo "No log files found"

