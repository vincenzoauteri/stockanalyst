#!/usr/bin/env python3
"""
View Yahoo Finance API Request Log
Similar to view_api_log.py but for Yahoo Finance requests
"""

import sys
import os
from yahoo_finance_client import YahooFinanceClient

def main():
    # Get number of entries to display (default: all)
    num_entries = None
    if len(sys.argv) > 1:
        try:
            num_entries = int(sys.argv[1])
        except ValueError:
            print("Usage: python view_yahoo_api_log.py [number_of_entries]")
            sys.exit(1)
    
    # Create client and get log entries
    client = YahooFinanceClient()
    log_entries = client.get_api_request_log()
    
    if num_entries:
        log_entries = log_entries[-num_entries:]
    
    print(f"\n=== Yahoo Finance API Request Log ===")
    print(f"Showing {'last ' + str(num_entries) if num_entries else 'all'} entries\n")
    
    for entry in log_entries:
        print(entry)
    
    print(f"\nTotal entries displayed: {len(log_entries)}")

if __name__ == "__main__":
    main()