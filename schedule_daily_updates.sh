#!/bin/bash
# Daily Update Scheduler for Stock Analyst
# Run this script via cron for autonomous daily updates

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/daily_updates.log"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SCHEDULER: $1" | tee -a "$LOG_FILE"
}

# Function to check if scheduler is running
check_scheduler() {
    cd "$SCRIPT_DIR"
    if python scheduler.py status > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start scheduler if not running
ensure_scheduler_running() {
    if ! check_scheduler; then
        log "Scheduler not running. Starting..."
        cd "$SCRIPT_DIR"
        python scheduler.py start
        sleep 5  # Wait for scheduler to be ready
        
        if check_scheduler; then
            log "Scheduler started successfully"
        else
            log "ERROR: Failed to start scheduler"
            exit 1
        fi
    else
        log "Scheduler is running"
    fi
}

# Function to run daily update
run_daily_update() {
    log "Starting daily database update..."
    
    # Run the daily updater directly
    cd "$SCRIPT_DIR"
    if python daily_updater.py; then
        log "Daily update completed successfully"
        return 0
    else
        log "ERROR: Daily update failed"
        return 1
    fi
}

# Function to cleanup old logs (keep last 30 days)
cleanup_logs() {
    if [ -f "$LOG_FILE" ]; then
        # Keep only the last 1000 lines to prevent log file from growing too large
        tail -1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
}

# Main execution
main() {
    log "=== Daily Update Scheduler Started ==="
    
    # Check if Python is available
    if ! command -v python &> /dev/null; then
        log "ERROR: Python not found. Please install Python."
        exit 1
    fi
    
    # Ensure scheduler is running
    ensure_scheduler_running
    
    # Run daily update
    if run_daily_update; then
        log "Daily update process completed successfully"
        exit_code=0
    else
        log "Daily update process failed"
        exit_code=1
    fi
    
    # Cleanup old logs
    cleanup_logs
    
    log "=== Daily Update Scheduler Finished ==="
    exit $exit_code
}

# Run main function
main "$@"