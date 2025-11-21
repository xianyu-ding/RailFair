#!/bin/bash
# Monitor Phase 2 collection progress in real-time
# Usage: ./monitor_phase2.sh [refresh_interval_seconds]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REFRESH_INTERVAL="${1:-10}"  # Default 10 seconds
LOG_DIR="logs"
DATA_DIR="data"

# Find latest PID file
PID_FILE=$(ls -t "$LOG_DIR"/phase2_batch_*.pid 2>/dev/null | head -1)

if [ -z "$PID_FILE" ] || [ ! -f "$PID_FILE" ]; then
    echo "❌ No Phase 2 process found. Start with: ./run_phase2_background.sh"
    exit 1
fi

PID=$(cat "$PID_FILE")
TIMESTAMP=$(basename "$PID_FILE" .pid | sed 's/phase2_batch_//')
LOG_FILE="${LOG_DIR}/phase2_batch_${TIMESTAMP}.log"
PROGRESS_FILE="${DATA_DIR}/progress_phase2.json"
DB_FILE="${DATA_DIR}/railfair.db"

echo "📊 Phase 2 Collection Monitor (Refresh: ${REFRESH_INTERVAL}s)"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "═══════════════════════════════════════════════════════════"
    echo "📊 Phase 2 Batch Collection Monitor"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Check if process is running
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Status: RUNNING"
        ELAPSED=$(ps -p "$PID" -o etime= | xargs)
        echo "⏱️  Elapsed: $ELAPSED"
    else
        echo "❌ Status: NOT RUNNING"
    fi
    echo ""
    
    # Extract task progress from log file
    if [ -f "$LOG_FILE" ] && command -v python3 > /dev/null 2>&1; then
        python3 << EOF
import json
import re
from datetime import datetime, timedelta

