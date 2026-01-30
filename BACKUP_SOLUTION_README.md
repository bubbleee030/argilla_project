# Argilla Auto-Backup Solution - Overview

## First thing first

A complete automated backup solution to protect your Argilla dataset from HuggingFace Spaces' 36-hour sleep/delete mechanism.

### Key Features

- **Smart Content Detection**: Only creates new backups when data actually changes (not just timestamps)
- **Discord Notifications**: Get instant alerts when backups fail or succeed
- **Automatic Git Integration**: Backs up to Git automatically with each change
- **Backup Rotation**: Keeps last N backups to save disk space
- **Error Recovery**: Automatic cleanup on failures
- **Chinese Character Support**: Proper UTF-8 encoding for all characters

## Files Created

### 1. **Backup Script** (`scripts/auto_backup.py`)
- Standalone Python script for managing backups
- Features:
  - One-time backups
  - Scheduled backups (background process)
  - Backup rotation (keeps last N backups)
  - Comprehensive logging
  - Metadata tracking
  - Error recovery

### 2. **Bash Wrapper** (`scripts/backup.sh`)
- Easy-to-use shell script wrapper
- Commands: `backup`, `schedule`, `list`, `help`
- Colorized output for clarity

### 3. **Setup Guide** (`AUTO_BACKUP_SETUP.md`)
- Detailed configuration instructions
- HF Spaces integration options
- Troubleshooting guide
- Restore procedures
- Security notes

### 4. **Quick Start** (`QUICK_START_BACKUP.md`)
- TL;DR setup (5 minutes)
- Step-by-step instructions
- Example commands
- Backup monitoring
- Integration examples

### 5. **Configuration Template** (`.env.template`)
- Copy to `.env` and fill in your credentials
- Example:
  ```
  ARGILLA_API_URL=https://bubble030-test-argilla.hf.space
  ARGILLA_API_KEY=your_api_key_here
  ```

## Quick Setup (5 Minutes)

```bash
cd /home/ubuntu/argilla_project

# 1. Install dependencies
pip install apscheduler requests

# 2. (Optional) Set up Discord webhook for error notifications
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"

# 3. Test Discord webhook (optional)
python scripts/auto_backup.py --test-webhook

# 4. Run backup once
python scripts/auto_backup.py --once

# 5. Schedule automatic backups every 2 hours
python scripts/auto_backup.py --schedule 120

# 6. List existing backups
python scripts/auto_backup.py --list
```

## What's New

### Smart Content Comparison
- Calculates SHA-256 hash of actual data (ignoring timestamps)
- Skips duplicate backups automatically
- Saves storage space and reduces Git noise

### Discord Notifications
- Error alerts: connection failures, backup failures, rotation errors
- Success notifications: with record count
- Easy setup with environment variable or CLI argument

### Automatic Git Integration
- Copies latest backup to `backups/latest/`
- Automatically commits and pushes to Git
- Only commits when content actually changes
- Restore with: `git pull`

### Git Configuration
```bash
# Set your credentials (already done in setup)
git config user.name "bubbleee030"
git config user.email "cmwang16@gmail.com"
```

# 1. Install dependency
pip install apscheduler

# 2. Setup credentials
cp .env.template .env
nano .env  # Add your API key

# 3. Test backup
python3 scripts/auto_backup.py --once

# 4. Schedule (every 2 hours)
python3 scripts/auto_backup.py --schedule 120 &
```

## Key Features

✅ **Automatic Backups**
- Run on schedule (hourly, daily, etc.)
- Background process (doesn't block your app)

✅ **Backup Rotation**
- Keeps only last N backups (default: 5)
- Automatically deletes old ones
- Saves storage space

✅ **Comprehensive Logging**
- All operations logged to `auto_backup.log`
- Easy troubleshooting
- Success/failure tracking

✅ **Metadata Tracking**
- Backup timestamp
- Record count
- File size
- Dataset info

✅ **Chinese Character Support**
- Uses `ensure_ascii=False`
- Proper UTF-8 encoding
- No Unicode escapes

✅ **Error Recovery**
- Handles connection failures
- Cleans up partial backups
- Detailed error messages

## Backup Location

```
/home/ubuntu/argilla_project/backups/
├── 模型回答偏好選擇_整合_20250129_150000/
│   ├── records.json              (all 800 records)
│   ├── backup_metadata.json
│   └── .argilla/
│       ├── settings.json
│       └── dataset.json
└── ... (more backups)
```

## Usage Examples

### One-Time Backup
```bash
python3 scripts/auto_backup.py --once
```

### Schedule Every 2 Hours
```bash
python3 scripts/auto_backup.py --schedule 120 &
```

### Schedule Every 12 Hours
```bash
python3 scripts/auto_backup.py --schedule 720 &
```

### List All Backups
```bash
python3 scripts/auto_backup.py --list
```

### Using Bash Wrapper
```bash
./scripts/backup.sh backup           # Run once
./scripts/backup.sh schedule 120     # Schedule
./scripts/backup.sh list             # List backups
```

## Restore from Backup

```python
import argilla as rg

