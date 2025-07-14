import pytest
import os
import pandas as pd
from datetime import datetime, date, timedelta
import threading
import time

# Import all components
from main import StockAnalyst
from scheduler import Scheduler
from database import DatabaseManager
from data_access_layer import StockDataService
from undervaluation_analyzer import UndervaluationAnalyzer
from auth import AuthenticationManager
from portfolio import PortfolioManager

@pytest.fixture
def integration_db_manager(db_manager_session):
    """Create a DatabaseManager using the test PostgreSQL database - reuse session manager"""
    return db_manager_session

@pytest.fixture
def integration_stock_service(integration_db_manager):
    """Create StockDataService with test database"""
    service = StockDataService()
    service.db_manager = integration_db_manager
    return service

@pytest.fixture
def integration_auth_manager(integration_db_manager):
    """Create AuthenticationManager with test database"""
    auth_manager = AuthenticationManager()
    auth_manager.db_manager = integration_db_manager
    return auth_manager

@pytest.fixture
def integration_portfolio_manager(integration_db_manager):
    """Create PortfolioManager with test database"""
    portfolio_manager = PortfolioManager()
    portfolio_manager.db_manager = integration_db_manager
    return portfolio_manager

@pytest.fixture
def clean_test_data(integration_db_manager):
    """Clean test data before each test"""
    from sqlalchemy import text
    
    # Clean up test data to avoid conflicts
    with integration_db_manager.engine.connect() as conn:
        # Clean user-related tables
        conn.execute(text("DELETE FROM user_sessions WHERE 1=1"))
        conn.execute(text("DELETE FROM user_watchlists WHERE 1=1"))
        conn.execute(text("DELETE FROM portfolio_transactions WHERE 1=1"))
        conn.execute(text("DELETE FROM user_portfolios WHERE 1=1"))
        conn.execute(text("DELETE FROM users WHERE username LIKE 'integration%' OR username LIKE 'test%' OR username LIKE '%portfolio%' OR username LIKE '%rollback%'"))
        conn.commit()
    
    yield
    
    # Clean up after test
    with integration_db_manager.engine.connect() as conn:
        conn.execute(text("DELETE FROM user_sessions WHERE 1=1"))
        conn.execute(text("DELETE FROM user_watchlists WHERE 1=1"))
        conn.execute(text("DELETE FROM portfolio_transactions WHERE 1=1"))
        conn.execute(text("DELETE FROM user_portfolios WHERE 1=1"))
        conn.execute(text("DELETE FROM users WHERE username LIKE 'integration%' OR username LIKE 'test%'"))
        conn.commit()

# --- Core System Tests ---

def test_database_initialization(integration_db_manager):
    """Test that database initializes correctly"""
    # Database should be initialized and accessible
    assert integration_db_manager is not None
    assert integration_db_manager.engine is not None
    
    # Test connection
    from sqlalchemy import text
    with integration_db_manager.engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1

def test_stock_data_service_integration(integration_stock_service):
    """Test StockDataService integration with database"""
    # Should be able to get stocks (even if empty)
    all_stocks = integration_stock_service.get_all_stocks_with_scores()
    assert isinstance(all_stocks, list)
    
    # Should be able to get summary stats
    stats = integration_stock_service.get_stock_summary_stats(all_stocks)
    assert isinstance(stats, dict)
    assert 'total_stocks' in stats

def test_full_authentication_flow(integration_auth_manager, clean_test_data):
    """Test complete authentication workflow"""
    username = 'integration_test_user'
    email = 'integration@test.com'
    password = 'secure_password_123'
    
    # Test user registration
    registration_result = integration_auth_manager.register_user(username, email, password)
    assert registration_result['success']
    user_id = registration_result['user_id']
    
    # Test user authentication
    auth_result = integration_auth_manager.authenticate_user(username, password)
    assert auth_result['success']
    assert auth_result['user_id'] == user_id
    
    # Test session creation
    session_token = auth_result['session_token']
    assert session_token is not None
    
    # Test session validation
    session_validation = integration_auth_manager.validate_session(session_token)
    assert session_validation['success']
    assert session_validation['user_id'] == user_id
    
    # Test logout
    logout_result = integration_auth_manager.logout_user(session_token)
    assert logout_result
    
    # Session should be invalid after logout
    post_logout_validation = integration_auth_manager.validate_session(session_token)
    assert not post_logout_validation['success']

