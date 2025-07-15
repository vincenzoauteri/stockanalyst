#!/usr/bin/env python3
"""
Daily Database Updater for Stock Analyst
Autonomous daily updates respecting FMP free tier limits (250 requests/day)
Refactored to use common DataFetcher module
"""

import sys
import logging
from datetime import datetime
from typing import List, Dict
from data_fetcher import DataFetcher
from data_access_layer import StockDataService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_updates.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DailyUpdater:
    """
    Daily updater that respects FMP free tier limits:
    - 250 requests/day total
    - 4 requests/second max
    """
    
    def __init__(self):
        self.data_fetcher = DataFetcher(daily_request_limit=250, rate_limit_delay=0.25)
        self.db_manager = self.data_fetcher.db_manager
        self.stock_data_service = StockDataService()
        
        # Data update priorities (most important first)
        self.update_priorities = [
            'sp500_constituents',  # 1 request - most critical
            'daily_prices',        # ~50-100 requests - essential for charts
            'company_profiles',    # ~50-100 requests - important for fundamentals
            'quarterly_updates'    # ~50-100 requests - less frequent but valuable
        ]
    
    @property
    def request_count(self):
        """Get current request count from data fetcher"""
        return self.data_fetcher.request_count
    
    def get_request_budget(self) -> Dict[str, int]:
        """
        Allocate daily request budget across different data types
        Total: 250 requests/day
        """
        return {
            'sp500_constituents': 1,     # Check for changes daily
            'daily_prices': 120,         # Priority: latest prices for top stocks
            'company_profiles': 80,      # Update profiles for missing/stale data
            'quarterly_updates': 40,     # Financial statements (lower priority)
            'buffer': 9                  # Keep some buffer for errors/retries
        }
    
    def check_api_availability(self) -> bool:
        """Check if API key is configured and working"""
        return self.data_fetcher.check_api_availability()
    
    def get_stale_data_priorities(self) -> Dict[str, List[str]]:
        """Get data update priorities using common data fetcher"""
        return self.data_fetcher.get_stale_data_priorities(max_symbols=100)
    
    def update_sp500_constituents(self, budget: int) -> int:
        """Update S&P 500 constituents list using common data fetcher"""
        return self.data_fetcher.update_sp500_constituents(budget)
    
    def update_daily_prices(self, budget: int, priorities: Dict[str, List[str]]) -> int:
        """Update daily prices for prioritized symbols using common data fetcher"""
        all_symbols = []
        # Process symbols by priority
        for priority_level in ['critical', 'high', 'medium', 'low']:
            all_symbols.extend(priorities[priority_level])
        
        return self.data_fetcher.update_historical_prices(all_symbols, budget, period='5D')
    
    def update_company_profiles(self, budget: int, priorities: Dict[str, List[str]]) -> int:
        """Update company profiles for missing symbols using common data fetcher"""
        # Get symbols missing profiles
        missing_profiles = self.data_fetcher.get_missing_profiles()
        
        # Combine with prioritized symbols
        all_symbols = missing_profiles + priorities.get('critical', [])
        
        # Remove duplicates while preserving order
        unique_symbols = list(dict.fromkeys(all_symbols))
        
        return self.data_fetcher.update_company_profiles(unique_symbols, budget)
    
    def update_quarterly_data(self, budget: int, priorities: Dict[str, List[str]]) -> int:
        """Update quarterly fundamental data using common data fetcher"""
        # Focus on symbols that need fundamental updates
        symbols_to_update = priorities.get('high', []) + priorities.get('medium', [])
        
        return self.data_fetcher.update_fundamentals_data(symbols_to_update[:20], budget)
    
    def run_daily_update(self) -> bool:
        """
        Run the complete daily update process
        Returns True if successful, False if failed
        """
        start_time = datetime.now()
        logger.info("=== Starting Daily Update Process ===")
        
        try:
            # Check API availability
            if not self.check_api_availability():
                logger.error("API not available. Aborting daily update.")
                return False
            
            # Get budget allocation
            budget = self.get_request_budget()
            logger.info(f"Daily budget allocation: {budget}")
            
            # Get data priorities
            priorities = self.get_stale_data_priorities()
            
            total_requests_used = 0
            
            # 1. Update S&P 500 constituents (highest priority)
            logger.info("Step 1: Updating S&P 500 constituents")
            requests_used = self.update_sp500_constituents(budget['sp500_constituents'])
            total_requests_used += requests_used
            logger.info(f"S&P 500 update used {requests_used} requests")
            
            # 2. Update daily prices (most important for charts)
            logger.info("Step 2: Updating daily prices")
            requests_used = self.update_daily_prices(budget['daily_prices'], priorities)
            total_requests_used += requests_used
            logger.info(f"Price updates used {requests_used} requests")
            
            # 3. Update company profiles (important for missing data)
            logger.info("Step 3: Updating company profiles")
            requests_used = self.update_company_profiles(budget['company_profiles'], priorities)
            total_requests_used += requests_used
            logger.info(f"Profile updates used {requests_used} requests")
            
            # 4. Update quarterly data (lower priority)
            logger.info("Step 4: Updating quarterly data")
            requests_used = self.update_quarterly_data(budget['quarterly_updates'], priorities)
            total_requests_used += requests_used
            logger.info(f"Quarterly updates used {requests_used} requests")
            
            # 5. Update Betas (local calculation, no API cost)
            logger.info("Step 5: Updating beta values for all stocks")
            self.update_all_betas()
            
            # Summary
            end_time = datetime.now()
            duration = end_time - start_time
            
            request_summary = self.data_fetcher.get_request_summary()
            
            logger.info("=== Daily Update Complete ===")
            logger.info(f"Duration: {duration}")
            logger.info(f"Requests used: {request_summary['requests_used']}/{request_summary['daily_limit']}")
            logger.info(f"Requests remaining: {request_summary['requests_remaining']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Daily update failed: {e}")
            return False

    def update_all_betas(self):
        """Calculate and update beta for all S&P 500 stocks."""
        logger.info("Starting beta calculation for all S&P 500 stocks.")
        symbols = self.db_manager.get_sp500_symbols()
        updated_count = 0
        failed_count = 0
        for symbol in symbols:
            try:
                beta = self.stock_data_service.calculate_beta(symbol)
                if beta is not None:
                    self.db_manager.update_beta(symbol, beta)
                    updated_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to calculate or update beta for {symbol}: {e}")
                failed_count += 1
        logger.info(f"Beta update complete. Updated: {updated_count}, Failed: {failed_count}")

    def get_update_status(self) -> Dict:
        """Get current update status and statistics"""
        try:
            # Get basic database stats
            symbols = self.db_manager.get_sp500_symbols()
            
            # Count missing data
            missing_profiles = len(self.data_fetcher.get_missing_profiles())
            
            # Get request summary
            request_summary = self.data_fetcher.get_request_summary()
            
            return {
                'total_symbols': len(symbols),
                'missing_profiles': missing_profiles,
                'request_summary': request_summary,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting update status: {e}")
            return {'error': str(e)}

def main():
    """Main entry point for daily updates"""
    updater = DailyUpdater()
    
    success = updater.run_daily_update()
    
    if success:
        logger.info("Daily update completed successfully")
        sys.exit(0)
    else:
        logger.error("Daily update failed")
        sys.exit(1)

if __name__ == "__main__":
    main()