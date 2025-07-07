#!/usr/bin/env python3
"""
Consolidated Scheduler for Stock Analyst Application
Manages daily updates, catchup operations, health checks, and provides a CLI.
"""

import argparse
import logging
import os
import signal
import sys
import threading
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import schedule
from sqlalchemy import text
from process_manager import EnhancedProcessManager

# --- Local Imports ---
try:
    from daily_updater import DailyUpdater
    from data_access_layer import StockDataService
    from fmp_client import FMPClient
    from yahoo_finance_client import YahooFinanceClient
    from gap_detector import GapDetector
    from logging_config import setup_logging
except ImportError as e:
    print(f"Error: Failed to import local modules. Details: {e}")
    sys.exit(1)

# --- Global Configuration ---
SCHEDULER_NAME = "stock_analyst_scheduler"
PID_FILE = Path(f"/tmp/{SCHEDULER_NAME}.pid")
STATUS_FILE = Path(f"/tmp/{SCHEDULER_NAME}_status.json")
LOG_FILE = Path('logs/scheduler.log')
SCHEDULER_COMMAND = [sys.executable, __file__, 'run-internal']

# Setup logging
logger = logging.getLogger(__name__)

class Scheduler:
    """
    A unified scheduler that handles all background data processing tasks.
    """

    def __init__(self):
        try:
            from database import DatabaseManager
            self.dal = StockDataService()
            self.db_manager = DatabaseManager()
            self.daily_updater = DailyUpdater()
            self.gap_detector = GapDetector()
            self.fmp_client = FMPClient()
            self.yahoo_client = YahooFinanceClient()
            self.status = {
                "running": False,
                "pid": os.getpid(),
                "last_successful_update": None,
                "next_scheduled_run": None,
                "consecutive_failures": 0,
            }
            self._running = True
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}", exc_info=True)
            raise

    def run_forever(self):
        """Runs the scheduler's main loop until stop() is called."""
        logger.info("Starting the Stock Analyst Scheduler main loop...")
        self.status["running"] = True
        self._save_status()

        # Schedule future jobs
        schedule.every().day.at("04:00").do(self.run_daily_update)
        schedule.every(4).hours.do(self.run_health_check)
        schedule.every(1).hour.do(self.run_catchup_operation)

        # Run initial catchup if gaps are detected
        logger.info("Checking for gaps at startup...")
        gaps = self.gap_detector.detect_all_gaps()
        if any(gaps.values()):
            total_gaps = sum(len(gap_list) for gap_list in gaps.values())
            logger.info(f"Found {total_gaps} gaps at startup. Running initial aggressive catchup...")
            self.run_catchup_operation()
        else:
            logger.info("No gaps detected at startup.")

        try:
            while self._running:
                schedule.run_pending()
                next_run_time = schedule.next_run()
                if next_run_time:
                    self.status["next_scheduled_run"] = next_run_time.isoformat()
                else:
                    self.status["next_scheduled_run"] = None
                self._save_status()
                time.sleep(15)
        except Exception as e:
            logger.error(f"An unhandled exception occurred in the scheduler loop: {e}", exc_info=True)
        finally:
            logger.info("Scheduler loop has been stopped.")
            self.status['running'] = False
            self._save_status()

    def stop(self):
        """Stops the scheduler gracefully."""
        logger.info("Requesting scheduler to stop...")
        self._running = False

    def run_daily_update(self):
        logger.info("Starting scheduled full daily update...")
        try:
            success = self.daily_updater.run_daily_update()
            if success:
                self.status["last_successful_update"] = datetime.now().isoformat()
                self.status["consecutive_failures"] = 0
                logger.info("Full daily update completed successfully.")
            else:
                self.status["consecutive_failures"] += 1
                logger.warning("Full daily update completed with failures.")
        except Exception as e:
            self.status["consecutive_failures"] += 1
            logger.error(f"An exception occurred during the daily update: {e}", exc_info=True)
        finally:
            self._save_status()

    def run_health_check(self):
        logger.info("Running periodic health check...")
        try:
            gaps_summary = self.gap_detector.detect_all_gaps()
            total_gaps = sum(len(gaps) for gaps in gaps_summary.values())
            if total_gaps > 0:
                logger.warning(f"Health Check: Found {total_gaps} data gaps.")
            else:
                logger.info("Health Check: No data gaps found.")
        except Exception as e:
            logger.error(f"An exception occurred during the health check: {e}", exc_info=True)
        finally:
            self._save_status()

    def run_catchup_operation(self):
        logger.info(f"Starting aggressive catch-up operation...")
        try:
            # Check if we're in a rate limit pause
            current_time = datetime.now()
            if hasattr(self, 'rate_limit_pause_until') and current_time < self.rate_limit_pause_until:
                remaining_minutes = (self.rate_limit_pause_until - current_time).total_seconds() / 60
                logger.info(f"Rate limit pause active. Resuming in {remaining_minutes:.1f} minutes.")
                return
            
            gaps = self.gap_detector.detect_all_gaps()
            retry_gaps = self._get_retry_gaps()
            
            # Get already processed gaps to avoid re-processing
            already_processed = self._get_already_processed_gaps()
            
            if not any(gaps.values()) and not retry_gaps:
                logger.info("No data gaps found. Catch-up not needed.")
                return
            
            # Get all symbols with gaps, prioritize by gap type, excluding already processed ones
            priority_symbols = []
            for gap_type, gap_list in gaps.items():
                for gap in gap_list:
                    if hasattr(gap, 'symbol'):
                        gap_key = (gap.symbol, gap_type)
                        # Skip if already processed and not ready for retry
                        if gap_key not in already_processed:
                            priority_symbols.append((gap.symbol, gap_type))
            
            # Add retry gaps to the front of the list (higher priority)
            priority_symbols = retry_gaps + priority_symbols
            logger.info(f"Including {len(retry_gaps)} retry gaps for data unavailable items")
            
            if not priority_symbols:
                logger.info("No symbols with gaps found.")
                return
            
            logger.info(f"Starting aggressive gap filling for {len(priority_symbols)} symbol-gaps")
            
            # Initialize Yahoo Finance client directly for faster responses
            from yahoo_finance_client import YahooFinanceClient
            yahoo_client = YahooFinanceClient()
            
            filled_count = 0
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            for symbol, gap_type in priority_symbols:
                if consecutive_errors >= max_consecutive_errors:
                    logger.warning(f"Hit {max_consecutive_errors} consecutive errors. Pausing for 1 hour.")
                    self.rate_limit_pause_until = datetime.now() + timedelta(hours=1)
                    break
                
                try:
                    logger.info(f"Filling {gap_type} gap for {symbol}")
                    success = False
                    
                    if gap_type == 'corporate_actions':
                        data = yahoo_client.get_corporate_actions(symbol)
                        if data and 'dividends' in data:
                            self.db_manager.insert_corporate_actions(symbol, data['dividends'], data.get('splits', []))
                            success = True
                    
                    elif gap_type in ['financial_statements', 'income_statements', 'balance_sheets', 'cash_flow_statements']:
                        statements = yahoo_client.get_financial_statements(symbol)
                        if statements:
                            if 'income_statement' in statements:
                                self.db_manager.insert_income_statements(symbol, statements['income_statement'])
                            if 'balance_sheet' in statements:
                                self.db_manager.insert_balance_sheets(symbol, statements['balance_sheet'])
                            if 'cash_flow' in statements:
                                self.db_manager.insert_cash_flow_statements(symbol, statements['cash_flow'])
                            success = True
                    
                    elif gap_type == 'analyst_recommendations':
                        recommendations = yahoo_client.get_analyst_recommendations(symbol)
                        if recommendations and 'recommendations' in recommendations:
                            self.db_manager.insert_analyst_recommendations(symbol, recommendations['recommendations'])
                            success = True
                    
                    elif gap_type == 'historical_prices':
                        prices = yahoo_client.get_historical_prices(symbol)
                        if prices and not prices.empty:
                            self.db_manager.insert_historical_prices(symbol, prices)
                            success = True
                    
                    elif gap_type == 'profile_data':
                        profile = yahoo_client.get_company_profile(symbol)
                        if profile:
                            self.db_manager.insert_company_profile(profile)
                            success = True
                    
                    if success:
                        filled_count += 1
                        consecutive_errors = 0  # Reset error counter on success
                        logger.info(f"Successfully filled {gap_type} for {symbol} ({filled_count} total)")
                    else:
                        # No data received - treat as data unavailability, not an error
                        logger.info(f"Data unavailable for {gap_type} - {symbol}")
                        self._mark_gap_unavailable(symbol, gap_type, "No data available from API")
                        filled_count += 1  # Count as filled so we move on
                        consecutive_errors = 0  # Don't count toward consecutive limit
                
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'too many requests' in error_msg or 'rate limit' in error_msg or 'service unavailable' in error_msg or '429' in error_msg or '503' in error_msg:
                        consecutive_errors += 1
                        logger.warning(f"Rate limit/service error for {symbol}: {e} (consecutive errors: {consecutive_errors})")
                        self._record_gap_attempt(symbol, gap_type, 'rate_limit', str(e))
                    elif 'no data' in error_msg or 'not found' in error_msg or 'data not available' in error_msg or '404' in error_msg:
                        # Data unavailability errors - mark gap as filled with unavailable status
                        logger.info(f"Data unavailable for {symbol} {gap_type}: {e}")
                        self._mark_gap_unavailable(symbol, gap_type, str(e))
                        filled_count += 1  # Count as filled so we move on
                        consecutive_errors = 0  # Don't count toward consecutive limit
                    else:
                        # Other errors don't count toward consecutive limit
                        logger.error(f"Error filling gap for {symbol}: {e}")
                        self._record_gap_attempt(symbol, gap_type, 'other_error', str(e))
                
                # Wait 1 second between calls for aggressive but controlled rate
                time.sleep(1)
            
            logger.info(f"Catch-up operation completed. Filled {filled_count} gaps.")
            
            # If we paused due to rate limits, log when we'll resume
            if hasattr(self, 'rate_limit_pause_until'):
                logger.info(f"Next catchup will resume at {self.rate_limit_pause_until}")

        except Exception as e:
            logger.error(f"An exception occurred during the catch-up operation: {e}", exc_info=True)
        finally:
            self._save_status()

    def _record_gap_attempt(self, symbol: str, gap_type: str, error_type: str, error_msg: str):
        """Record a gap filling attempt with error details"""
        try:
            with self.db_manager.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO data_gaps (symbol, gap_type, start_date, end_date, gap_days, priority, status, last_attempt, error_count, error_type)
                    VALUES (:symbol, :gap_type, CURRENT_DATE, CURRENT_DATE, 1, 'medium', 'pending', CURRENT_TIMESTAMP, 1, :error_type)
                    ON CONFLICT (symbol, gap_type, start_date, end_date) DO UPDATE SET
                    last_attempt = CURRENT_TIMESTAMP,
                    error_count = data_gaps.error_count + 1,
                    error_type = :error_type,
                    updated_at = CURRENT_TIMESTAMP
                """), {
                    'symbol': symbol,
                    'gap_type': gap_type, 
                    'error_type': error_type
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording gap attempt for {symbol}: {e}")

    def _mark_gap_unavailable(self, symbol: str, gap_type: str, error_msg: str):
        """Mark a gap as filled but with data unavailable status, set retry for 1 day"""
        try:
            from datetime import timedelta
            next_retry = datetime.now() + timedelta(days=1)
            
            with self.db_manager.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO data_gaps (symbol, gap_type, start_date, end_date, gap_days, priority, status, last_attempt, next_retry, error_count, error_type)
                    VALUES (:symbol, :gap_type, CURRENT_DATE, CURRENT_DATE, 1, 'medium', 'data_unavailable', CURRENT_TIMESTAMP, :next_retry, 1, 'data_unavailable')
                    ON CONFLICT (symbol, gap_type, start_date, end_date) DO UPDATE SET
                    status = 'data_unavailable',
                    last_attempt = CURRENT_TIMESTAMP,
                    next_retry = :next_retry,
                    error_count = data_gaps.error_count + 1,
                    error_type = 'data_unavailable',
                    updated_at = CURRENT_TIMESTAMP
                """), {
                    'symbol': symbol,
                    'gap_type': gap_type,
                    'next_retry': next_retry
                })
                conn.commit()
                logger.info(f"Gap marked as data unavailable for {symbol} {gap_type}, will retry at {next_retry}")
        except Exception as e:
            logger.error(f"Error marking gap as unavailable for {symbol}: {e}")

    def _get_retry_gaps(self):
        """Get gaps that are ready for retry (data_unavailable status with next_retry <= now)"""
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT symbol, gap_type FROM data_gaps 
                    WHERE status = 'data_unavailable' 
                    AND next_retry <= CURRENT_TIMESTAMP
                    ORDER BY priority DESC, next_retry ASC
                    LIMIT 50
                """))
                return [(row[0], row[1]) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting retry gaps: {e}")
            return []

    def _get_already_processed_gaps(self):
        """Get gaps that are already processed (data_unavailable status with future retry time)"""
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT symbol, gap_type FROM data_gaps 
                    WHERE status = 'data_unavailable' 
                    AND next_retry > CURRENT_TIMESTAMP
                """))
                return {(row[0], row[1]) for row in result.fetchall()}
        except Exception as e:
            logger.error(f"Error getting already processed gaps: {e}")
            return set()

    def _save_status(self):
        """Saves the current scheduler status to a file."""
        self.status['last_updated'] = datetime.now().isoformat()
        try:
            # Ensure the directory exists
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATUS_FILE, 'w') as f:
                json.dump(self.status, f, indent=4)
        except (IOError, TypeError) as e:
            logger.warning(f"Could not save scheduler status to {STATUS_FILE}: {e}")

