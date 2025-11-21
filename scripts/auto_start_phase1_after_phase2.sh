#!/bin/bash
# Auto-start Phase 1, 2, 3 sequentially with fixed intervals
# Phase 1 → wait 3h → Phase 2 → wait 2h → Phase 3
# No confirmations, no loops

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="logs"
DATA_DIR="data"

echo "======================================================================"
echo "🚀 Auto-start Sequential Phase Collection"
echo "======================================================================"
echo ""
echo "📋 Schedule:"
echo "   1. Phase 1 → Wait 3 hours → Phase 2 → Wait 2 hours → Phase 3"
echo "   2. No confirmations required"
echo "   3. Fixed intervals (no loops)"
echo ""

# Clean up stale PID files first
cleanup_stale_pids() {
    local phase=$1
    local pid_pattern="${phase}_batch_*.pid"
    for PID_FILE in "$LOG_DIR"/$pid_pattern; do
        if [ -f "$PID_FILE" ]; then
            local PID=$(cat "$PID_FILE")
            if ! ps -p "$PID" > /dev/null 2>&1; then
                rm -f "$PID_FILE"
            fi
        fi
    done
}

cleanup_stale_pids "phase1"
cleanup_stale_pids "phase2"
cleanup_stale_pids "phase3"

# Check if a phase is running
check_phase_running() {
    local phase=$1
    local pid_pattern="${phase}_batch_*.pid"
    local pid_file=$(ls -t "$LOG_DIR"/$pid_pattern 2>/dev/null | head -1)
    
    if [ -z "$pid_file" ] || [ ! -f "$pid_file" ]; then
        return 1
    fi
    
    local pid=$(cat "$pid_file")
    if ps -p "$pid" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check if a phase is complete
check_phase_complete() {
    local phase=$1
    local pid_pattern="${phase}_batch_*.pid"
    local pid_file=$(ls -t "$LOG_DIR"/$pid_pattern 2>/dev/null | head -1)
    
    if [ -z "$pid_file" ] || [ ! -f "$pid_file" ]; then
        return 0  # No PID file means not started or already cleaned up
    fi
    
    local pid=$(cat "$pid_file")
    if ! ps -p "$pid" > /dev/null 2>&1; then
        return 0  # Process not running means complete
    fi
    
    return 1  # Process still running
}

# Wait for a phase to complete
wait_for_phase() {
    local phase=$1
    local phase_name=$(echo "$phase" | tr '[:lower:]' '[:upper:]')
    local check_interval=30  # Check every 30 seconds
    
    echo "⏳ Waiting for $phase_name to complete..."
    
    while true; do
        if ! check_phase_running "$phase"; then
            if check_phase_complete "$phase"; then
                echo "✅ $phase_name completed!"
                return 0
            fi
        fi
        
        # Show progress
        local pid_pattern="${phase}_batch_*.pid"
        local pid_file=$(ls -t "$LOG_DIR"/$pid_pattern 2>/dev/null | head -1)
        if [ -n "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            local elapsed=$(ps -p "$pid" -o etime= 2>/dev/null | xargs || echo "unknown")
            echo "   $phase_name still running (Elapsed: $elapsed)..."
        fi
        
        sleep "$check_interval"
    done
}

# Start a phase
start_phase() {
    local phase=$1
    local phase_name=$(echo "$phase" | tr '[:lower:]' '[:upper:]')
    local script="run_${phase}_background.sh"
    
    echo ""
    echo "🚀 Starting $phase_name..."
    echo ""
    
    AUTO_START_MODE=1 ./"$script"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ $phase_name started successfully!"
        return 0
    else
        echo ""
        echo "❌ Failed to start $phase_name. Check logs for details."
        return 1
    fi
}

# Wait for a fixed interval
wait_interval() {
    local hours=$1
    local seconds=$((hours * 3600))
    local minutes=$((hours * 60))
    
    echo ""
    echo "⏸️  Waiting ${hours} hour(s) before next phase..."
    echo "   (This is a fixed interval, not checking completion)"
    
    # Show countdown every 5 minutes
    local remaining=$seconds
    while [ $remaining -gt 0 ]; do
        local remaining_hours=$((remaining / 3600))
        local remaining_mins=$(((remaining % 3600) / 60))
        
        if [ $((remaining % 300)) -eq 0 ] || [ $remaining -eq $seconds ]; then
            echo "   ⏱️  Remaining: ${remaining_hours}h ${remaining_mins}m"
        fi
        
        sleep 60
        remaining=$((remaining - 60))
    done
    
    echo "✅ Interval completed!"
}

# ============================================================================
# Main execution flow
# ============================================================================

# Step 1: Start Phase 1 (if not already running)
if check_phase_running "phase1"; then
    echo "ℹ️  Phase 1 is already running. Monitoring it..."
else
    echo "📋 Step 1: Starting Phase 1"
    if ! start_phase "phase1"; then
        echo "❌ Failed to start Phase 1. Exiting."
        exit 1
    fi
fi

# Step 2: Wait for Phase 1 to complete
wait_for_phase "phase1"

# Step 3: Wait 3 hours
wait_interval 3

# Step 4: Start Phase 2
echo ""
echo "📋 Step 2: Starting Phase 2"
if ! start_phase "phase2"; then
    echo "❌ Failed to start Phase 2. Exiting."
    exit 1
fi

# Step 5: Wait for Phase 2 to complete
wait_for_phase "phase2"

# Step 6: Wait 2 hours
wait_interval 2

# Step 7: Start Phase 3
echo ""
echo "📋 Step 3: Starting Phase 3"
if ! start_phase "phase3"; then
    echo "❌ Failed to start Phase 3. Exiting."
    exit 1
fi

# Step 8: Wait for Phase 3 to complete
wait_for_phase "phase3"

# All done!
echo ""
echo "======================================================================"
echo "✅ All phases completed successfully!"
echo "======================================================================"
echo ""
echo "📊 Summary:"
echo "   Phase 1: ✅ Complete"
echo "   Phase 2: ✅ Complete"
echo "   Phase 3: ✅ Complete"
echo ""
echo "🎉 Data collection finished!"
echo ""

exit 0