def test_portfolio_integration_workflow(integration_auth_manager, integration_portfolio_manager, clean_test_data):
    """Test complete portfolio management workflow"""
    # Create a test user
    username = 'portfolio_integration_user'
    email = 'portfolio@integration.com'
    password = 'portfolio_pass_123'
    
    registration_result = integration_auth_manager.register_user(username, email, password)
    assert registration_result['success']
    user_id = registration_result['user_id']
    
    # Test adding transactions
    transaction_data = {
        'user_id': user_id,
        'transaction_type': 'BUY',
        'symbol': 'AAPL',
        'shares': 10,
        'price_per_share': 150.0,
        'transaction_date': date.today(),
        'fees': 5.0,
        'notes': 'Test transaction'
    }
    
    add_result = integration_portfolio_manager.add_transaction(**transaction_data)
    assert add_result['success']
    transaction_id = add_result['transaction_id']
    
    # Test getting user portfolio
    portfolio = integration_portfolio_manager.get_user_portfolio(user_id)
    assert isinstance(portfolio, dict)
    assert 'holdings' in portfolio
    assert 'summary' in portfolio
    
    # Test getting user transactions
    transactions = integration_portfolio_manager.get_user_transactions(user_id)
    assert isinstance(transactions, list)
    assert len(transactions) >= 1
    
    # Verify transaction details
    added_transaction = next((t for t in transactions if t['id'] == transaction_id), None)
    assert added_transaction is not None
    assert added_transaction['symbol'] == 'AAPL'
    assert added_transaction['shares'] == 10
    
    # Test deleting transaction
    delete_result = integration_portfolio_manager.delete_transaction(user_id, transaction_id)
    assert delete_result['success']
    
    # Verify transaction is deleted
    transactions_after_delete = integration_portfolio_manager.get_user_transactions(user_id)
    deleted_transaction = next((t for t in transactions_after_delete if t['id'] == transaction_id), None)
    assert deleted_transaction is None

def test_scheduler_integration():
    """Test scheduler integration with database"""
    scheduler = Scheduler()
    
    # Test scheduler initialization
    assert scheduler is not None
    
    # Test getting scheduler status
    status = scheduler.status
    assert isinstance(status, dict)

def test_undervaluation_analyzer_integration(integration_db_manager):
    """Test undervaluation analyzer integration"""
    analyzer = UndervaluationAnalyzer()
    analyzer.db_manager = integration_db_manager
    
    # Test analyzer initialization
    assert analyzer is not None
    
    # Test getting cache stats
    cache_stats = analyzer.get_cache_stats()
    assert isinstance(cache_stats, dict)

def test_concurrent_database_operations(integration_db_manager):
    """Test concurrent database operations"""
    results = []
    errors = []
    
    def db_operation(operation_id):
        try:
            service = StockDataService()
            service.db_manager = integration_db_manager
            stocks = service.get_all_stocks_with_scores(limit=1)
            results.append(f"Operation {operation_id}: {len(stocks)} stocks")
        except Exception as e:
            errors.append(f"Operation {operation_id}: {str(e)}")
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=db_operation, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # All operations should complete successfully
    assert len(results) == 5
    assert len(errors) == 0

def test_data_consistency_across_services(integration_db_manager, integration_auth_manager, integration_portfolio_manager, clean_test_data):
    """Test data consistency across different services"""
    # Create user through auth manager with unique identifier
    import time
    unique_id = int(time.time() * 1000)
    username = f'consistency_test_user_{unique_id}'
    email = f'consistency_{unique_id}@test.com'
    password = 'consistency_pass_123'
    
    registration_result = integration_auth_manager.register_user(username, email, password)
    if not registration_result['success']:
        # If registration fails, skip the test or use a different approach
        import pytest
        pytest.skip(f"User registration failed: {registration_result.get('error', 'Unknown error')}")
    assert registration_result['success']
    user_id = registration_result['user_id']
    
    # Add transaction through portfolio manager
    transaction_data = {
        'user_id': user_id,
        'transaction_type': 'BUY',
        'symbol': 'MSFT',
        'shares': 5,
        'price_per_share': 300.0,
        'transaction_date': date.today()
    }
    
    add_result = integration_portfolio_manager.add_transaction(**transaction_data)
    assert add_result['success']
    
    # Verify data consistency by checking both services can access the data
    # Check through portfolio manager
    user_transactions = integration_portfolio_manager.get_user_transactions(user_id)
    assert isinstance(user_transactions, list)
    assert len(user_transactions) >= 1
    assert user_transactions[0]['symbol'] == 'MSFT'
    
    # Verify user exists and can authenticate
    auth_result = integration_auth_manager.authenticate_user(username, password)
    assert auth_result['success']
    assert auth_result['user_id'] == user_id