# --- CLI and Service Management ---
service_manager = EnhancedProcessManager(
    name=SCHEDULER_NAME,
    pid_file=PID_FILE,
    status_file=STATUS_FILE,
    command=SCHEDULER_COMMAND,
    working_dir='/app'
)

def handle_start():
    """Starts the scheduler as a background process."""
    print("Starting scheduler as a background service...")
    success = service_manager.start()
    if success:
        # Wait longer for the process to initialize
        time.sleep(5)
        attempts = 0
        while attempts < 3:
            if service_manager.is_running():
                print(f"Scheduler started successfully (PID: {service_manager.get_pid()}).")
                return True
            time.sleep(2)
            attempts += 1
        
        print("Failed to start scheduler - process died unexpectedly.")
        # Check log files for errors
        stderr_log = Path('logs') / f"{SCHEDULER_NAME}_stderr.log"
        if stderr_log.exists() and stderr_log.stat().st_size > 0:
            print(f"Check error log: {stderr_log}")
        service_manager._cleanup()
        return False
    return success

def handle_stop():
    """Stops the running scheduler process."""
    print("Stopping scheduler...")
    success = service_manager.stop()
    if success:
        print("Scheduler stopped successfully.")
    else:
        print("Failed to stop scheduler.")
    # Ensure cleanup is called to remove any stale files
    service_manager._cleanup()
    return success

