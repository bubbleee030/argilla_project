# Quick Start: Auto Backup for Argilla on HF Spaces

## TL;DR (Quick Setup)

```bash
cd /home/ubuntu/argilla_project

# 1. Install APScheduler (if not already installed)
pip install apscheduler

# 2. Copy template env file
cp .env.template .env

# 3. Edit .env with your credentials
nano .env

# 4. Run backup once
python3 scripts/auto_backup.py --once

# 5. Schedule automatic backups every 2 hours via tmux
tmux
python3 scripts/auto_backup.py --schedule 120 

# 6. List backups anytime
python3 scripts/auto_backup.py --list
```

## Setup Step-by-Step

### Step 1: Navigate to Project Directory

```bash
cd /home/ubuntu/argilla_project
```

### Step 2: Install Dependencies

```bash
# Install APScheduler for scheduling
pip install apscheduler

# Or if using conda
conda install apscheduler
```

### Step 3: Configure Credentials

```bash
# Copy the template
cp .env.template .env

# Edit with your Argilla credentials
nano .env
```

Your `.env` should look like:
```
ARGILLA_API_URL=https://bubble030-test-argilla.hf.space
ARGILLA_API_KEY=your_actual_api_key_here
```

### Step 4: Test the Backup

```bash
# Run backup once to verify it works
python3 scripts/auto_backup.py --once
```

**Expected output:**
```
2025-01-29 15:00:00 - root - INFO - STARTING BACKUP CYCLE
2025-01-29 15:00:00 - root - INFO - Connecting to Argilla...
2025-01-29 15:00:05 - root - INFO - ✅ Connected successfully
2025-01-29 15:00:05 - root - INFO - Starting backup...
2025-01-29 15:00:15 - root - INFO - ✅ Backup completed successfully
2025-01-29 15:00:15 - root - INFO - ✅ BACKUP CYCLE COMPLETED SUCCESSFULLY
```

### Step 5: Schedule Automatic Backups

Choose your backup interval:

**Every 2 hours** (recommended for HF Spaces):
```bash
python3 scripts/auto_backup.py --schedule 120 
```

**Every 6 hours**:
```bash
python3 scripts/auto_backup.py --schedule 360 
```

**Every 12 hours**:
```bash
python3 scripts/auto_backup.py --schedule 720 
```

**Every 24 hours**:
```bash
python3 scripts/auto_backup.py --schedule 1440 
```

## Using the Bash Wrapper (Optional)

If you prefer a simpler interface:

```bash
# Run backup once
./scripts/backup.sh backup

# Schedule backups every 2 hours
./scripts/backup.sh schedule 120

# List all backups
./scripts/backup.sh list

# Show help
./scripts/backup.sh help
```

## Checking Backups

### List All Backups

```bash
python3 scripts/auto_backup.py --list
```

### View Backup Metadata

```bash
cat ./backups/模型回答偏好選擇_整合_20250129_150000/backup_metadata.json
```

### Check Backup Size

```bash
du -sh ./backups/*/
```

### Monitor Backup Logs

```bash
# View last 20 lines of log
tail -20 auto_backup.log

# Follow log in real-time
tail -f auto_backup.log

# Count number of successful backups
grep "✅ BACKUP CYCLE COMPLETED" auto_backup.log | wc -l
```

## Storage Location

All backups are stored in: `/home/ubuntu/argilla_project/backups/`

```
backups/
├── 模型回答偏好選擇_整合_20250129_150000/
│   ├── records.json              (800 records ~45 MB)
│   ├── backup_metadata.json      (metadata)
│   └── .argilla/
│       ├── settings.json
│       └── dataset.json
├── 模型回答偏好選擇_整合_20250129_120000/
│   ├── records.json
│   ├── backup_metadata.json
│   └── .argilla/
│
└── ... (older backups)
```

## Important Information

### ✅ What Gets Backed Up
- ✅ All submitted responses
- ✅ All draft responses
- ✅ Dataset settings
- ✅ Dataset configuration
- ✅ Metadata (timestamps, record counts, etc.)

### ❌ What Does NOT Get Backed Up
- ❌ Discarded responses (Argilla filters them out)
- ❌ User accounts
- ❌ Workspace settings

### 📊 Backup Size Estimates

For a dataset with 800 records:
- ~45-50 MB per backup (including metadata)
- 5 backups = ~225-250 MB total storage

### ⏱️ Recommended Schedule for HF Spaces

HF Spaces delete after 36 hours of inactivity. Recommended setup:

```bash
# Backup every 12 hours
# This gives you 3 backups before deletion
python3 scripts/auto_backup.py --schedule 720 

# Keep last 5 backups
# Each backup ~45 MB, total ~225 MB
```