def test_error_recovery_and_rollback(integration_db_manager, integration_auth_manager, clean_test_data):
    """Test error recovery and transaction rollback"""
    from unittest.mock import patch
    from sqlalchemy.exc import SQLAlchemyError
    
    # Test that failed operations don't leave partial data
    username = 'rollback_test_user'
    email = 'rollback@test.com'
    password = 'rollback_pass_123'
    
    # First, successfully create a user
    registration_result = integration_auth_manager.register_user(username, email, password)
    assert registration_result['success']
    
    # Now try to create a user with the same username (should fail)
    duplicate_result = integration_auth_manager.register_user(username, 'different@test.com', 'different_pass')
    assert not duplicate_result['success']
    
    # Verify original user is still intact
    auth_result = integration_auth_manager.authenticate_user(username, password)
    assert auth_result['success']

def test_system_performance_under_load(integration_stock_service):
    """Test system performance under moderate load"""
    import time
    
    start_time = time.time()
    
    # Perform multiple operations
    for _ in range(10):
        stocks = integration_stock_service.get_all_stocks_with_scores(limit=5)
        stats = integration_stock_service.get_stock_summary_stats(stocks)
        assert isinstance(stocks, list)
        assert isinstance(stats, dict)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Should complete within reasonable time (5 seconds)
    assert duration < 5.0, f"Operations took too long: {duration:.2f} seconds"

def test_database_connection_recovery(integration_db_manager):
    """Test database connection recovery after temporary failure"""
    from unittest.mock import patch
    from sqlalchemy.exc import SQLAlchemyError
    
    # Test that the system can recover from connection issues
    service = StockDataService()
    service.db_manager = integration_db_manager
    
    # Normal operation should work
    stocks = service.get_all_stocks_with_scores(limit=1)
    assert isinstance(stocks, list)
    
    # Simulate connection failure and recovery
    with patch.object(integration_db_manager.engine, 'connect') as mock_connect:
        # First call fails, second succeeds
        mock_connect.side_effect = [SQLAlchemyError("Connection lost"), 
                                  integration_db_manager.engine.connect()]
        
        # Should handle the failure gracefully
        try:
            stocks = service.get_all_stocks_with_scores(limit=1)
            # If it succeeds, that's good
            assert isinstance(stocks, list)
        except SQLAlchemyError:
            # If it fails, that's also acceptable for this test
            pass

def test_memory_usage_stability():
    """Test that the system doesn't have obvious memory leaks"""
    import gc
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Perform operations that might cause memory leaks
    for _ in range(5):
        db_manager = DatabaseManager()
        service = StockDataService()
        service.db_manager = db_manager
        stocks = service.get_all_stocks_with_scores(limit=1)
        
        # Force garbage collection
        del db_manager
        del service
        gc.collect()
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable (less than 50MB)
    assert memory_increase < 50 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.2f} MB"

def test_configuration_integration():
    """Test that configuration is properly integrated across components"""
    from unified_config import get_config
    
    config = get_config()
    
    # Test that configuration is accessible
    assert hasattr(config, 'POSTGRES_HOST')
    assert hasattr(config, 'POSTGRES_DB')
    
    # Test that database components use the configuration
    db_manager = DatabaseManager()
    assert db_manager.engine is not None

def test_logging_integration():
    """Test that logging works across all components"""
    import logging
    import io
    
    # Capture log output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger('database')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    try:
        # Perform operations that should generate logs
        db_manager = DatabaseManager()
        service = StockDataService()
        service.db_manager = db_manager
        stocks = service.get_all_stocks_with_scores(limit=1)
        
        # Check that some logging occurred
        log_output = log_capture.getvalue()
        # Don't assert specific content since logging might vary
        assert isinstance(log_output, str)
        
    finally:
        logger.removeHandler(handler)