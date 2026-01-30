#!/bin/bash
# Automated Argilla Backup Wrapper Script
# This script makes it easy to manage backups from the command line

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/auto_backup.py"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Show usage
show_help() {
    cat << EOF
${BLUE}Argilla Automated Backup Manager${NC}

Usage: $0 [COMMAND] [OPTIONS]

Commands:
  backup              Run backup once (default)
  schedule [MINS]     Schedule backups at regular intervals (requires APScheduler)
  list                List all existing backups
  help                Show this help message

Examples:
  $0 backup                           # Run backup once
  $0 schedule 120                     # Backup every 2 hours
  $0 schedule 1440                    # Backup every 24 hours
  $0 list                             # List all backups

Environment Variables:
  ARGILLA_API_URL                     Argilla API URL
  ARGILLA_API_KEY                     Argilla API key

For more info, see: $PROJECT_DIR/AUTO_BACKUP_SETUP.md

EOF
}

# Parse command
COMMAND="${1:-backup}"

case "$COMMAND" in
    backup)
        print_info "Running backup..."
        python "$BACKUP_SCRIPT" --once
        ;;
    schedule)
        INTERVAL="${2:-120}"
        if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]]; then
            print_error "Interval must be a number (minutes)"
            exit 1
        fi
        print_info "Scheduling backups every $INTERVAL minutes..."
        print_warning "Press Ctrl+C to stop"
        python "$BACKUP_SCRIPT" --schedule "$INTERVAL"
        ;;
    list)
        print_info "Listing backups..."
        python "$BACKUP_SCRIPT" --list
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
