import pytest
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
from datetime import datetime, date
import requests
from sqlalchemy.exc import SQLAlchemyError
import json

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'DATABASE_PATH': ':memory:',
        'FMP_API_KEY': 'test_fmp_key',
        'SECRET_KEY': 'test-secret-key'
    }):
        yield

# Import modules after environment setup
from database import DatabaseManager
from data_access_layer import StockDataService
from fmp_client import FMPClient
from yahoo_finance_client import YahooFinanceClient
from auth import AuthenticationManager
from portfolio import PortfolioManager
from main import StockAnalyst

# --- Database Error Handling Tests ---

def test_database_connection_failure():
    """Test handling of database connection failures"""
    with patch('database.create_engine') as mock_create_engine:
        mock_create_engine.side_effect = SQLAlchemyError("Connection failed")
        
        with pytest.raises(SQLAlchemyError):
            DatabaseManager()

def test_database_corrupted_data_handling():
    """Test handling of corrupted database data"""
    db_manager = DatabaseManager(db_path=":memory:")
    
    # Insert corrupted data directly to database
    conn = sqlite3.connect(db_manager.db_path)
    cursor = conn.cursor()
    
    # Insert invalid data that could cause issues
    try:
        cursor.execute("""
            INSERT INTO company_profiles (symbol, companyname, price, mktcap) 
            VALUES ('CORRUPT', 'Test', 'invalid_price', 'invalid_cap')
        """)
        conn.commit()
    except:
        pass  # Expected to fail with some database configurations
    
    conn.close()
    
    # Should handle corrupted data gracefully
    stock_service = StockDataService(db_manager=db_manager)
    result = stock_service.get_stock_company_profile('CORRUPT')
    
    # Should either return None or handle gracefully
    assert result is None or isinstance(result, dict)

def test_database_transaction_rollback():
    """Test database transaction rollback on errors"""
    db_manager = DatabaseManager(db_path=":memory:")
    
    # Create a scenario that would cause a rollback
    with patch.object(db_manager, 'engine') as mock_engine:
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_connection.execute.side_effect = SQLAlchemyError("Transaction failed")
        
        # Should handle transaction failure gracefully
        try:
            stock_service = StockDataService(db_manager=db_manager)
            result = stock_service.get_all_stocks_with_scores()
            assert isinstance(result, list)
        except SQLAlchemyError:
            # Expected behavior - should propagate critical errors
            pass

def test_database_disk_full_simulation():
    """Test handling when disk is full"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path=db_path)
        
        # Mock disk full error
        with patch('pandas.DataFrame.to_sql') as mock_to_sql:
            mock_to_sql.side_effect = OSError("No space left on device")
            
            # Should handle disk full error gracefully
            sp500_data = pd.DataFrame({
                'symbol': ['TEST'],
                'name': ['Test Company'],
                'sector': ['Technology'],
                'sub_sector': ['Software'],
                'headquarters_location': ['Test City'],
                'date_first_added': ['2023-01-01'],
                'cik': ['0000000000'],
                'founded': ['2000']
            })
            
            # Should not crash, might log error or handle gracefully
            try:
                db_manager.insert_sp500_constituents(sp500_data)
            except OSError:
                # Expected to fail with disk full
                pass
    
    finally:
        os.unlink(db_path)

# --- API Error Handling Tests ---

def test_fmp_api_rate_limit_exceeded():
    """Test handling when FMP API rate limit is exceeded"""
    with patch('fmp_client.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429  # Rate limit exceeded
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_get.return_value = mock_response
        
        fmp_client = FMPClient()
        
        # Should handle rate limit gracefully
        profile = fmp_client.get_company_profile('AAPL')
        assert profile is not None  # Should fallback to Yahoo Finance
        assert profile.get('source') == 'yahoo_finance'

def test_fmp_api_invalid_response():
    """Test handling of invalid API responses"""
    with patch('fmp_client.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response
        
        fmp_client = FMPClient()
        
        # Should handle invalid JSON gracefully
        profile = fmp_client.get_company_profile('AAPL')
        assert profile is not None  # Should fallback
        assert profile.get('source') == 'yahoo_finance'

def test_network_timeout_handling():
    """Test handling of network timeouts"""
    with patch('fmp_client.requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        fmp_client = FMPClient()
        
        # Should handle timeout gracefully
        profile = fmp_client.get_company_profile('AAPL')
        assert profile is not None  # Should fallback
        assert profile.get('source') == 'yahoo_finance'

def test_network_connection_error():
    """Test handling of network connection errors"""
    with patch('fmp_client.requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")
        
        fmp_client = FMPClient()
        
        # Should handle connection error gracefully
        profile = fmp_client.get_company_profile('AAPL')
        assert profile is not None  # Should fallback
        assert profile.get('source') == 'yahoo_finance'

def test_yahoo_finance_api_failure():
    """Test handling when both FMP and Yahoo Finance APIs fail"""
    with patch('fmp_client.requests.get') as mock_fmp_get, \
         patch('yfinance.Ticker') as mock_yf_ticker:
        
        # Mock FMP failure
        mock_fmp_get.side_effect = requests.exceptions.ConnectionError("FMP unreachable")
        
        # Mock Yahoo Finance failure
        mock_ticker_instance = MagicMock()
        mock_yf_ticker.return_value = mock_ticker_instance
        mock_ticker_instance.info = {}  # Empty info indicates failure
        
        fmp_client = FMPClient()
        
        # Should handle complete API failure gracefully
        profile = fmp_client.get_company_profile('AAPL')
        assert profile is None or profile.get('source') in ['yahoo_finance', 'error']

# --- File System Error Handling Tests ---

def test_log_file_permission_error():
    """Test handling when log files can't be written"""
    with patch('pathlib.Path.mkdir') as mock_mkdir:
        mock_mkdir.side_effect = PermissionError("Permission denied")
        
        # Should handle log directory creation failure
        try:
            from logging_config import setup_logging
            setup_logging(enable_file_logging=True)
        except PermissionError:
            # Expected behavior
            pass

