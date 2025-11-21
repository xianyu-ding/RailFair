# RailFair Statistics CRON Configuration

## 📋 Overview

This document explains how to set up automatic statistics updates using CRON.

## 🔧 Setup Instructions

### 1. Make Script Executable

```bash
chmod +x update_statistics.sh
```

### 2. Edit Project Path

Open `update_statistics.sh` and update the project directory:

```bash
PROJECT_DIR="/your/path/to/uk-rail-delay-predictor"
```

### 3. Test Manual Run

```bash
# Basic update
./update_statistics.sh

# With report generation
./update_statistics.sh --report
```

### 4. Configure CRON

Open crontab editor:

```bash
crontab -e
```

Add one of the following schedules:

## 📅 Recommended CRON Schedules

### Option 1: Daily at 2 AM (Recommended for Production)
```cron
0 2 * * * /path/to/uk-rail-delay-predictor/update_statistics.sh >> /path/to/uk-rail-delay-predictor/logs/cron.log 2>&1
```

**Why 2 AM?**
- Low system load
- After daily data collection might have completed
- Before morning user traffic

### Option 2: Every 6 Hours (For Development)
```cron
0 */6 * * * /path/to/uk-rail-delay-predictor/update_statistics.sh >> /path/to/uk-rail-delay-predictor/logs/cron.log 2>&1
```

**Use cases:**
- Frequent data updates during development
- Testing cache expiration
- Monitoring data freshness

### Option 3: Weekly on Sunday at 3 AM (For Light Load)
```cron
0 3 * * 0 /path/to/uk-rail-delay-predictor/update_statistics.sh --report >> /path/to/uk-rail-delay-predictor/logs/cron.log 2>&1
```

**Use cases:**
- Low-traffic production
- Weekly performance reports
- Minimal resource usage

### Option 4: After Data Collection (Chained)
```cron
# Run data collection at 1 AM
0 1 * * * /path/to/uk-rail-delay-predictor/fetch_hsp_batch.py config.yaml

# Run statistics update at 2 AM (after collection)
0 2 * * * /path/to/uk-rail-delay-predictor/update_statistics.sh >> /path/to/uk-rail-delay-predictor/logs/cron.log 2>&1
```

## 🔍 CRON Schedule Syntax

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
│ │ │ │ │
* * * * * command
```

### Examples:
- `0 2 * * *` - Daily at 2:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 3 * * 0` - Every Sunday at 3:00 AM
- `0 0 1 * *` - First day of every month at midnight
- `*/30 * * * *` - Every 30 minutes

## 📊 Monitoring

### Check CRON Logs

```bash
# View today's logs
tail -f logs/stats_update_$(date +%Y-%m-%d).log

# View CRON output
tail -f logs/cron.log
```

### Verify CRON is Running

```bash
# List your CRON jobs
crontab -l

# Check CRON service status (Mac)
sudo launchctl list | grep cron

# Check CRON service status (Linux)
systemctl status cron
```

## 🚨 Troubleshooting

### Issue 1: CRON Not Running

**Symptoms:** No logs generated

**Solutions:**
1. Check CRON service is running
2. Verify script path is absolute (not relative)
3. Check script permissions (`chmod +x`)
4. Check CRON log for errors

### Issue 2: Python Not Found

**Symptoms:** `python3: command not found`

**Solution:** Use absolute Python path in script
```bash
# Find Python path
which python3

# Update in update_statistics.sh
PYTHON="/usr/local/bin/python3"  # or your path
```

### Issue 3: Permission Denied

**Symptoms:** `Permission denied` errors

**Solutions:**
```bash
# Make script executable
chmod +x update_statistics.sh

# Check database file permissions
chmod 644 data/railfair.db

# Check directory permissions
chmod 755 data logs
```

### Issue 4: Virtual Environment Not Activated

**Symptoms:** Module import errors

**Solution:** Update script to use virtual environment:
```bash
# In update_statistics.sh, add before Python commands:
source "$PROJECT_DIR/venv/bin/activate"
```

## 📈 Performance Considerations

### Resource Usage

| Schedule | CPU Usage | Disk I/O | Recommended For |
|----------|-----------|----------|-----------------|
| Every hour | Medium | High | Development |
| Every 6 hours | Low | Medium | Testing |
| Daily | Low | Low | Production |
| Weekly | Very Low | Very Low | Light load |

### Execution Time

Based on 58,000 records:
- Statistics calculation: ~10-30 seconds
- Cache cleanup: ~1-2 seconds
- Report generation: ~5-10 seconds
- **Total: ~20-45 seconds**

## 🔐 Security

### Best Practices

1. **Use Dedicated User**
```bash
# Create service user (Linux)
sudo useradd -r -s /bin/bash railfair
sudo -u railfair crontab -e
```

2. **Limit File Permissions**
```bash
chmod 700 update_statistics.sh  # Only owner can execute
chmod 600 data/railfair.db      # Only owner can read/write
```

3. **Log Rotation**
```bash
# Add to logrotate config
# /etc/logrotate.d/railfair
/path/to/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## 📝 Maintenance

### Weekly Tasks
- [ ] Check CRON logs for errors
- [ ] Verify statistics are updating
- [ ] Monitor disk space usage

### Monthly Tasks
- [ ] Review and archive old logs
- [ ] Check database size growth
- [ ] Optimize if needed

### As Needed
- [ ] Update schedule based on usage
- [ ] Adjust cache TTL
- [ ] Add new statistics calculations

## 🎯 Integration with Week 2

When you move to Week 2 (Prediction Engine), the statistics cache will be automatically used by:

1. **Baseline Predictor** - Uses route statistics for predictions
2. **API Endpoints** - Fast queries via cached statistics
3. **Recommendation Engine** - Compares routes using pre-calculated metrics

## 📚 Additional Resources

- [CRON Guru](https://crontab.guru) - CRON schedule expression editor
- [Logrotate Manual](https://linux.die.net/man/8/logrotate)
- SQLite [Performance Tuning](https://www.sqlite.org/performance.html)

---

**Last Updated:** 2025-11-13  
**Status:** ✅ Production Ready  
**Next Review:** Week 2 - After Prediction Engine Integration
