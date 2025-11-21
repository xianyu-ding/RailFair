#!/bin/bash
# ============================================================================
# RailFair Statistics Auto-Update Script
# 用于CRON定时自动更新统计数据
# ============================================================================

# 配置
PROJECT_DIR="/Volumes/HP P900/RailFair/V1D1/uk-rail-delay-predictor"
PYTHON="/usr/bin/python3"
LOG_DIR="$PROJECT_DIR/logs"
DB_PATH="$PROJECT_DIR/data/railfair.db"

# 日期时间
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 日志文件
LOG_FILE="$LOG_DIR/stats_update_$DATE.log"

# ============================================================================
# 日志函数
# ============================================================================

log() {
    echo "[$TIME] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$TIME] ❌ ERROR: $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo "[$TIME] ✅ SUCCESS: $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# 主程序
# ============================================================================

log "=========================================="
log "RailFair Statistics Auto-Update"
log "=========================================="

# 切换到项目目录
cd "$PROJECT_DIR" || {
    log_error "Cannot change to project directory: $PROJECT_DIR"
    exit 1
}

log "Project directory: $PROJECT_DIR"

# 检查数据库
if [ ! -f "$DB_PATH" ]; then
    log_error "Database not found: $DB_PATH"
    exit 1
fi

log "Database found: $DB_PATH"

# 运行统计计算
log "Starting statistics calculation..."

$PYTHON calculate_stats.py "$DB_PATH" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log_success "Statistics calculated successfully"
else
    log_error "Statistics calculation failed"
    exit 1
fi

# 清理过期缓存
log "Cleaning expired cache..."

$PYTHON -c "
from query_stats import StatisticsQuery
with StatisticsQuery('$DB_PATH') as query:
    deleted = query.clean_expired_cache()
    print(f'Cleaned {deleted} expired cache entries')
" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log_success "Cache cleaned"
else
    log_error "Cache cleaning failed"
fi

# 生成快照报告（可选）
if [ "$1" = "--report" ]; then
    log "Generating statistics report..."
    
    REPORT_FILE="$PROJECT_DIR/data/stats_snapshot_$TIMESTAMP.txt"
    $PYTHON query_stats.py "$DB_PATH" > "$REPORT_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Report generated: $REPORT_FILE"
    else
        log_error "Report generation failed"
    fi
fi

# 完成
log "=========================================="
log "Statistics update completed"
log "=========================================="

exit 0