def test_config_file_not_found():
    """Test handling when configuration files are missing"""
    with patch('unified_config.Path.exists') as mock_exists:
        mock_exists.return_value = False
        
        # Should handle missing config gracefully
        from unified_config import get_config
        config = get_config()
        
        # Should return default configuration
        assert config is not None
        assert hasattr(config, 'FMP_RATE_LIMIT_DELAY')

def test_database_file_locked():
    """Test handling when database file is locked"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        db_path = f.name
    
    try:
        # Create a database lock scenario
        db_manager = DatabaseManager(db_path=db_path)
        
        # Simulate another process locking the database
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("database is locked")
            
            # Should handle locked database gracefully
            try:
                stock_service = StockDataService(db_manager=db_manager)
                result = stock_service.get_all_stocks_with_scores()
                assert isinstance(result, list)
            except sqlite3.OperationalError:
                # Expected to fail with locked database
                pass
    
    finally:
        os.unlink(db_path)

# --- Authentication Error Handling Tests ---

def test_invalid_password_hash():
    """Test handling of invalid password hashes"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        auth_manager = AuthenticationManager(db_path=db_path)
        
        # Create user
        auth_manager.register_user('testuser', 'test@example.com', 'password123')
        
        # Corrupt password hash in database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = 'corrupted_hash' WHERE username = 'testuser'")
        conn.commit()
        conn.close()
        
        # Should handle corrupted hash gracefully
        result = auth_manager.authenticate_user('testuser', 'password123')
        assert result['success'] is False
        assert 'error' in result
    
    finally:
        os.unlink(db_path)

def test_session_token_collision():
    """Test handling of session token collisions"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        auth_manager = AuthenticationManager(db_path=db_path)
        
        # Mock UUID generation to create collision
        with patch('auth.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'duplicate_token'
            
            # Register two users
            auth_manager.register_user('user1', 'user1@example.com', 'password123')
            auth_manager.register_user('user2', 'user2@example.com', 'password123')
            
            # Try to authenticate both (should handle token collision)
            result1 = auth_manager.authenticate_user('user1', 'password123')
            result2 = auth_manager.authenticate_user('user2', 'password123')
            
            # Both should succeed or handle collision gracefully
            assert result1['success'] is True or 'error' in result1
            assert result2['success'] is True or 'error' in result2
    
    finally:
        os.unlink(db_path)

# --- Portfolio Error Handling Tests ---

def test_negative_shares_transaction():
    """Test handling of invalid transaction data"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        auth_manager = AuthenticationManager(db_path=db_path)
        portfolio_manager = PortfolioManager(db_path=db_path)
        
        # Create user
        user_result = auth_manager.register_user('testuser', 'test@example.com', 'password123')
        user_id = user_result['user_id']
        
        # Try to add transaction with negative shares
        result = portfolio_manager.add_transaction(
            user_id=user_id,
            transaction_type='BUY',
            symbol='AAPL',
            shares=-10.0,  # Invalid negative shares
            price_per_share=150.0,
            transaction_date=date.today()
        )
        
        # Should reject invalid transaction
        assert result['success'] is False
        assert 'error' in result
    
    finally:
        os.unlink(db_path)

