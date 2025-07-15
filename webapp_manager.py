#!/usr/bin/env python3
"""
Stock Analyst Webapp Manager
Modern process management utility using psutil for graceful start/stop/restart.
"""

import sys
import time
import argparse
import socket
from pathlib import Path
from process_manager import EnhancedProcessManager

# --- Configuration ---
WEBAPP_NAME = "stock_analyst_webapp"
PID_FILE = Path(f"/tmp/{WEBAPP_NAME}.pid")
STATUS_FILE = Path(f"/tmp/{WEBAPP_NAME}_status.json")
APP_COMMAND = [sys.executable, '/app/app.py']
APP_PORT = 5000

# --- Service Initialization ---
webapp_service = EnhancedProcessManager(
    name=WEBAPP_NAME,
    pid_file=PID_FILE,
    status_file=STATUS_FILE,
    command=APP_COMMAND,
    working_dir='/app'
)

def check_port_available(port: int) -> bool:
    """Check if a local port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def start_webapp():
    """Start the webapp."""
    if not check_port_available(APP_PORT):
        # Check if the process is running, if so, maybe the port check is a false positive
        if not webapp_service.is_running():
            print(f"Error: Port {APP_PORT} is in use by another application.")
            return False
        else:
            print(f"Webapp seems to be running, but port {APP_PORT} is occupied. "
                  f"Consider stopping the existing process.")

    print("Starting Stock Analyst Web Application...")
    success = webapp_service.start()
    if success:
        time.sleep(2)  # Give the app a moment to initialize
        if webapp_service.is_running():
            print(f"Webapp started successfully (PID: {webapp_service.get_pid()}).")
            print(f"Access at: http://localhost:{APP_PORT}")
        else:
            print("Failed to start webapp - process died unexpectedly.")
            # Attempt to clean up if the process died
            webapp_service._cleanup()
            success = False
    return success

def stop_webapp():
    """Stop the webapp."""
    success = webapp_service.stop()
    if success:
        print("Webapp stopped successfully.")
    else:
        print("Failed to stop webapp.")
    # Ensure cleanup is called regardless of stop() success,
    # as there might be stale files.
    webapp_service._cleanup()
    return success

def restart_webapp():
    """Restart the webapp."""
    return webapp_service.restart()

def status():
    """Show webapp status."""
    status_info = webapp_service.get_status()
    if status_info.get('running'):
        print("Webapp Status: RUNNING")
        print(f"  PID: {status_info.get('pid')}")
        print(f"  Access: http://localhost:{APP_PORT}")
        if 'timestamp' in status_info:
            start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status_info['timestamp']))
            print(f"  Started: {start_time_str}")
    else:
        print("Webapp Status: STOPPED")

def main():
    parser = argparse.ArgumentParser(
        description="Stock Analyst Webapp Manager - Modern Process Management",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status'],
                        help="""
start   - Start the webapp
stop    - Stop the webapp gracefully
restart - Restart the webapp
status  - Show current status
""")
    
    args = parser.parse_args()
    
    try:
        if args.command == 'start':
            success = start_webapp()
        elif args.command == 'stop':
            success = stop_webapp()
        elif args.command == 'restart':
            success = restart_webapp()
        elif args.command == 'status':
            status()
            success = True
        
        sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
