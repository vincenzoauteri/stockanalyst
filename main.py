#!/usr/bin/env python3
# TEST SYNC: Container sync test comment added

import pandas as pd
import time
from fmp_client import FMPClient
from database import DatabaseManager
from unified_config import get_config
from sqlalchemy import text
from logging_config import setup_logging, get_logger

# Initialize centralized logging
setup_logging(
    log_level="INFO",
    enable_file_logging=True,
    enable_console_logging=True
)
logger = get_logger(__name__)

class StockAnalyst:
    def __init__(self):
        self.fmp_client = FMPClient()
        self.db_manager = DatabaseManager()
        self.config = get_config()
    
    def fetch_and_store_sp500_constituents(self):
        """Fetch S&P 500 constituents and store in database"""
        logger.info("Fetching S&P 500 constituents...")
        
        df = self.fmp_client.get_sp500_constituents()
        if df.empty:
            logger.error("Failed to fetch S&P 500 constituents")
            return False
        
        logger.info(f"Fetched {len(df)} S&P 500 constituents")
        
        # Clean and prepare data
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        
        # Store in database
        self.db_manager.insert_sp500_constituents(df)
        logger.info("S&P 500 constituents stored in database")
        
        return True
    
    def fetch_and_store_company_profiles(self, limit=None):
        """Fetch company profiles for S&P 500 constituents"""
        symbols = self.db_manager.get_sp500_symbols()
        
        if limit:
            symbols = symbols[:limit]
        
        logger.info(f"Fetching company profiles for {len(symbols)} symbols...")
        
        for i, symbol in enumerate(symbols, 1):
            if self.db_manager.symbol_exists_in_profiles(symbol):
                logger.info(f"Profile for {symbol} already exists, skipping...")
                continue
            
            logger.info(f"Fetching profile for {symbol} ({i}/{len(symbols)})")
            
            profile = self.fmp_client.get_company_profile(symbol)
            if profile:
                # Clean column names
                cleaned_profile = {k.lower().replace(' ', '_'): v for k, v in profile.items()}
                self.db_manager.insert_company_profile(cleaned_profile)
                logger.info(f"Stored profile for {symbol}")
            else:
                logger.warning(f"No profile data for {symbol}")
            
            # Rate limiting from configuration
            time.sleep(self.config.FMP_RATE_LIMIT_DELAY)
    
    def fetch_and_store_historical_data(self, symbols=None, limit=None):
        """Fetch historical price data for symbols"""
        if not symbols:
            symbols = self.db_manager.get_sp500_symbols()
        
        if limit:
            symbols = symbols[:limit]
        
        logger.info(f"Fetching historical data for {len(symbols)} symbols...")
        
        for i, symbol in enumerate(symbols, 1):
            if self.db_manager.symbol_has_historical_data(symbol):
                logger.info(f"Historical data for {symbol} already exists, skipping...")
                continue
                
            logger.info(f"Fetching historical data for {symbol} ({i}/{len(symbols)})")
            
            df = self.fmp_client.get_historical_prices(symbol)
            if not df.empty:
                # Clean column names
                df.columns = df.columns.str.lower().str.replace(' ', '_')
                self.db_manager.insert_historical_prices(symbol, df)
                logger.info(f"Stored {len(df)} price records for {symbol}")
            else:
                logger.warning(f"No historical data for {symbol}")
            
            # Rate limiting from configuration
            time.sleep(self.config.FMP_RATE_LIMIT_DELAY)
    
    def run_initial_setup(self):
        """Run initial data collection"""
        logger.info("Starting initial stock data collection...")
        
        # Step 1: Fetch S&P 500 constituents
        if not self.fetch_and_store_sp500_constituents():
            logger.error("Failed to fetch S&P 500 constituents, aborting...")
            return
        
        # Step 2: Fetch company profiles (configurable limit)
        self.fetch_and_store_company_profiles(limit=self.config.INITIAL_SETUP_COMPANY_PROFILES_LIMIT)
        
        # Step 3: Fetch historical data (configurable limit)
        self.fetch_and_store_historical_data(limit=self.config.INITIAL_SETUP_HISTORICAL_DATA_LIMIT)
        
        logger.info("Initial data collection completed!")
    
    def analyze_data(self):
        """Perform basic stock analysis"""
        logger.info("Performing basic stock analysis...")
        
        # Example analysis queries could go here
        with self.db_manager.engine.connect() as conn:
            # Get top 10 companies by market cap
            result = conn.execute(text("""
                SELECT symbol, companyname, mktcap 
                FROM company_profiles 
                WHERE mktcap IS NOT NULL 
                ORDER BY mktcap DESC 
                LIMIT 10
            """))
            
            logger.info("Top 10 companies by market cap:")
            for row in result.fetchall():
                logger.info(f"{row[0]}: {row[1]} - ${row[2]:,}")

def main():
    """Main application entry point"""
    try:
        analyst = StockAnalyst()
        analyst.run_initial_setup()
        analyst.analyze_data()
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()