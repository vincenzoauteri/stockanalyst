#!/usr/bin/env python3
"""
Test script for new financial data implementation
Tests database creation, data fetching, and basic functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from yahoo_finance_client import YahooFinanceClient
from data_fetcher import DataFetcher
from data_access_layer import StockDataService
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_schema():
    """Test that new database tables are created properly"""
    logger.info("Testing database schema...")
    
    try:
        db = DatabaseManager()
        
        # Test that tables exist by querying them
        with db.engine.connect() as conn:
            tables_to_test = [
                'corporate_actions',
                'income_statements', 
                'balance_sheets',
                'cash_flow_statements',
                'analyst_recommendations'
            ]
            
            for table in tables_to_test:
                try:
                    from sqlalchemy import text
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    logger.info(f"✓ Table '{table}' exists with {count} records")
                except Exception as e:
                    logger.error(f"✗ Table '{table}' failed: {e}")
                    return False
        
        logger.info("✓ Database schema test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database schema test failed: {e}")
        return False

def test_yahoo_finance_client():
    """Test Yahoo Finance client with new methods"""
    logger.info("Testing Yahoo Finance client...")
    
    try:
        client = YahooFinanceClient()
        symbol = "AAPL"
        
        # Test corporate actions
        logger.info(f"Testing corporate actions for {symbol}...")
        actions = client.get_corporate_actions(symbol)
        if actions and actions.get('actions'):
            logger.info(f"✓ Corporate actions: {len(actions['actions'])} actions found")
        else:
            logger.warning(f"⚠ Corporate actions: No data returned for {symbol}")
        
        # Test financial statements
        logger.info(f"Testing financial statements for {symbol}...")
        statements = client.get_financial_statements(symbol)
        if statements:
            income_count = len(statements.get('income_statements', []))
            balance_count = len(statements.get('balance_sheets', []))
            cashflow_count = len(statements.get('cash_flow_statements', []))
            logger.info(f"✓ Financial statements: {income_count} income, {balance_count} balance, {cashflow_count} cash flow")
        else:
            logger.warning(f"⚠ Financial statements: No data returned for {symbol}")
        
        # Test analyst recommendations
        logger.info(f"Testing analyst recommendations for {symbol}...")
        recommendations = client.get_analyst_recommendations(symbol)
        if recommendations and recommendations.get('recommendations'):
            logger.info(f"✓ Analyst recommendations: {len(recommendations['recommendations'])} periods found")
        else:
            logger.warning(f"⚠ Analyst recommendations: No data returned for {symbol}")
        
        logger.info("✓ Yahoo Finance client test completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Yahoo Finance client test failed: {e}")
        return False

def test_data_access_layer():
    """Test data access layer methods"""
    logger.info("Testing data access layer...")
    
    try:
        service = StockDataService()
        
        # Test basic connection
        stocks = service.get_all_stocks_with_scores()
        logger.info(f"✓ Basic connection: {len(stocks)} stocks retrieved")
        
        # Test new methods (they should return empty lists if no data)
        symbol = "AAPL"
        
        actions = service.get_corporate_actions(symbol)
        logger.info(f"✓ Corporate actions query: {len(actions)} records")
        
        income = service.get_income_statements(symbol)
        logger.info(f"✓ Income statements query: {len(income)} records")
        
        balance = service.get_balance_sheets(symbol)
        logger.info(f"✓ Balance sheets query: {len(balance)} records")
        
        cashflow = service.get_cash_flow_statements(symbol)
        logger.info(f"✓ Cash flow statements query: {len(cashflow)} records")
        
        recommendations = service.get_analyst_recommendations(symbol)
        logger.info(f"✓ Analyst recommendations query: {len(recommendations)} records")
        
        # Test financial summary
        summary = service.get_financial_summary(symbol)
        logger.info(f"✓ Financial summary: {len(summary)} keys in response")
        
        logger.info("✓ Data access layer test completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Data access layer test failed: {e}")
        return False

def test_data_collection():
    """Test data collection for a small sample"""
    logger.info("Testing data collection...")
    
    try:
        fetcher = DataFetcher()
        
        # Test with a small sample
        test_symbols = ["AAPL"]
        
        logger.info("Testing corporate actions collection...")
        result1 = fetcher.fetch_corporate_actions(test_symbols, max_requests=1)
        logger.info(f"✓ Corporate actions: {result1} symbols processed")
        
        logger.info("Testing financial statements collection...")
        result2 = fetcher.fetch_financial_statements(test_symbols, max_requests=1)
        logger.info(f"✓ Financial statements: {result2} symbols processed")
        
        logger.info("Testing analyst recommendations collection...")
        result3 = fetcher.fetch_analyst_recommendations(test_symbols, max_requests=1)
        logger.info(f"✓ Analyst recommendations: {result3} symbols processed")
        
        logger.info("✓ Data collection test completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Data collection test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=== Starting New Financial Data Implementation Tests ===")
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Yahoo Finance Client", test_yahoo_finance_client),
        ("Data Access Layer", test_data_access_layer),
        ("Data Collection", test_data_collection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"Test '{test_name}' failed!")
    
    logger.info(f"\n=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        logger.info("🎉 All tests passed! Implementation is ready.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)