#!/bin/bash
# Clean progress file by removing routes that don't have data in database
# Usage: ./clean_progress_file.sh [phase1|phase2]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PHASE="${1:-phase1}"
DB_FILE="data/railfair.db"
PROGRESS_FILE="data/progress_${PHASE}.json"

echo "🧹 Cleaning Progress File (${PHASE})"
echo "======================================"
echo ""

# Check files
if [ ! -f "$DB_FILE" ]; then
    echo "❌ Database file not found: $DB_FILE"
    exit 1
fi

if [ ! -f "$PROGRESS_FILE" ]; then
    echo "❌ Progress file not found: $PROGRESS_FILE"
    exit 1
fi

# Backup original
BACKUP_FILE="${PROGRESS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$PROGRESS_FILE" "$BACKUP_FILE"
echo "💾 Backup created: $BACKUP_FILE"
echo ""

# Get routes with data from database
echo "📊 Routes with data in database:"
ROUTES_WITH_DATA=$(sqlite3 "$DB_FILE" << 'EOF'
SELECT DISTINCT origin || '-' || destination
FROM hsp_service_metrics
ORDER BY origin || '-' || destination;
EOF
)

echo "$ROUTES_WITH_DATA" | while read route; do
    if [ -n "$route" ]; then
        echo "   ✅ $route"
    fi
done
echo ""

# Clean progress file using Python
python3 << PYTHON_EOF
import json
import os
from datetime import datetime

progress_file = "$PROGRESS_FILE"
db_file = "$DB_FILE"
backup_file = "$BACKUP_FILE"

# Load progress
with open(progress_file, 'r') as f:
    progress = json.load(f)

# Get routes with data from database
import sqlite3
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute("""
    SELECT DISTINCT origin || '-' || destination
    FROM hsp_service_metrics
""")
routes_with_data = {row[0] for row in cursor.fetchall()}
conn.close()

# Clean completed routes
completed_routes = progress.get('completed_routes', [])
cleaned_completed = []
removed_completed = []

for route in completed_routes:
    if route in routes_with_data:
        cleaned_completed.append(route)
    else:
        removed_completed.append(route)

# Clean failed routes (keep only recent failures, remove old 405 errors)
failed_routes = progress.get('failed_routes', [])
cleaned_failed = []

for route_info in failed_routes:
    if isinstance(route_info, dict):
        error = route_info.get('error', '')
        # Keep failures that are not old 405 errors (those were fixed)
        if '405' not in error or 'GET' not in error:
            cleaned_failed.append(route_info)
    else:
        # Keep non-dict entries
        cleaned_failed.append(route_info)

# Update progress
progress['completed_routes'] = cleaned_completed
progress['failed_routes'] = cleaned_failed
progress['last_updated'] = datetime.now().isoformat()

# Save
with open(progress_file, 'w') as f:
    json.dump(progress, f, indent=2)

# Print summary
print("📋 Cleaning Summary:")
print("────────────────────")
print(f"   Completed routes: {len(completed_routes)} → {len(cleaned_completed)}")
if removed_completed:
    print(f"   Removed (no data): {len(removed_completed)}")
    for route in removed_completed:
        print(f"      • {route}")
print(f"   Failed routes: {len(failed_routes)} → {len(cleaned_failed)}")
print("")
print(f"✅ Progress file cleaned: {progress_file}")
print(f"💾 Original backed up to: {backup_file}")
PYTHON_EOF

echo ""
echo "✅ Done!"