def handle_restart():
    """Restarts the scheduler."""
    print("Restarting scheduler...")
    return service_manager.restart()

def handle_status():
    """Displays the current status of the scheduler."""
    status_info = service_manager.get_status()
    if status_info.get('running'):
        print(f"Scheduler Status: RUNNING")
        print(f"  PID: {status_info.get('pid')}")
        if 'timestamp' in status_info:
            start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status_info['timestamp']))
            print(f"  Started: {start_time_str}")
        
        # Display details from the status file
        if 'last_updated' in status_info:
            print(f"  Last Updated: {status_info['last_updated']}")
        if 'next_scheduled_run' in status_info:
             print(f"  Next Run: {status_info['next_scheduled_run']}")
        if 'consecutive_failures' in status_info and status_info['consecutive_failures'] > 0:
             print(f"  Failures: {status_info['consecutive_failures']}")
    else:
        print("Scheduler Status: STOPPED")

def run_scheduler_process():
    """The actual scheduler process logic."""
    try:
        LOG_FILE.parent.mkdir(exist_ok=True)
        setup_logging(log_level="INFO", log_dir=LOG_FILE.parent, enable_console_logging=True)
        
        logger.info("Starting scheduler process...")
        scheduler = Scheduler()
        logger.info("Scheduler instance created successfully")
        
        def signal_handler(signum, frame):
            logger.info(f"Signal {signal.Signals(signum).name} received, stopping scheduler.")
            scheduler.stop()
            # No sys.exit here, allow the loop to terminate gracefully

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Starting scheduler main loop...")
        scheduler.run_forever()
        logger.info("Scheduler process exiting normally")
    except Exception as e:
        # Log the error and exit
        if 'logger' in locals():
            logger.error(f"Scheduler process failed: {e}", exc_info=True)
        else:
            print(f"Scheduler process failed during initialization: {e}")
        sys.exit(1)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Stock Analyst Scheduler: Manages background data processing.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 'run-internal'],
                        help="""
start       - Start the scheduler as a background service.
stop        - Stop the running scheduler service.
restart     - Restart the scheduler service.
status      - Show the current status of the scheduler.
run-internal- For internal use by the process manager.
""")
    
    args = parser.parse_args()

    if args.command == 'run-internal':
        run_scheduler_process()
    else:
        # Setup basic logging for CLI feedback
        setup_logging(log_level="INFO", enable_file_logging=False)
        
        success = False
        if args.command == 'start':
            success = handle_start()
        elif args.command == 'stop':
            success = handle_stop()
        elif args.command == 'restart':
            success = handle_restart()
        elif args.command == 'status':
            handle_status()
            success = True
        
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
