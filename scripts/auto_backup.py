#!/usr/bin/env python3
"""
Automated Argilla Dataset Backup Script

This script automatically backs up your Argilla dataset to disk at regular intervals.
It's designed to run on HuggingFace Spaces where datasets can be lost during hibernation.

Features:
- Periodic backups (configurable interval)
- Backup rotation (keeps last N backups)
- Comprehensive logging
- Error handling and recovery
- Chinese character support (ensure_ascii=False)
"""

import os
import json
import logging
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import time
import requests
import hashlib

import argilla as rg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Sends notifications to Discord webhook"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Discord notifier
        
        Args:
            webhook_url: Discord webhook URL (or set DISCORD_WEBHOOK_URL env var)
        """
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)
    
    def send_error(self, title: str, message: str, error_details: str = None) -> bool:
        """
        Send error notification to Discord
        
        Args:
            title: Error title
            message: Error message
            error_details: Detailed error information
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            embed = {
                "title": f"[ERROR] {title}",
                "description": message,
                "color": 15158332,
                "fields": [
                    {
                        "name": "Timestamp",
                        "value": datetime.now().isoformat(),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Argilla Backup Manager"
                }
            }
            
            if error_details:
                embed["fields"].append({
                    "name": "Details",
                    "value": f"```{error_details[:1000]}```",
                    "inline": False
                })
            
            payload = {"embeds": [embed]}
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code in (200, 204)
            
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    def send_success(self, title: str, message: str) -> bool:
        """
        Send success notification to Discord
        
        Args:
            title: Success title
            message: Success message
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            embed = {
                "title": f"[SUCCESS] {title}",
                "description": message,
                "color": 3066993,
                "fields": [
                    {
                        "name": "Timestamp",
                        "value": datetime.now().isoformat(),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Argilla Backup Manager"
                }
            }
            
            payload = {"embeds": [embed]}
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code in (200, 204)
            
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False


class ArgillaBackupManager:
    """Manages automated backups of Argilla datasets"""
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        dataset_name: str,
        backup_dir: str = "./backups",
        max_backups: int = 5,
        workspace_name: str = "argilla",
        discord_webhook: Optional[str] = None
    ):
        """
        Initialize the backup manager
        
        Args:
            api_url: Argilla API URL
            api_key: Argilla API key
            dataset_name: Name of dataset to backup
            backup_dir: Directory to store backups
            max_backups: Maximum number of backups to keep
            workspace_name: Workspace name (default: "argilla")
            discord_webhook: Discord webhook URL for notifications
        """
        self.api_url = api_url
        self.api_key = api_key
        self.dataset_name = dataset_name
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.workspace_name = workspace_name
        
        # Initialize client
        self.client = None
        self.dataset = None
        
        # Initialize Discord notifier
        self.notifier = DiscordNotifier(discord_webhook)
        
    def connect(self) -> bool:
        """Connect to Argilla and load dataset"""
        try:
            logger.info(f"Connecting to Argilla at {self.api_url}")
            self.client = rg.Argilla(
                api_url=self.api_url,
                api_key=self.api_key,
            )
            
            # Get workspace
            workspace = self.client.workspaces(self.workspace_name)
            if not workspace:
                logger.error(f"Workspace '{self.workspace_name}' not found")
                return False
            
            # Get dataset
            self.dataset = self.client.datasets(name=self.dataset_name, workspace=workspace)
            if not self.dataset:
                logger.error(f"Dataset '{self.dataset_name}' not found")
                return False
            
            logger.info(f"✅ Connected successfully to dataset '{self.dataset_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            self.notifier.send_error(
                "Connection Failed",
                f"Failed to connect to Argilla at {self.api_url}",
                str(e)
            )
            return False
    
    def create_backup_dir(self) -> bool:
        """Create backup directory if it doesn't exist"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Backup directory ready: {self.backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
            return False
    
    def get_backup_path(self) -> Path:
        """Generate timestamped backup path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.dataset_name}_{timestamp}"
        return self.backup_dir / backup_name
    
    def get_existing_backups(self) -> List[Path]:
        """Get list of existing backups sorted by date (newest first)"""
        try:
            backups = sorted(
                self.backup_dir.iterdir(),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            # Exclude 'latest' symlink from backup list
            return [b for b in backups if b.is_dir() and b.name != 'latest']
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def calculate_backup_hash(self, backup_path: Path) -> Optional[str]:
        """Calculate hash of records data (excluding timestamps) to detect changes"""
        try:
            records_json = backup_path / "records.json"
            if not records_json.exists():
                return None
            
            with open(records_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract only the actual record data, excluding timestamps
            records_content = []
            
            if isinstance(data, list):
                for record in data:
                    # Create a filtered version without timestamp fields
                    filtered_record = {
                        'id': record.get('id'),
                        'fields': record.get('fields'),
                        'status': record.get('status')
                    }
                    
                    # Process responses - keep only the actual response values, not timestamps
                    responses = record.get('responses', [])
                    if responses:
                        filtered_responses = []
                        for resp in responses:
                            if isinstance(resp, dict):
                                # Extract only the answer value, not metadata
                                filtered_resp = {
                                    'value': resp.get('value'),
                                    'status': resp.get('status')
                                }
                                filtered_responses.append(filtered_resp)
                            else:
                                filtered_responses.append(resp)
                        filtered_record['responses'] = filtered_responses
                    
                    # Process suggestions similarly
                    suggestions = record.get('suggestions', [])
                    if suggestions:
                        filtered_suggestions = []
                        for sug in suggestions:
                            if isinstance(sug, dict):
                                filtered_sug = {
                                    'value': sug.get('value'),
                                    'type': sug.get('type')
                                }
                                filtered_suggestions.append(filtered_sug)
                            else:
                                filtered_suggestions.append(sug)
                        filtered_record['suggestions'] = filtered_suggestions
                    
                    records_content.append(filtered_record)
            
            # Convert to JSON string with sorted keys for consistent hashing
            content_str = json.dumps(records_content, sort_keys=True, ensure_ascii=False)
            file_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
            
            return file_hash
            
        except Exception as e:
            logger.error(f"Failed to calculate hash: {e}")
            return None
    
    def has_backup_changed(self, new_backup_path: Path) -> bool:
        """Check if backup content differs from the latest existing backup
        
        NOTE: This method is deprecated. Use direct hash comparison in backup_dataset() instead.
        This method has a bug where it compares the new backup with itself if called after creation.
        """
        try:
            existing_backups = self.get_existing_backups()
            if not existing_backups:
                logger.info("No existing backup found, will create new backup")
                return True
            
            # Skip the most recent backup if it has the same timestamp as new backup
            # to avoid comparing new backup with itself
            latest_backup = None
            for backup in existing_backups:
                # Compare by directory name to avoid using the newly created backup
                if backup.name != new_backup_path.name:
                    latest_backup = backup
                    break
            
            if latest_backup is None:
                logger.info("No previous backup found to compare with")
                return True
            
            # Calculate hashes
            new_hash = self.calculate_backup_hash(new_backup_path)
            old_hash = self.calculate_backup_hash(latest_backup)
            
            if new_hash is None or old_hash is None:
                logger.warning("Could not calculate hash, assuming content changed")
                return True
            
            if new_hash == old_hash:
                logger.info(f"Backup content unchanged (hash: {new_hash[:16]}...)")
                return False
            else:
                logger.info(f"Backup content changed (old: {old_hash[:16]}..., new: {new_hash[:16]}...)")
                return True
                
        except Exception as e:
            logger.error(f"Error checking backup changes: {e}")
            return True  # Assume changed on error
    
    def fix_json_encoding(self, file_path: Path) -> bool:
        """Convert JSON file to UTF-8 encoding (fix Chinese characters from Unicode escapes)"""
        try:
            # Read with Unicode escapes
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Write back with ensure_ascii=False to use proper UTF-8
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Fixed JSON encoding (Chinese characters): {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fix JSON encoding: {e}")
            return False
    
    def backup_dataset(self) -> bool:
        """Create backup of the dataset"""
        if not self.dataset:
            logger.error("Dataset not loaded. Call connect() first")
            return False
        
        # IMPORTANT: Get the hash of the latest existing backup BEFORE creating new backup
        # This avoids the bug where we compare new backup with itself
        existing_backups = self.get_existing_backups()
        old_hash = None
        if existing_backups:
            old_hash = self.calculate_backup_hash(existing_backups[0])
            logger.info(f"Latest existing backup hash: {old_hash[:16] if old_hash else 'None'}...")
        
        backup_path = self.get_backup_path()
        
        try:
            logger.info(f"Starting backup to {backup_path}")
            
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Get dataset info before backup
            progress = self.dataset.progress(with_users_distribution=True)
            total_records = progress.get('total', 0)
            completed = progress.get('completed', 0)
            pending = progress.get('pending', 0)
            
            logger.info(f"Dataset stats: {total_records} total, {completed} completed, {pending} pending")
            
            # Perform backup
            self.dataset.to_disk(path=str(backup_path), with_records=True)
            
            logger.info(f"✅ Backup completed successfully to {backup_path}")
            
            # Fix JSON encoding for Chinese characters (convert \uXXXX to proper UTF-8)
            records_json = backup_path / "records.json"
            if records_json.exists():
                logger.info("Converting Unicode escapes to UTF-8 for Chinese characters...")
                self.fix_json_encoding(records_json)
            
            # Also fix settings.json if it exists
            settings_json = backup_path / ".argilla" / "settings.json"
            if settings_json.exists():
                self.fix_json_encoding(settings_json)
            
            # Also fix dataset.json if it exists
            dataset_json = backup_path / ".argilla" / "dataset.json"
            if dataset_json.exists():
                self.fix_json_encoding(dataset_json)
            
            # Check if content has changed by comparing with the old hash we saved earlier
            new_hash = self.calculate_backup_hash(backup_path)
            content_changed = (old_hash is None or new_hash != old_hash)
            
            if content_changed:
                logger.info(f"Backup content changed (old: {old_hash[:16] if old_hash else 'None'}..., new: {new_hash[:16]}...)")
            else:
                logger.info(f"Backup content unchanged (hash: {new_hash[:16]}...)")
            
            if not content_changed:
                logger.info("⏭️  No changes detected, removing backup")
                shutil.rmtree(backup_path)
                # Ensure latest backup exists in Git even if no changes
                self._ensure_latest_backup_exists()
                
                return True  # Still considered successful
            
            # Create metadata file
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'dataset_name': self.dataset_name,
                'total_records': total_records,
                'completed': completed,
                'pending': pending,
                'records_exported': total_records,  # Note: discarded responses are NOT included
                'note': 'Discarded responses are not exported (Argilla design limitation)'
            }
            
            metadata_path = backup_path / "backup_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Metadata saved to {metadata_path}")
            
            # Update latest backup copy for Git tracking
            self._update_latest_backup_copy()
            
            # Auto commit to Git if enabled
            self._auto_commit_to_git()
            
            return True
            
        except FileExistsError as e:
            logger.error(f"❌ Directory already exists: {e}")
            self.notifier.send_error(
                "Backup Directory Error",
                f"Directory already exists: {backup_path}",
                str(e)
            )
            return False
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            self.notifier.send_error(
                "Backup Failed",
                f"Failed to backup dataset: {self.dataset_name}",
                str(e)
            )
            # Clean up partial backup
            if backup_path.exists():
                shutil.rmtree(backup_path)
            return False
    
    def rotate_backups(self) -> bool:
        """Delete old backups, keeping only the most recent ones"""
        try:
            backups = self.get_existing_backups()
            
            if len(backups) <= self.max_backups:
                logger.info(f"Backup rotation: {len(backups)} backups (max: {self.max_backups})")
                return True
            
            # Remove oldest backups
            to_remove = backups[self.max_backups:]
            
            for backup in to_remove:
                logger.warning(f"Removing old backup: {backup}")
                shutil.rmtree(backup)
            
            logger.info(f"✅ Rotation complete: keeping {self.max_backups} most recent backups")
            return True
            
        except Exception as e:
            logger.error(f"Backup rotation failed: {e}")
            self.notifier.send_error(
                "Rotation Failed",
                "Failed to rotate old backups",
                str(e)
            )
            return False
    
    def _update_latest_backup_copy(self) -> None:
        """Copy latest backup to 'latest' directory for Git tracking"""
        try:
            backups = self.get_existing_backups()
            if not backups:
                return
            
            latest_backup = backups[0]
            latest_dir = self.backup_dir / "latest"
            
            # Remove existing latest directory if it exists
            if latest_dir.exists():
                shutil.rmtree(latest_dir)
            
            # Copy the latest backup to 'latest' directory
            shutil.copytree(latest_backup, latest_dir)
            logger.info(f"✅ Updated latest backup copy: latest/ <- {latest_backup.name}")
            
        except Exception as e:
            logger.warning(f"Failed to copy latest backup: {e}")
    
    def _ensure_latest_backup_exists(self) -> None:
        """Ensure latest backup directory exists for Git tracking"""
        try:
            latest_dir = self.backup_dir / "latest"
            
            # If latest already exists, nothing to do
            if latest_dir.exists():
                logger.info("Latest backup already exists, no update needed")
                return
            
            # Create latest from the most recent backup
            backups = self.get_existing_backups()
            if not backups:
                logger.info("No backups found to create latest")
                return
            
            latest_backup = backups[0]
            shutil.copytree(latest_backup, latest_dir)
            logger.info(f"✅ Created latest backup copy: latest/ <- {latest_backup.name}")
            
            # Commit to Git
            self._auto_commit_to_git()
            
        except Exception as e:
            logger.warning(f"Failed to ensure latest backup exists: {e}")
    
    def _auto_commit_to_git(self) -> None:
        """Auto commit and push changes to Git if in a Git repository"""
        try:
            import subprocess
            
            # Check if we're in a Git repository
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.backup_dir.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.info("Not in a Git repository, skipping auto-commit")
                return
            
            # Check if there are changes to commit
            result = subprocess.run(
                ['git', 'status', '--porcelain', 'backups/latest'],
                cwd=self.backup_dir.parent,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                logger.info("No Git changes detected, skipping commit")
                return
            
            # Add the latest backup directory
            subprocess.run(
                ['git', 'add', 'backups/latest'],
                cwd=self.backup_dir.parent,
                check=True
            )
            
            # Commit with timestamp
            commit_msg = f"Backup updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=self.backup_dir.parent,
                check=True
            )
            
            # Push to remote
            subprocess.run(
                ['git', 'push'],
                cwd=self.backup_dir.parent,
                check=True
            )
            
            logger.info(f"✅ Auto-committed and pushed to Git: {commit_msg}")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git operation failed: {e}")
        except Exception as e:
            logger.warning(f"Failed to auto-commit to Git: {e}")
    
    def run_backup_cycle(self) -> bool:
        """Run complete backup cycle: connect, backup, rotate"""
        logger.info("=" * 70)
        logger.info("STARTING BACKUP CYCLE")
        logger.info("=" * 70)
        
        # Step 1: Connect
        if not self.connect():
            return False
        
        # Step 2: Create backup directory
        if not self.create_backup_dir():
            return False
        
        # Step 3: Backup dataset
        if not self.backup_dataset():
            return False
        
        # Step 4: Rotate old backups
        if not self.rotate_backups():
            return False
        
        logger.info("=" * 70)
        logger.info("✅ BACKUP CYCLE COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        
        # Send success notification
        progress = self.dataset.progress(with_users_distribution=True)
        total = progress.get('total', 0)
        self.notifier.send_success(
            "Backup Completed",
            f"Successfully backed up {total} records from {self.dataset_name}"
        )
        
        return True
    
    def list_backups(self) -> None:
        """List all existing backups"""
        backups = self.get_existing_backups()
        
        if not backups:
            logger.info("No backups found")
            return
        
        logger.info(f"Found {len(backups)} backups:")
        for i, backup in enumerate(backups, 1):
            # Try to read metadata
            metadata_path = backup / "backup_metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    size = sum(f.stat().st_size for f in backup.rglob('*') if f.is_file())
                    size_mb = size / (1024 * 1024)
                    logger.info(
                        f"{i}. {backup.name}\n"
                        f"   Timestamp: {metadata.get('timestamp')}\n"
                        f"   Records: {metadata.get('total_records')}\n"
                        f"   Size: {size_mb:.2f} MB"
                    )
                except Exception as e:
                    logger.error(f"Failed to read metadata: {e}")
            else:
                logger.info(f"{i}. {backup.name}")


def schedule_backups(backup_manager: ArgillaBackupManager, interval_minutes: int = 60) -> None:
    """
    Schedule backups at regular intervals using APScheduler
    
    Args:
        backup_manager: ArgillaBackupManager instance
        interval_minutes: Interval between backups in minutes
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            backup_manager.run_backup_cycle,
            'interval',
            minutes=interval_minutes,
            id='argilla_backup'
        )
        scheduler.start()
        
        logger.info(f"✅ Scheduler started: Backup every {interval_minutes} minutes")
        
        # Keep scheduler running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down scheduler...")
            scheduler.shutdown()
            
    except ImportError:
        logger.error("APScheduler not installed. Install it with: pip install apscheduler")


