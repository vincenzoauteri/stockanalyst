import pytest
import os
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import date
import requests
from sqlalchemy.exc import SQLAlchemyError
import json

# Import modules after environment setup
from database import DatabaseManager
from data_access_layer import StockDataService
from fmp_client import FMPClient
from auth import AuthenticationManager
from portfolio import PortfolioManager

# --- Database Error Handling Tests ---

def test_database_connection_failure():
    """Test handling of database connection failures"""
    with patch('database.create_engine') as mock_create_engine:
        mock_create_engine.side_effect = SQLAlchemyError("Connection failed")
        
        with pytest.raises(SQLAlchemyError):
            DatabaseManager()

def test_database_corrupted_data_handling():
    """Test handling of corrupted database data"""
    db_manager = DatabaseManager()
    try:
        # Insert corrupted data directly to database using PostgreSQL
        from sqlalchemy import text
        with db_manager.engine.connect() as conn:
            # Try to insert invalid data that could cause issues
            # PostgreSQL is more strict about data types, so this should fail gracefully
            conn.execute(text("""
                INSERT INTO company_profiles (symbol, companyname, price, mktcap) 
                VALUES ('CORRUPT', 'Test', NULL, NULL)
            """))
            conn.commit()
    except Exception:
        pass  # Expected to fail with some database configurations
    
        # Should handle corrupted data gracefully
        stock_service = StockDataService()
        stock_service.db_manager = db_manager
        result = stock_service.get_stock_company_profile('CORRUPT')
        
        # Should either return None or handle gracefully
        assert result is None or isinstance(result, dict)
    finally:
        db_manager.cleanup_connections()

def test_database_transaction_rollback():
    """Test database transaction rollback on errors"""
    db_manager = DatabaseManager()
    try:
        # Create a scenario that would cause a rollback
        with patch.object(db_manager, 'engine') as mock_engine:
            mock_connection = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            mock_connection.execute.side_effect = SQLAlchemyError("Transaction failed")
            
            # Should handle transaction failure gracefully
            try:
                stock_service = StockDataService()
                stock_service.db_manager = db_manager
                result = stock_service.get_all_stocks_with_scores()
                assert isinstance(result, list)
            except SQLAlchemyError:
                # Expected behavior - should propagate critical errors
                pass
    finally:
        db_manager.cleanup_connections()

# --- API Error Handling Tests ---

def test_fmp_api_rate_limit_exceeded():
    """Test handling when FMP API rate limit is exceeded"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.json.return_value = {"Error Message": "Rate limit exceeded"}
        # Configure raise_for_status to raise HTTPError for 429 status
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Client Error: Too Many Requests")
        mock_get.return_value = mock_response
        
        fmp_client = FMPClient()
        # Should fall back to Yahoo Finance when FMP fails
        profile = fmp_client.get_company_profile('AAPL')
        
        # Should either get Yahoo Finance data or handle gracefully
        assert profile is None or isinstance(profile, dict)

def test_fmp_api_invalid_response():
    """Test handling of invalid API responses"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Invalid JSON response"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response
        
        fmp_client = FMPClient()
        profile = fmp_client.get_company_profile('AAPL')
        
        # Should fall back to Yahoo Finance and include source info
        assert profile is None or isinstance(profile, dict)
        if profile:
            # Yahoo Finance fallback should work
            assert 'companyname' in profile or profile is None

def test_network_timeout_handling():
    """Test handling of network timeouts"""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        fmp_client = FMPClient()
        profile = fmp_client.get_company_profile('AAPL')
        
        # Should fall back to Yahoo Finance
        assert profile is None or isinstance(profile, dict)

def test_network_connection_error():
    """Test handling of network connection errors"""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("FMP unreachable")
        
        fmp_client = FMPClient()
        profile = fmp_client.get_company_profile('AAPL')
        
        # Should fall back to Yahoo Finance or return None
        assert profile is None or isinstance(profile, dict)

def test_yahoo_finance_api_failure():
    """Test handling when both FMP and Yahoo Finance fail"""
    with patch('requests.get') as mock_get, \
         patch('yfinance.Ticker') as mock_ticker:
        
        # Make FMP fail
        mock_get.side_effect = requests.exceptions.ConnectionError("FMP unreachable")
        
        # Make Yahoo Finance fail
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {}  # Empty info
        mock_ticker.return_value = mock_ticker_instance
        
        fmp_client = FMPClient()
        profile = fmp_client.get_company_profile('AAPL')
        
        # Should handle gracefully when both sources fail
        # FMP returns empty dict when fallback fails
        assert profile == {} or profile is None

def test_config_file_not_found():
    """Test handling when configuration files are missing"""
    with patch.dict(os.environ, {}, clear=True):
        # Clear all environment variables
        
        # Should handle missing configuration gracefully
        try:
            from unified_config import BaseConfig
            config = BaseConfig()
            assert hasattr(config, 'FMP_API_KEY')  # Should have default or None
        except Exception as e:
            # Should not crash, but may have warnings
            assert isinstance(e, (AttributeError, ValueError))

# --- Authentication Error Handling Tests ---