try:
    # Read log file
    with open("$LOG_FILE", 'r') as f:
        log_content = f.read()
    
    # Extract total tasks from "Total combinations: X"
    total_match = re.search(r'Total combinations: (\d+)', log_content)
    total_tasks = int(total_match.group(1)) if total_match else None
    
    # Extract completed tasks from "Task X/Y" or "Progress: X/Y tasks"
    completed_tasks = 0
    task_matches = re.findall(r'Task (\d+)/(\d+)', log_content)
    if task_matches:
        # Get the highest task number completed
        completed_tasks = max([int(m[0]) for m in task_matches])
        if total_tasks is None:
            total_tasks = max([int(m[1]) for m in task_matches])
    
    # Also check "Progress: X/Y tasks"
    progress_matches = re.findall(r'Progress: (\d+)/(\d+) tasks', log_content)
    if progress_matches:
        completed_tasks = max(completed_tasks, max([int(m[0]) for m in progress_matches]))
        if total_tasks is None:
            total_tasks = max([int(m[1]) for m in progress_matches])
    
    # Fallback: Count task lines (Task X/Y) even if not all are completed
    if total_tasks is None and task_matches:
        total_tasks = max([int(m[1]) for m in task_matches])
    
    # Count skipped/completed/failed tasks from log patterns
    skipped_count = len(re.findall(r'⏭️.*Skipping|Task skipped', log_content))
    completed_count = len(re.findall(r'✅ Task completed', log_content))
    failed_count = len(re.findall(r'❌.*Failed to process task|Server error: (50[23]|502|503)', log_content))
    
    # If we have counts but no task numbers, estimate progress
    if total_tasks and completed_tasks == 0:
        # Try to estimate from pattern counts
        estimated_completed = skipped_count + completed_count
        if estimated_completed > 0:
            completed_tasks = min(estimated_completed, total_tasks)
    
    # Extract start time from process or log
    start_time_match = re.search(r'Started: (.+)', log_content)
    if not start_time_match:
        # Try to get from process start time
        import subprocess
        try:
            result = subprocess.run(['ps', '-p', '$PID', '-o', 'lstart='], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                start_time_str = result.stdout.strip()
                # Parse ps date format
                from datetime import datetime
                start_time = datetime.strptime(start_time_str, '%a %b %d %H:%M:%S %Y')
        except:
            start_time = None
    else:
        try:
            start_time = datetime.fromisoformat(start_time_match.group(1).replace('Z', '+00:00'))
        except:
            start_time = None
    
    # Calculate progress
    if total_tasks and completed_tasks > 0:
        progress_pct = (completed_tasks / total_tasks) * 100
        remaining_tasks = total_tasks - completed_tasks
        
        # Calculate time estimates
        if start_time:
            elapsed_time = datetime.now() - start_time.replace(tzinfo=None) if start_time.tzinfo else datetime.now() - start_time
            elapsed_seconds = elapsed_time.total_seconds()
            
            if completed_tasks > 0:
                avg_time_per_task = elapsed_seconds / completed_tasks
                estimated_remaining_seconds = avg_time_per_task * remaining_tasks
                estimated_remaining = timedelta(seconds=int(estimated_remaining_seconds))
                
                # Format time
                hours = int(estimated_remaining.total_seconds() // 3600)
                minutes = int((estimated_remaining.total_seconds() % 3600) // 60)
                if hours > 0:
                    remaining_str = f"{hours}h {minutes}m"
                else:
                    remaining_str = f"{minutes}m"
                
                # Calculate speed
                tasks_per_minute = (completed_tasks / elapsed_seconds) * 60 if elapsed_seconds > 0 else 0
            else:
                remaining_str = "Calculating..."
                tasks_per_minute = 0
        else:
            remaining_str = "N/A"
            tasks_per_minute = 0
        
        # Progress bar
        bar_length = 40
        filled = int(bar_length * completed_tasks / total_tasks)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        print("📊 Task Progress:")
        print(f"   Tasks: {completed_tasks}/{total_tasks} completed ({remaining_tasks} remaining)")
        print(f"   [{bar}] {progress_pct:.1f}%")
        print(f"   Speed: {tasks_per_minute:.1f} tasks/min")
        if remaining_str != "N/A":
            print(f"   ⏱️  Estimated remaining: {remaining_str}")
    else:
        print("📊 Task Progress:")
        if total_tasks:
            print(f"   Total tasks: {total_tasks}")
        print(f"   Completed: {completed_tasks}")
        if not total_tasks:
            print("   (Waiting for task information...)")
    
    # Also show route-based progress
    try:
        with open("$PROGRESS_FILE", 'r') as f:
            progress = json.load(f)
            
            # Route name mapping (old -> new)
            route_name_map = {
                "KGX-EDR": "KGX-EDB",
                "VIC-BHM": "EUS-BHM",  # Updated: MYB-BHM → EUS-BHM
                "MYB-BHM": "EUS-BHM",  # Updated route
                "MAN-LEE": "MCV-LDS",  # Updated: MAN-LDS → MCV-LDS
                "MAN-LDS": "MCV-LDS",  # Updated route
                "MAN-LIV": "MCV-LIV",  # Updated route
                "EDR-GLC": "EDB-GLC"
            }
            
            def map_route_name(route):
                return route_name_map.get(route, route)
            
            completed_routes_list = [map_route_name(r) for r in progress.get('completed_routes', [])]
            failed_routes_list = [map_route_name(r) for r in progress.get('failed_routes', [])]
            
            completed_routes = len(completed_routes_list)
            failed_routes = len(failed_routes_list)
            total_records = progress.get('total_records', 0)
            
            print("")
            print("📈 Route Progress:")
            print(f"   Routes: {completed_routes}/10 completed, {failed_routes} failed")
            print(f"   Records: {total_records:,}")
            
            if completed_routes > 0:
                print("")
                print("   ✅ Completed routes:")
                for route in completed_routes_list[:5]:
                    print(f"      • {route}")
                if completed_routes > 5:
                    print(f"      ... and {completed_routes - 5} more")
    except FileNotFoundError:
        pass
    except Exception:
        pass
        
except Exception as e:
    print(f"   Error calculating progress: {e}")
    import traceback
    traceback.print_exc()
EOF
    fi
    echo ""
    
    # Database stats
    if [ -f "$DB_FILE" ] && command -v sqlite3 > /dev/null 2>&1; then
        METRICS_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM hsp_service_metrics;" 2>/dev/null || echo "0")
        DETAILS_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM hsp_service_details;" 2>/dev/null || echo "0")
        echo "💾 Database:"
        echo "   Metrics: $METRICS_COUNT records"
        echo "   Details: $DETAILS_COUNT records"
        echo ""
    fi
    
    # Recent log (last 8 lines)
    if [ -f "$LOG_FILE" ]; then
        echo "📝 Recent Activity:"
        echo "───────────────────────────────────────────────────────"
        tail -n 8 "$LOG_FILE" | sed 's/^/   /'
    fi
    
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "Next update in ${REFRESH_INTERVAL}s... (Ctrl+C to stop)"
    
    sleep "$REFRESH_INTERVAL"
done