## Restoring from Backup

When you need to restore:

```python
import argilla as rg

client = rg.Argilla(
    api_url="https://bubble030-test-argilla.hf.space",
    api_key="your_api_key"
)

# Restore from specific backup
dataset = rg.Dataset.from_disk(
    path="./backups/模型回答偏好選擇_整合_20250129_150000",
    name="restored_dataset",
    workspace="argilla",
    client=client,
    with_records=True
)

# Create on server
dataset.create()
```

## Troubleshooting

### Error: "No module named 'argilla'"

```bash
# Install argilla first
pip install argilla

# Or if using your sft_env
source ~/sft_env/bin/activate
pip install argilla
```

### Error: "APScheduler not installed"

```bash
pip install apscheduler
```

### Error: "Connection failed"

1. Check API URL and key in `.env`
2. Verify Argilla is running
3. Test connectivity:
   ```bash
   python3 scripts/auto_backup.py --list
   ```

### Error: "Backup failed: Disk space"

Check available space:
```bash
df -h /home/ubuntu/argilla_project

# Delete old backups manually if needed
rm -rf ./backups/oldest_backup
```

### Backups Not Running (Scheduled)

1. Check if process is still running:
   ```bash
   ps aux | grep auto_backup
   ```

2. View logs:
   ```bash
   tail -50 auto_backup.log
   ```

3. Restart:
   ```bash
   pkill -f auto_backup.py
   python3 scripts/auto_backup.py --schedule 120 
   ```

## Running on HF Spaces Permanently

### Option 1: Docker + Cron (Recommended)

In your Dockerfile:
```dockerfile
RUN apt-get install -y cron
RUN echo "0 */12 * * * cd /home/ubuntu/argilla_project && python3 scripts/auto_backup.py --once >> auto_backup.log 2>&1" | crontab -
CMD ["cron", "-f"]
```

### Option 2: Background Process in app.py

```python
from threading import Thread
from argilla_project.scripts.auto_backup import ArgillaBackupManager

def start_backup_scheduler():
    backup_manager = ArgillaBackupManager(
        api_url="https://bubble030-test-argilla.hf.space",
        api_key="your_key",
        dataset_name="your_dataset"
    )
    
    # Run in background
    backup_manager.run_backup_cycle()

# Start backup thread on app startup
backup_thread = Thread(target=start_backup_scheduler, daemon=True)
backup_thread.start()
```

### Option 3: Scheduled Job in Gradio

```python
import gradio as gr
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(backup_manager.run_backup_cycle, 'interval', hours=12)
scheduler.start()

# Your Gradio interface...
```

## Example: Complete Integration

```bash
#!/bin/bash
# setup_argilla_backups.sh

cd /home/ubuntu/argilla_project

# 1. Install dependencies
pip install argilla apscheduler

# 2. Setup credentials
if [ ! -f .env ]; then
    cp .env.template .env
    echo "⚠️  Edit .env with your API credentials"
    echo "   nano .env"
    exit 1
fi

# 3. Create backups directory
mkdir -p backups

# 4. Run initial backup
echo "Running initial backup..."
python3 scripts/auto_backup.py --once

# 5. Start scheduler in background
echo "Starting backup scheduler (every 12 hours)..."
python3 scripts/auto_backup.py --schedule 720 

# 6. Save PID for later cleanup
echo $! > .backup_scheduler.pid

echo "✅ Setup complete! Backups scheduled every 12 hours"
echo "Monitor with: tail -f auto_backup.log"
```

Save as `setup_backups.sh` and run:
```bash
chmod +x setup_backups.sh
./setup_backups.sh
```

## Support & Monitoring

### Daily Monitoring Checklist

```bash
# 1. Check if backup process is running
ps aux | grep auto_backup

# 2. Check latest backup
ls -lh backups/ | tail -5

# 3. Check logs for errors
grep "❌" auto_backup.log | tail -10

# 4. Check available space
df -h /home/ubuntu/argilla_project
```

### Set Up Log Monitoring (Optional)

```bash
# Send daily summary to log
0 9 * * * tail -50 /home/ubuntu/argilla_project/auto_backup.log | mail -s "Argilla Backup Report" your_email@example.com
```

## Next Steps

1. ✅ Install dependencies
2. ✅ Configure `.env` with your credentials
3. ✅ Run first backup with `--once`
4. ✅ Schedule automatic backups
5. ✅ Monitor logs regularly
6. ✅ Test restore process (optional but recommended)

Good luck! Your Argilla data is now safe! 🚀