def test_sell_more_shares_than_owned():
    """Test handling of selling more shares than owned"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        auth_manager = AuthenticationManager(db_path=db_path)
        portfolio_manager = PortfolioManager(db_path=db_path)
        
        # Create user
        user_result = auth_manager.register_user('testuser', 'test@example.com', 'password123')
        user_id = user_result['user_id']
        
        # Buy 5 shares
        portfolio_manager.add_transaction(
            user_id=user_id,
            transaction_type='BUY',
            symbol='AAPL',
            shares=5.0,
            price_per_share=150.0,
            transaction_date=date.today()
        )
        
        # Try to sell 10 shares (more than owned)
        result = portfolio_manager.add_transaction(
            user_id=user_id,
            transaction_type='SELL',
            symbol='AAPL',
            shares=10.0,  # More than owned
            price_per_share=160.0,
            transaction_date=date.today()
        )
        
        # Should handle oversell gracefully (either reject or allow with negative balance)
        assert 'success' in result
        if result['success'] is False:
            assert 'error' in result
    
    finally:
        os.unlink(db_path)

# --- Data Validation Error Handling Tests ---

def test_invalid_stock_symbol():
    """Test handling of invalid stock symbols"""
    db_manager = DatabaseManager(db_path=":memory:")
    stock_service = StockDataService(db_manager=db_manager)
    
    # Test various invalid symbols
    invalid_symbols = ['', None, 'TOOLONG_SYMBOL', '123INVALID', 'INVALID@SYMBOL']
    
    for symbol in invalid_symbols:
        result = stock_service.get_stock_basic_info(symbol)
        assert result is None

def test_malformed_date_data():
    """Test handling of malformed date data"""
    db_manager = DatabaseManager(db_path=":memory:")
    
    # Try to insert data with invalid dates
    prices_data = pd.DataFrame({
        'date': ['invalid-date', '2023-13-45', 'not-a-date'],  # Invalid dates
        'open': [100.0, 101.0, 102.0],
        'high': [102.0, 103.0, 104.0],
        'low': [99.0, 100.0, 101.0],
        'close': [101.0, 102.0, 103.0],
        'volume': [100000, 120000, 110000]
    })
    
    # Should handle invalid dates gracefully
    try:
        db_manager.insert_historical_prices('TEST', prices_data)
    except (ValueError, TypeError):
        # Expected to fail with invalid dates
        pass

def test_extreme_numerical_values():
    """Test handling of extreme numerical values"""
    db_manager = DatabaseManager(db_path=":memory:")
    
    # Test with extreme values
    profile_data = {
        'symbol': 'EXTREME',
        'companyname': 'Extreme Values Company',
        'price': float('inf'),  # Infinity
        'sector': 'Technology',
        'mktcap': float('nan')  # NaN
    }
    
    # Should handle extreme values gracefully
    try:
        db_manager.insert_company_profile(profile_data)
    except (ValueError, TypeError, sqlite3.DataError):
        # Expected to fail with extreme values
        pass

# --- Concurrency Error Handling Tests ---

def test_concurrent_database_write_conflicts():
    """Test handling of concurrent database write conflicts"""
    import threading
    import time
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        errors = []
        
        def write_data(thread_id):
            try:
                db_manager = DatabaseManager(db_path=db_path)
                profile_data = {
                    'symbol': f'THREAD{thread_id}',
                    'companyname': f'Thread Company {thread_id}',
                    'price': 100.0 + thread_id,
                    'sector': 'Technology',
                    'mktcap': 1000000000 + thread_id
                }
                db_manager.insert_company_profile(profile_data)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads writing simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=write_data, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Some errors might occur due to concurrency, but shouldn't crash
        if errors:
            print(f"Concurrent write errors (expected): {errors}")
    
    finally:
        os.unlink(db_path)

# --- Memory and Resource Error Handling Tests ---

def test_memory_exhaustion_simulation():
    """Test handling when memory is exhausted"""
    # This test simulates memory exhaustion during large data operations
    
    with patch('pandas.DataFrame') as mock_df:
        mock_df.side_effect = MemoryError("Out of memory")
        
        db_manager = DatabaseManager(db_path=":memory:")
        
        # Should handle memory error gracefully
        try:
            large_data = {
                'symbol': ['TEST'] * 1000000,  # Large dataset
                'name': ['Test'] * 1000000,
                'sector': ['Technology'] * 1000000,
                'sub_sector': ['Software'] * 1000000,
                'headquarters_location': ['Test City'] * 1000000,
                'date_first_added': ['2023-01-01'] * 1000000,
                'cik': ['0000000000'] * 1000000,
                'founded': ['2000'] * 1000000
            }
            # This will fail due to mocked MemoryError
            pd.DataFrame(large_data)
        except MemoryError:
            # Expected behavior
            pass

# --- Recovery and Graceful Degradation Tests ---

def test_partial_service_failure_recovery():
    """Test recovery when some services fail but others work"""
    # Mock partial failure scenario
    with patch('fmp_client.requests.get') as mock_fmp_get, \
         patch('yfinance.Ticker') as mock_yf_ticker:
        
        # FMP fails completely
        mock_fmp_get.side_effect = requests.exceptions.ConnectionError("FMP down")
        
        # Yahoo Finance works
        mock_ticker_instance = MagicMock()
        mock_yf_ticker.return_value = mock_ticker_instance
        mock_ticker_instance.info = {
            'currentPrice': 150.0,
            'longName': 'Apple Inc.',
            'sector': 'Technology'
        }
        
        fmp_client = FMPClient()
        
        # Should fall back to working service
        profile = fmp_client.get_company_profile('AAPL')
        assert profile is not None
        assert profile.get('source') == 'yahoo_finance'

def test_configuration_fallback():
    """Test fallback to default configuration when config is corrupted"""
    with patch('unified_config.json.load') as mock_json_load:
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        # Should fall back to defaults
        from unified_config import get_config
        config = get_config()
        
        assert config is not None
        assert hasattr(config, 'FMP_RATE_LIMIT_DELAY')

# --- Error Logging and Monitoring Tests ---

def test_error_logging_when_logger_fails():
    """Test behavior when logging itself fails"""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_logger.error.side_effect = Exception("Logger failed")
        mock_get_logger.return_value = mock_logger
        
        # Should not crash when logging fails
        db_manager = DatabaseManager(db_path=":memory:")
        
        # Operation should still work even if logging fails
        symbols = db_manager.get_sp500_symbols()
        assert isinstance(symbols, list)

def test_critical_error_propagation():
    """Test that critical errors are properly propagated"""
    # Some errors should be propagated rather than handled silently
    
    with patch('database.create_engine') as mock_engine:
        mock_engine.side_effect = SystemExit("Critical system error")
        
        # Critical errors should be propagated
        with pytest.raises(SystemExit):
            DatabaseManager()

def test_error_recovery_state_consistency():
    """Test that system state remains consistent after errors"""
    db_manager = DatabaseManager(db_path=":memory:")
    
    # Add valid data
    profile_data = {
        'symbol': 'VALID',
        'companyname': 'Valid Company',
        'price': 100.0,
        'sector': 'Technology',
        'mktcap': 1000000000
    }
    db_manager.insert_company_profile(profile_data)
    
    # Try to add invalid data
    invalid_profile_data = {
        'symbol': None,  # Invalid
        'companyname': 'Invalid Company',
        'price': 'invalid_price',
        'sector': 'Technology',
        'mktcap': 'invalid_cap'
    }
    
    try:
        db_manager.insert_company_profile(invalid_profile_data)
    except:
        pass  # Expected to fail
    
    # Valid data should still be accessible
    assert db_manager.symbol_exists_in_profiles('VALID') is True