def main():
    parser = argparse.ArgumentParser(
        description='Automated Argilla Dataset Backup Manager'
    )
    parser.add_argument(
        '--api-url',
        default=os.getenv('ARGILLA_API_URL', 'https://bubble030-test-argilla.hf.space'),
        help='Argilla API URL'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('ARGILLA_API_KEY', '0KQy1XjHdNK35xRz4Tk6AQZ8lrw1TB8EEo8VCubfSa4JQnWhn50jBSwE44gTCvWSv7QBdYzRDaNcEzpPuoSjQ4Erf47sMk31b5GnT1DkqvM'),
        help='Argilla API key (or set ARGILLA_API_KEY env var)'
    )
    parser.add_argument(
        '--dataset',
        default='模型回答偏好選擇_整合',
        help='Dataset name to backup'
    )
    parser.add_argument(
        '--backup-dir',
        default='./backups',
        help='Directory to store backups'
    )
    parser.add_argument(
        '--max-backups',
        type=int,
        default=5,
        help='Maximum number of backups to keep'
    )
    parser.add_argument(
        '--workspace',
        default='argilla',
        help='Workspace name'
    )
    parser.add_argument(
        '--schedule',
        type=int,
        help='Schedule backups at regular intervals (minutes). Requires APScheduler'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run backup once and exit'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all existing backups'
    )
    parser.add_argument(
        '--discord-webhook',
        default=os.getenv('DISCORD_WEBHOOK_URL'),
        help='Discord webhook URL for error notifications (or set DISCORD_WEBHOOK_URL env var)'
    )
    parser.add_argument(
        '--test-webhook',
        action='store_true',
        help='Test Discord webhook connection without running backup'
    )
    
    args = parser.parse_args()
    
    if not args.api_key:
        parser.error('API key required. Set ARGILLA_API_KEY env var or use --api-key')
    
    # Initialize backup manager
    backup_manager = ArgillaBackupManager(
        api_url=args.api_url,
        api_key=args.api_key,
        dataset_name=args.dataset,
        backup_dir=args.backup_dir,
        max_backups=args.max_backups,
        workspace_name=args.workspace,
        discord_webhook=args.discord_webhook
    )
    
    # Execute requested action
    if args.test_webhook:
        # Test Discord webhook
        notifier = DiscordNotifier(args.discord_webhook)
        if not notifier.enabled:
            logger.error("Discord webhook not configured. Use --discord-webhook or set DISCORD_WEBHOOK_URL env var")
            exit(1)
        
        logger.info("Testing Discord webhook connection...")
        success = notifier.send_error(
            "Test Connection",
            "This is a test notification from Argilla Backup Manager",
            "If you see this message, your webhook is correctly configured!"
        )
        
        if success:
            logger.info("✅ Discord webhook test successful!")
            exit(0)
        else:
            logger.error("❌ Failed to send test notification")
            exit(1)
    elif args.list:
        backup_manager.list_backups()
    elif args.schedule:
        schedule_backups(backup_manager, args.schedule)
    else:
        # Default: run once
        success = backup_manager.run_backup_cycle()
        exit(0 if success else 1)


if __name__ == '__main__':
    main()
