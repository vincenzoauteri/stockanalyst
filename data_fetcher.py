#!/usr/bin/env python3
"""
Common Data Fetching Module for Stock Analyst
Provides shared functionality for daily updates and catch-up operations
"""

import time
import logging
from datetime import datetime
from typing import Dict, List
from database import DatabaseManager
from fmp_client import FMPClient

logger = logging.getLogger(__name__)

class DataFetcher:
    """
    Common data fetching functionality shared between daily updater and catchup scheduler
    """
    
    def __init__(self, daily_request_limit: int = 250, rate_limit_delay: float = 0.25):
        self.db_manager = DatabaseManager()
        self.fmp_client = FMPClient()
        self.daily_request_limit = daily_request_limit
        self.rate_limit_delay = rate_limit_delay
        self.request_count = 0
        
    def check_api_availability(self) -> bool:
        """Check if API key is configured and working"""
        if not self.fmp_client.api_key:
            logger.warning("No FMP API key configured. Skipping updates.")
            return False
        
        try:
            # Test API with a simple quote request
            profile = self.fmp_client.get_company_profile('AAPL')
            self.request_count += 1
            if profile and 'symbol' in profile:
                logger.info("API connection verified")
                return True
            else:
                logger.warning("API test returned unexpected response")
                return True  # API might be working but response format different
        except Exception as e:
            logger.error(f"API test error: {e}")
            return False
    
    def get_stale_data_priorities(self, max_symbols: int = 100) -> Dict[str, List[str]]:
        """
        Identify which data needs updating based on age
        Returns prioritized lists of symbols needing updates
        """
        priorities = {
            'critical': [],   # No data or very old (>7 days)
            'high': [],       # Moderately old (3-7 days)
            'medium': [],     # Somewhat old (1-3 days)
            'low': []         # Recent but could refresh (<1 day)
        }
        
        try:
            symbols = self.db_manager.get_sp500_symbols()
            
            # Limit symbols to avoid too many checks
            symbols_to_check = symbols[:max_symbols] if max_symbols else symbols
            
            for symbol in symbols_to_check:
                # Check if symbol has any historical data
                if not self.db_manager.symbol_has_historical_data(symbol):
                    priorities['critical'].append(symbol)
                    continue
                
                # Check price data freshness
                historical_data = self.db_manager.get_historical_prices_for_symbol(symbol, limit=1)
                if not historical_data:
                    priorities['critical'].append(symbol)
                    continue
                
                last_date_str = historical_data[0]['date']
                try:
                    last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
                    days_old = (datetime.now().date() - last_date).days
                    
                    if days_old > 7:
                        priorities['critical'].append(symbol)
                    elif days_old > 3:
                        priorities['high'].append(symbol)
                    elif days_old > 1:
                        priorities['medium'].append(symbol)
                    else:
                        priorities['low'].append(symbol)
                except ValueError:
                    # If date parsing fails, treat as critical
                    priorities['critical'].append(symbol)
            
            logger.info(f"Data priorities: {len(priorities['critical'])} critical, "
                      f"{len(priorities['high'])} high, {len(priorities['medium'])} medium, "
                      f"{len(priorities['low'])} low priority updates needed")
                
        except Exception as e:
            logger.error(f"Error analyzing data priorities: {e}")
        
        return priorities
    
    def update_sp500_constituents(self, budget: int) -> int:
        """Update S&P 500 constituents list (1 request)"""
        if budget < 1 or self.request_count >= self.daily_request_limit:
            return 0
        
        try:
            logger.info("Updating S&P 500 constituents...")
            time.sleep(self.rate_limit_delay)
            
            constituents = self.fmp_client.get_sp500_constituents()
            self.request_count += 1
            
            if not constituents.empty:
                # Normalize column names for database consistency
                constituents.columns = constituents.columns.str.replace(' ', '_').str.lower()
                self.db_manager.insert_sp500_constituents(constituents)
                logger.info(f"Updated {len(constituents)} S&P 500 constituents")
                return 1
            else:
                logger.warning("No S&P 500 constituents data received")
                return 1  # Still consumed the request
                
        except Exception as e:
            logger.error(f"Error updating S&P 500 constituents: {e}")
            return 0
    
    def update_company_profiles(self, symbols: List[str], budget: int) -> int:
        """Update company profiles for given symbols"""
        requests_used = 0
        
        for symbol in symbols:
            if requests_used >= budget or self.request_count >= self.daily_request_limit:
                break
            
            try:
                # Skip if profile already exists and is recent
                if self.db_manager.symbol_exists_in_profiles(symbol):
                    continue
                
                logger.debug(f"Fetching company profile for {symbol}")
                time.sleep(self.rate_limit_delay)
                
                profile = self.fmp_client.get_company_profile(symbol)
                self.request_count += 1
                requests_used += 1
                
                if profile:
                    # Normalize column names
                    normalized_profile = {k.replace(' ', '_').lower(): v for k, v in profile.items()}
                    self.db_manager.insert_company_profile(normalized_profile)
                    logger.debug(f"Updated profile for {symbol}")
                
            except Exception as e:
                logger.error(f"Error updating profile for {symbol}: {e}")
        
        logger.info(f"Updated {requests_used} company profiles")
        return requests_used
    
    def update_historical_prices(self, symbols: List[str], budget: int, period: str = '1year') -> int:
        """Update historical prices for given symbols"""
        requests_used = 0
        
        for symbol in symbols:
            if requests_used >= budget or self.request_count >= self.daily_request_limit:
                break
            
            try:
                logger.debug(f"Fetching historical prices for {symbol}")
                time.sleep(self.rate_limit_delay)
                
                prices = self.fmp_client.get_historical_prices(symbol, period)
                self.request_count += 1
                requests_used += 1
                
                if not prices.empty:
                    # Normalize column names
                    prices.columns = prices.columns.str.replace(' ', '_').str.lower()
                    self.db_manager.insert_historical_prices(symbol, prices)
                    logger.debug(f"Updated {len(prices)} price records for {symbol}")
                
            except Exception as e:
                logger.error(f"Error updating prices for {symbol}: {e}")
        
        logger.info(f"Updated historical prices for {requests_used} symbols")
        return requests_used
    
    def update_fundamentals_data(self, symbols: List[str], budget: int) -> int:
        """Update fundamental data (key metrics, ratios, income statements) for symbols"""
        requests_used = 0
        
        for symbol in symbols:
            if requests_used >= budget or self.request_count >= self.daily_request_limit:
                break
            
            try:
                # Get fundamentals summary (this uses multiple API calls internally)
                logger.debug(f"Fetching fundamentals for {symbol}")
                
                # Check remaining budget for fundamentals (typically uses 3 requests)
                if requests_used + 3 > budget:
                    break
                
                fundamentals = self.fmp_client.get_fundamentals_summary(symbol)
                self.request_count += 3  # Fundamentals summary uses 3 endpoints
                requests_used += 3
                
                if fundamentals and 'symbol' in fundamentals:
                    logger.debug(f"Updated fundamentals for {symbol}")
                    # Note: Fundamentals data could be stored in a separate table if needed
                
            except Exception as e:
                logger.error(f"Error updating fundamentals for {symbol}: {e}")
        
        logger.info(f"Updated fundamentals for {requests_used // 3} symbols using {requests_used} requests")
        return requests_used
    
    def get_missing_profiles(self) -> List[str]:
        """Get list of symbols that don't have company profiles"""
        try:
            all_symbols = self.db_manager.get_sp500_symbols()
            missing_profiles = []
            
            for symbol in all_symbols:
                if not self.db_manager.symbol_exists_in_profiles(symbol):
                    missing_profiles.append(symbol)
            
            logger.info(f"Found {len(missing_profiles)} symbols missing company profiles")
            return missing_profiles
            
        except Exception as e:
            logger.error(f"Error getting missing profiles: {e}")
            return []
    
    def get_request_summary(self) -> Dict[str, int]:
        """Get summary of requests used in this session"""
        return {
            'requests_used': self.request_count,
            'requests_remaining': max(0, self.daily_request_limit - self.request_count),
            'daily_limit': self.daily_request_limit
        }
    
    def has_budget_remaining(self, required_requests: int = 1) -> bool:
        """Check if there's enough budget for additional requests"""
        return (self.request_count + required_requests) <= self.daily_request_limit

    def fetch_corporate_actions(self, symbols: List[str], max_requests: int = 50) -> int:
        """
        Fetch corporate actions for given symbols using Yahoo Finance
        Returns number of symbols processed
        """
        logger.info(f"Fetching corporate actions for {len(symbols)} symbols")
        
        if not hasattr(self.fmp_client, 'yahoo_client') or not self.fmp_client.yahoo_client:
            logger.warning("Yahoo Finance client not available for corporate actions")
            return 0
        
        processed_count = 0
        
        for i, symbol in enumerate(symbols):
            if i >= max_requests:
                logger.info(f"Reached maximum request limit of {max_requests}")
                break
                
            try:
                logger.debug(f"Fetching corporate actions for {symbol} ({i+1}/{len(symbols)})")
                
                # Get corporate actions from Yahoo Finance
                actions_data = self.fmp_client.yahoo_client.get_corporate_actions(symbol)
                
                if actions_data and actions_data.get('actions'):
                    # Insert into database
                    self.db_manager.insert_corporate_actions(symbol, actions_data['actions'])
                    processed_count += 1
                    logger.debug(f"Updated corporate actions for {symbol}")
                else:
                    logger.debug(f"No corporate actions data found for {symbol}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error fetching corporate actions for {symbol}: {e}")
        
        logger.info(f"Processed corporate actions for {processed_count} symbols")
        return processed_count

    def fetch_financial_statements(self, symbols: List[str], max_requests: int = 50) -> int:
        """
        Fetch financial statements for given symbols using Yahoo Finance
        Returns number of symbols processed
        """
        logger.info(f"Fetching financial statements for {len(symbols)} symbols")
        
        if not hasattr(self.fmp_client, 'yahoo_client') or not self.fmp_client.yahoo_client:
            logger.warning("Yahoo Finance client not available for financial statements")
            return 0
        
        processed_count = 0
        
        for i, symbol in enumerate(symbols):
            if i >= max_requests:
                logger.info(f"Reached maximum request limit of {max_requests}")
                break
                
            try:
                logger.debug(f"Fetching financial statements for {symbol} ({i+1}/{len(symbols)})")
                
                # Get financial statements from Yahoo Finance
                statements_data = self.fmp_client.yahoo_client.get_financial_statements(symbol)
                
                if statements_data:
                    # Insert income statements
                    if statements_data.get('income_statements'):
                        self.db_manager.insert_income_statements(symbol, statements_data['income_statements'])
                    
                    # Insert balance sheets
                    if statements_data.get('balance_sheets'):
                        self.db_manager.insert_balance_sheets(symbol, statements_data['balance_sheets'])
                    
                    # Insert cash flow statements
                    if statements_data.get('cash_flow_statements'):
                        self.db_manager.insert_cash_flow_statements(symbol, statements_data['cash_flow_statements'])
                    
                    processed_count += 1
                    logger.debug(f"Updated financial statements for {symbol}")
                else:
                    logger.debug(f"No financial statements data found for {symbol}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error fetching financial statements for {symbol}: {e}")
        
        logger.info(f"Processed financial statements for {processed_count} symbols")
        return processed_count

    def fetch_analyst_recommendations(self, symbols: List[str], max_requests: int = 50) -> int:
        """
        Fetch analyst recommendations for given symbols using Yahoo Finance
        Returns number of symbols processed
        """
        logger.info(f"Fetching analyst recommendations for {len(symbols)} symbols")
        
        if not hasattr(self.fmp_client, 'yahoo_client') or not self.fmp_client.yahoo_client:
            logger.warning("Yahoo Finance client not available for analyst recommendations")
            return 0
        
        processed_count = 0
        
        for i, symbol in enumerate(symbols):
            if i >= max_requests:
                logger.info(f"Reached maximum request limit of {max_requests}")
                break
                
            try:
                logger.debug(f"Fetching analyst recommendations for {symbol} ({i+1}/{len(symbols)})")
                
                # Get analyst recommendations from Yahoo Finance
                recommendations_data = self.fmp_client.yahoo_client.get_analyst_recommendations(symbol)
                
                if recommendations_data and recommendations_data.get('recommendations'):
                    # Insert into database
                    self.db_manager.insert_analyst_recommendations(symbol, recommendations_data['recommendations'])
                    processed_count += 1
                    logger.debug(f"Updated analyst recommendations for {symbol}")
                else:
                    logger.debug(f"No analyst recommendations data found for {symbol}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error fetching analyst recommendations for {symbol}: {e}")
        
        logger.info(f"Processed analyst recommendations for {processed_count} symbols")
        return processed_count

    def fetch_all_new_data_types(self, symbols: List[str] = None, max_requests_per_type: int = 25) -> Dict[str, int]:
        """
        Fetch all new data types (corporate actions, financial statements, analyst recommendations)
        for given symbols or all S&P 500 symbols
        """
        if symbols is None:
            symbols = self.db_manager.get_sp500_symbols()
        
        logger.info(f"Fetching all new data types for {len(symbols)} symbols")
        
        results = {
            'corporate_actions': 0,
            'financial_statements': 0,
            'analyst_recommendations': 0,
            'total_symbols': len(symbols)
        }
        
        # Fetch corporate actions
        results['corporate_actions'] = self.fetch_corporate_actions(symbols, max_requests_per_type)
        
        # Fetch financial statements
        results['financial_statements'] = self.fetch_financial_statements(symbols, max_requests_per_type)
        
        # Fetch analyst recommendations
        results['analyst_recommendations'] = self.fetch_analyst_recommendations(symbols, max_requests_per_type)
        
        logger.info(f"Completed fetching new data types. Results: {results}")
        return results