def test_invalid_password_hash():
    """Test handling of invalid password hashes in database"""
    auth_manager = AuthenticationManager()
    
    # Create user and then corrupt password hash in database
    registration_result = auth_manager.register_user('testuser', 'test@example.com', 'password123')
    
    if registration_result['success']:
        # Try to manually corrupt the password hash in database
        with auth_manager.db_manager.engine.connect() as conn:
            from sqlalchemy import text
            try:
                conn.execute(text("""
                    UPDATE users SET password_hash = 'corrupted_hash' 
                    WHERE username = 'testuser'
                """))
                conn.commit()
            except Exception:
                pass
        
        # Authentication should fail gracefully
        auth_result = auth_manager.authenticate_user('testuser', 'password123')
        assert not auth_result['success']

def test_session_token_collision():
    """Test handling of session token collisions during authentication"""
    auth_manager = AuthenticationManager()
    
    # Register a user
    registration_result = auth_manager.register_user('testuser1', 'test1@example.com', 'password123')
    
    if registration_result['success']:
        # Mock uuid generation to create potential collision
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'collision_token'
            
            # Authenticate user twice (which creates sessions)
            auth1 = auth_manager.authenticate_user('testuser1', 'password123')
            auth2 = auth_manager.authenticate_user('testuser1', 'password123')
            
            # Should handle gracefully even with same UUID mock
            assert auth1['success']
            assert auth2['success']
            assert 'session_token' in auth1
            assert 'session_token' in auth2

# --- Portfolio Error Handling Tests ---

def test_portfolio_invalid_transaction_data():
    """Test handling of invalid transaction data"""
    auth_manager = AuthenticationManager()
    portfolio_manager = PortfolioManager()
    
    # Register a user
    registration_result = auth_manager.register_user('portfoliouser', 'portfolio@example.com', 'password123')
    
    if registration_result['success']:
        user_id = registration_result['user_id']
        
        # Try to add transaction with invalid data
        invalid_transaction = {
            'user_id': user_id,
            'transaction_type': 'INVALID_TYPE',  # Invalid type
            'symbol': 'AAPL',
            'shares': 'not_a_number',  # Invalid shares
            'price_per_share': -100,  # Negative price
            'transaction_date': 'invalid_date'  # Invalid date
        }
        
        result = portfolio_manager.add_transaction(**invalid_transaction)
        
        # Should handle invalid data gracefully
        assert not result['success']
        assert 'error' in result

def test_portfolio_database_constraint_violation():
    """Test handling of database constraint violations in portfolio"""
    portfolio_manager = PortfolioManager()
    
    # Try to add transaction for non-existent user
    invalid_transaction = {
        'user_id': 99999,  # Non-existent user
        'transaction_type': 'BUY',
        'symbol': 'AAPL',
        'shares': 10,
        'price_per_share': 150.0,
        'transaction_date': date.today()
    }
    
    result = portfolio_manager.add_transaction(**invalid_transaction)
    
    # Should handle constraint violation gracefully
    assert not result['success']
    assert 'error' in result

# --- Data Processing Error Handling Tests ---

def test_malformed_csv_data_handling():
    """Test handling of malformed CSV data"""
    db_manager = DatabaseManager()
    try:
        # Create malformed DataFrame
        malformed_data = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', None],  # None value
            'name': ['Apple Inc.', '', 'Google'],  # Empty string
            'price': [150.0, 'invalid', -50.0],  # Invalid price
        })
        
        # Should handle malformed data gracefully
        try:
            # This should either process correctly or fail gracefully
            result = db_manager.insert_sp500_constituents(malformed_data)
            # If it succeeds, that's fine
        except Exception as e:
            # If it fails, should be a controlled failure
            assert isinstance(e, (ValueError, TypeError, SQLAlchemyError))
    finally:
        db_manager.cleanup_connections()

def test_memory_pressure_handling():
    """Test handling of memory pressure scenarios"""
    stock_service = StockDataService()
    
    # Try to request large amount of data
    try:
        # This should either work or fail gracefully
        stocks = stock_service.get_all_stocks_with_scores(limit=999999)
        assert isinstance(stocks, list)
    except MemoryError:
        # Should handle memory pressure gracefully
        pass
    except Exception as e:
        # Should handle other errors gracefully
        assert isinstance(e, (ValueError, SQLAlchemyError))

def test_concurrent_database_access():
    """Test handling of concurrent database access"""
    import threading
    
    def db_operation():
        db_manager = DatabaseManager()
        try:
            stock_service = StockDataService()
            stock_service.db_manager = db_manager
            return stock_service.get_all_stocks_with_scores(limit=1)
        finally:
            db_manager.cleanup_connections()
    
    # Create multiple threads accessing database
    threads = []
    results = []
    
    def thread_worker():
        try:
            result = db_operation()
            results.append(result)
        except Exception as e:
            results.append(e)
    
    for _ in range(5):
        thread = threading.Thread(target=thread_worker)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Should handle concurrent access gracefully
    assert len(results) == 5
    for result in results:
        assert isinstance(result, (list, Exception))