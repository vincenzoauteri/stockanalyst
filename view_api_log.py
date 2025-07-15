#!/usr/bin/env python3

import sys
from fmp_client import FMPClient

def view_log(last_n=None):
    """View the FMP API request log"""
    
    client = FMPClient()
    log_entries = client.get_api_request_log()
    
    if not log_entries or log_entries == ["No API requests logged yet."]:
        print("No API requests logged yet.")
        return
    
    print(f"FMP API Request Log (showing {'all' if last_n is None else f'last {last_n}'} entries):")
    print("=" * 80)
    
    entries_to_show = log_entries if last_n is None else log_entries[-last_n:]
    
    for entry in entries_to_show:
        print(entry)
    
    print("=" * 80)
    print(f"Total entries in log: {len(log_entries)}")

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) > 1:
        try:
            last_n = int(sys.argv[1])
            view_log(last_n)
        except ValueError:
            print("Usage: python view_api_log.py [number_of_entries]")
            print("Example: python view_api_log.py 10")
            sys.exit(1)
    else:
        view_log()

if __name__ == "__main__":
    main()