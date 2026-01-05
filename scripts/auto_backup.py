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


class ArgillaBackupManager:
    """Manages automated backups of Argilla datasets"""
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        dataset_name: str,
        backup_dir: str = "./backups",
        max_backups: int = 5,
        workspace_name: str = "argilla"
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
            return [b for b in backups if b.is_dir()]
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
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
            return True
            
        except FileExistsError as e:
            logger.error(f"❌ Directory already exists: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
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
            return False
    
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
        default=os.getenv('ARGILLA_API_KEY'),
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
        workspace_name=args.workspace
    )
    
    # Execute requested action
    if args.list:
        backup_manager.list_backups()
    elif args.schedule:
        schedule_backups(backup_manager, args.schedule)
    else:
        # Default: run once
        success = backup_manager.run_backup_cycle()
        exit(0 if success else 1)


if __name__ == '__main__':
    main()