client = rg.Argilla(api_url="...", api_key="...")

# Restore specific backup
dataset = rg.Dataset.from_disk(
    path="./backups/模型回答偏好選擇_整合_20250129_150000",
    name="restored_dataset",
    client=client,
    with_records=True
)

dataset.create()
```

## For HuggingFace Spaces

### Recommended Configuration

Since HF Spaces have 36-hour sleep/delete:

```bash
# Backup every 12 hours (gives 3 backups before deletion)
# Keep last 5 backups (covers 60 hours of history)
python3 scripts/auto_backup.py --schedule 720 &
```

### Integration in Docker

Add to Dockerfile:
```dockerfile
RUN apt-get install -y cron
RUN echo "0 */12 * * * cd /app && python3 scripts/auto_backup.py --once" | crontab -
```

### Integration in app.py

```python
from threading import Thread
from scripts.auto_backup import ArgillaBackupManager

backup_mgr = ArgillaBackupManager(...)
Thread(target=backup_mgr.run_backup_cycle, daemon=True).start()
```

## Storage Estimates

- Dataset with 800 records ≈ 45-50 MB per backup
- 5 backups (default rotation) ≈ 225-250 MB total
- No practical storage issues

## Important Caveats

### ⚠️ Discarded Responses Not Backed Up

As discovered earlier, **discarded responses are NOT included** in backups. This is an Argilla API limitation, not a backup issue.

Backups include:
- ✅ All submitted responses
- ✅ All draft responses
- ✅ All metadata
- ❌ Discarded responses

### ⚠️ Security Notes

- Don't commit `.env` to git
- Add to `.gitignore`:
  ```
  .env
  auto_backup.log
  backups/
  ```
- API keys are sensitive - keep backups private

## Monitoring

### Check Latest Backups
```bash
python3 scripts/auto_backup.py --list
```

### View Logs
```bash
tail -f auto_backup.log
```

### Check If Running
```bash
ps aux | grep auto_backup
```

## Troubleshooting

### Error: "No module named 'argilla'"
```bash
pip install argilla
```

### Error: "APScheduler not installed"
```bash
pip install apscheduler
```

### Error: "Connection failed"
1. Check `.env` credentials
2. Verify Argilla is running
3. Test: `python3 scripts/auto_backup.py --list`

## Next Steps

1. **Immediate**: Run first backup to test
   ```bash
   python3 scripts/auto_backup.py --once
   ```

2. **Today**: Set up automatic backups
   ```bash
   python3 scripts/auto_backup.py --schedule 720 &
   ```

3. **This Week**: Verify restore works
   ```bash
   python3 -c "
   import argilla as rg
   client = rg.Argilla(api_url='...', api_key='...')
   dataset = rg.Dataset.from_disk('./backups/...', client=client, with_records=True)
   print('✓ Restore test passed')
   "
   ```

4. **For Production**: Deploy with Docker/cron for permanent backups

## Documentation Files

- 📖 [QUICK_START_BACKUP.md](./QUICK_START_BACKUP.md) - 5-minute setup guide
- 📖 [AUTO_BACKUP_SETUP.md](./AUTO_BACKUP_SETUP.md) - Detailed configuration guide

## Support

For issues:
1. Check `auto_backup.log` for error messages
2. Verify credentials in `.env`
3. Test connectivity: `python3 scripts/auto_backup.py --list`
4. Check disk space: `df -h`

Your Argilla dataset is now protected! 🚀
