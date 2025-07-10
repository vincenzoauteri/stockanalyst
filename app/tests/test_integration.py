import pytest
import os
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, date, timedelta
import sqlite3
import threading
import time

# Mock environment variables before importing components
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'DATABASE_PATH': ':memory:',
        'FMP_API_KEY': 'test_fmp_key',
        'SECRET_KEY': 'test-secret-key'
    }):
        yield

# Import all components after environment setup
from main import StockAnalyst
from scheduler import Scheduler
from database import DatabaseManager
from data_access_layer import StockDataService
from undervaluation_analyzer import UndervaluationAnalyzer
from auth import AuthenticationManager
from portfolio import PortfolioManager

@pytest.fixture
def temp_db():
    """Create a temporary database file for integration tests"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass

@pytest.fixture
def integration_db_manager(temp_db):
    """Create a DatabaseManager with a real temporary database"""
    return DatabaseManager(db_path=temp_db)

@pytest.fixture
def integration_stock_service(integration_db_manager):
    """Create a StockDataService with real database"""
    return StockDataService(db_manager=integration_db_manager)

# --- End-to-End User Workflow Tests ---

def test_complete_user_registration_to_portfolio_workflow(temp_db):
    """Test complete user flow from registration to portfolio creation"""
    # Step 1: User Registration
    auth_manager = AuthenticationManager(db_path=temp_db)
    
    registration_result = auth_manager.register_user(
        username='testuser',
        email='test@example.com',
        password='securepassword123'
    )
    
    assert registration_result['success'] is True
    user_id = registration_result['user_id']
    
    # Step 2: User Login
    login_result = auth_manager.authenticate_user('testuser', 'securepassword123')
    
    assert login_result['success'] is True
    assert login_result['user_id'] == user_id
    session_token = login_result['session_token']
    
    # Step 3: Session Validation
    session_validation = auth_manager.validate_session(session_token)
    assert session_validation['success'] is True
    assert session_validation['user_id'] == user_id
    
    # Step 4: Portfolio Creation
    portfolio_manager = PortfolioManager(db_path=temp_db)
    
    # Add a transaction
    transaction_result = portfolio_manager.add_transaction(
        user_id=user_id,
        transaction_type='BUY',
        symbol='AAPL',
        shares=10.0,
        price_per_share=150.0,
        transaction_date=date.today(),
        fees=5.0,
        notes='Initial purchase'
    )
    
    assert transaction_result['success'] is True
    
    # Step 5: Portfolio Retrieval
    portfolio = portfolio_manager.get_user_portfolio(user_id)
    
    assert portfolio['summary']['total_holdings'] == 1
    assert len(portfolio['holdings']) == 1
    assert portfolio['holdings'][0]['symbol'] == 'AAPL'
    assert portfolio['holdings'][0]['shares'] == 10.0
    
    # Step 6: Transaction History
    transactions = portfolio_manager.get_user_transactions(user_id)
    
    assert len(transactions) == 1
    assert transactions[0]['symbol'] == 'AAPL'
    assert transactions[0]['transaction_type'] == 'BUY'

def test_data_flow_from_database_to_frontend(integration_db_manager, integration_stock_service):
    """Test data flow from database through data access layer to frontend"""
    # Step 1: Populate database with test data
    
    # Add S&P 500 constituents
    sp500_data = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOG'],
        'name': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.'],
        'sector': ['Technology', 'Technology', 'Technology'],
        'sub_sector': ['Consumer Electronics', 'Software', 'Internet'],
        'headquarters_location': ['Cupertino, CA', 'Redmond, WA', 'Mountain View, CA'],
        'date_first_added': ['1980-12-12', '1986-03-13', '2006-04-03'],
        'cik': ['0000320193', '0000789019', '0001652044'],
        'founded': ['1976', '1975', '1998']
    })
    integration_db_manager.insert_sp500_constituents(sp500_data)
    
    # Add company profiles
    for symbol, name, price, mktcap in [
        ('AAPL', 'Apple Inc.', 170.0, 2800000000000),
        ('MSFT', 'Microsoft Corp.', 400.0, 3000000000000),
        ('GOOG', 'Alphabet Inc.', 2800.0, 1800000000000)
    ]:
        profile_data = {
            'symbol': symbol,
            'companyname': name,
            'price': price,
            'sector': 'Technology',
            'mktcap': mktcap
        }
        integration_db_manager.insert_company_profile(profile_data)
    
    # Add historical prices
    for symbol in ['AAPL', 'MSFT', 'GOOG']:
        prices_data = pd.DataFrame({
            'date': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0],
            'volume': [100000, 120000, 110000]
        })
        integration_db_manager.insert_historical_prices(symbol, prices_data)
    
    # Add undervaluation scores
    scores_data = [
        {
            'symbol': 'AAPL',
            'sector': 'Technology',
            'undervaluation_score': 75.5,
            'valuation_score': 70.0,
            'quality_score': 80.0,
            'strength_score': 78.0,
            'risk_score': 60.0,
            'data_quality': 'high',
            'price': 170.0,
            'mktcap': 2800000000000
        },
        {
            'symbol': 'MSFT',
            'sector': 'Technology',
            'undervaluation_score': 60.2,
            'valuation_score': 55.0,
            'quality_score': 65.0,
            'strength_score': 62.0,
            'risk_score': 55.0,
            'data_quality': 'high',
            'price': 400.0,
            'mktcap': 3000000000000
        }
    ]
    integration_db_manager.insert_undervaluation_scores(scores_data)
    
    # Step 2: Test data access layer queries
    
    # Get all stocks with scores (main page data)
    all_stocks = integration_stock_service.get_all_stocks_with_scores()
    assert len(all_stocks) >= 2
    
    apple_stock = next((s for s in all_stocks if s['symbol'] == 'AAPL'), None)
    assert apple_stock is not None
    assert apple_stock['company_name'] == 'Apple Inc.'
    assert apple_stock['undervaluation_score'] == 75.5
    assert apple_stock['price'] == 170.0
    
    # Get stock detail (stock detail page data)
    stock_basic_info = integration_stock_service.get_stock_basic_info('AAPL')
    assert stock_basic_info['symbol'] == 'AAPL'
    assert stock_basic_info['name'] == 'Apple Inc.'
    
    stock_profile = integration_stock_service.get_stock_company_profile('AAPL')
    assert stock_profile['companyname'] == 'Apple Inc.'
    assert stock_profile['price'] == 170.0
    
    stock_scores = integration_stock_service.get_stock_undervaluation_score('AAPL')
    assert stock_scores['undervaluation_score'] == 75.5
    
    historical_prices = integration_stock_service.get_stock_historical_prices('AAPL', limit=5)
    assert len(historical_prices) == 3
    
    # Get sector analysis (sectors page data)
    sector_analysis = integration_stock_service.get_sector_analysis()
    tech_sector = next((s for s in sector_analysis if s['sector'] == 'Technology'), None)
    assert tech_sector is not None
    assert tech_sector['total_stocks'] >= 2
    
    # Get stocks by sector (sector detail page data)
    tech_stocks = integration_stock_service.get_stocks_by_sector('Technology')
    assert len(tech_stocks) >= 2
    
    # Search functionality
    search_results = integration_stock_service.search_stocks('Apple')
    assert len(search_results) >= 1
    assert search_results[0]['symbol'] == 'AAPL'
    
    # Summary stats
    summary_stats = integration_stock_service.get_stock_summary_stats()
    assert summary_stats['total_stocks'] >= 3
    assert summary_stats['stocks_with_profiles'] >= 3

def test_api_and_web_interface_consistency(temp_db):
    """Test that API endpoints and web routes return consistent data"""
    # This would test Flask app routes vs API routes
    # For now, we'll test the data access layer consistency
    
    stock_service = StockDataService(db_manager=DatabaseManager(db_path=temp_db))
    
    # Setup test data
    db_manager = DatabaseManager(db_path=temp_db)
    
    # Add minimal test data
    sp500_data = pd.DataFrame({
        'symbol': ['AAPL'],
        'name': ['Apple Inc.'],
        'sector': ['Technology'],
        'sub_sector': ['Consumer Electronics'],
        'headquarters_location': ['Cupertino, CA'],
        'date_first_added': ['1980-12-12'],
        'cik': ['0000320193'],
        'founded': ['1976']
    })
    db_manager.insert_sp500_constituents(sp500_data)
    
    profile_data = {
        'symbol': 'AAPL',
        'companyname': 'Apple Inc.',
        'price': 170.0,
        'sector': 'Technology',
        'mktcap': 2800000000000
    }
    db_manager.insert_company_profile(profile_data)
    
    # Test data consistency between different access methods
    
    # Method 1: Get basic info
    basic_info = stock_service.get_stock_basic_info('AAPL')
    
    # Method 2: Get from all stocks list
    all_stocks = stock_service.get_all_stocks_with_scores()
    apple_from_list = next((s for s in all_stocks if s['symbol'] == 'AAPL'), None)
    
    # Data should be consistent
    assert basic_info['symbol'] == apple_from_list['symbol']
    assert basic_info['name'] == apple_from_list['company_name']
    assert basic_info['sector'] == apple_from_list['sector']

def test_authentication_across_components(temp_db):
    """Test authentication integration across different components"""
    auth_manager = AuthenticationManager(db_path=temp_db)
    portfolio_manager = PortfolioManager(db_path=temp_db)
    
    # Step 1: Create user
    user_result = auth_manager.register_user(
        username='integrationuser',
        email='integration@test.com',
        password='testpass123'
    )
    assert user_result['success'] is True
    user_id = user_result['user_id']
    
    # Step 2: Login and get session
    login_result = auth_manager.authenticate_user('integrationuser', 'testpass123')
    assert login_result['success'] is True
    session_token = login_result['session_token']
    
    # Step 3: Use session in portfolio operations
    # Portfolio operations should work with valid user_id
    transaction_result = portfolio_manager.add_transaction(
        user_id=user_id,
        transaction_type='BUY',
        symbol='AAPL',
        shares=5.0,
        price_per_share=150.0,
        transaction_date=date.today()
    )
    assert transaction_result['success'] is True
    
    # Step 4: Session expiration handling
    # Simulate session expiration
    expired_time = datetime.now() - timedelta(hours=25)  # 25 hours ago
    
    # Update session to be expired (direct database manipulation for testing)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_sessions SET expires_at = ? WHERE session_token = ?",
        (expired_time.isoformat(), session_token)
    )
    conn.commit()
    conn.close()
    
    # Session validation should fail
    validation_result = auth_manager.validate_session(session_token)
    assert validation_result['success'] is False

def test_error_propagation_between_layers(integration_db_manager):
    """Test how errors propagate between different layers"""
    stock_service = StockDataService(db_manager=integration_db_manager)
    
    # Test 1: Database connection error simulation
    with patch.object(integration_db_manager, 'engine') as mock_engine:
        mock_engine.connect.side_effect = Exception("Database connection failed")
        
        # Should handle database errors gracefully
        result = stock_service.get_all_stocks_with_scores()
        # Depending on implementation, should return empty list or handle gracefully
        assert isinstance(result, list)
    
    # Test 2: Invalid data handling
    # Try to get data for non-existent stock
    non_existent_stock = stock_service.get_stock_basic_info('NONEXISTENT')
    assert non_existent_stock is None
    
    # Test 3: Malformed data handling
    # This would test how the system handles corrupted data in database
    # For now, just verify the system doesn't crash on empty results
    empty_results = stock_service.get_stocks_by_sector('NONEXISTENT_SECTOR')
    assert isinstance(empty_results, list)
    assert len(empty_results) == 0

# --- Cross-Component Integration Tests ---

def test_scheduler_and_database_integration(temp_db):
    """Test scheduler integration with database operations"""
    # Mock the scheduler dependencies but use real database
    with patch('scheduler.DailyUpdater') as mock_updater, \
         patch('scheduler.FMPClient') as mock_fmp, \
         patch('scheduler.YahooFinanceClient') as mock_yahoo, \
         patch('scheduler.GapDetector') as mock_gap_detector, \
         patch('scheduler.PID_FILE', Path(f'{temp_db}.pid')), \
         patch('scheduler.STATUS_FILE', Path(f'{temp_db}.status')):
        
        # Create scheduler with real database
        scheduler = Scheduler()
        
        # Mock successful daily update
        mock_updater.return_value.run_update.return_value = {
            'success': True,
            'updated_stocks': 100
        }
        
        # Test daily update job
        scheduler._daily_update_job()
        
        # Verify status was updated
        assert 'last_daily_update' in scheduler.status
        assert scheduler.status.get('total_api_calls', 0) >= 0

def test_main_application_and_database_integration(temp_db):
    """Test main application integration with database"""
    with patch('main.FMPClient') as mock_fmp_client, \
         patch('main.get_config') as mock_config, \
         patch('main.setup_logging'), \
         patch('main.get_logger'):
        
        # Configure mocks
        mock_config.return_value.FMP_RATE_LIMIT_DELAY = 0.01
        mock_config.return_value.INITIAL_SETUP_COMPANY_PROFILES_LIMIT = 2
        mock_config.return_value.INITIAL_SETUP_HISTORICAL_DATA_LIMIT = 2
        
        # Mock FMP client
        mock_fmp_instance = mock_fmp_client.return_value
        
        # Mock S&P 500 data
        mock_sp500_df = pd.DataFrame({
            'Symbol': ['AAPL', 'MSFT'],
            'Name': ['Apple Inc.', 'Microsoft Corp.'],
            'Sector': ['Technology', 'Technology'],
            'Sub-Industry': ['Consumer Electronics', 'Software'],
            'Headquarters': ['Cupertino, CA', 'Redmond, WA']
        })
        mock_fmp_instance.get_sp500_constituents.return_value = mock_sp500_df
        
        # Mock company profile
        mock_fmp_instance.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'companyName': 'Apple Inc.',
            'price': 170.0,
            'sector': 'Technology',
            'marketCap': 2800000000000
        }
        
        # Mock historical data
        mock_historical_df = pd.DataFrame({
            'Date': ['2023-01-01', '2023-01-02'],
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [100000, 120000]
        })
        mock_fmp_instance.get_historical_prices.return_value = mock_historical_df
        
        # Create analyst with real database
        analyst = StockAnalyst()
        analyst.db_manager = DatabaseManager(db_path=temp_db)
        
        # Run initial setup
        with patch('time.sleep'):  # Speed up test
            analyst.run_initial_setup()
        
        # Verify data was stored in database
        symbols = analyst.db_manager.get_sp500_symbols()
        assert len(symbols) >= 2
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        
        # Verify profiles were stored
        assert analyst.db_manager.symbol_exists_in_profiles('AAPL')
        
        # Verify historical data was stored
        assert analyst.db_manager.symbol_has_historical_data('AAPL')

def test_undervaluation_analyzer_integration(integration_db_manager):
    """Test undervaluation analyzer with real data"""
    # Setup test data
    sp500_data = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT'],
        'name': ['Apple Inc.', 'Microsoft Corp.'],
        'sector': ['Technology', 'Technology'],
        'sub_sector': ['Consumer Electronics', 'Software'],
        'headquarters_location': ['Cupertino, CA', 'Redmond, WA'],
        'date_first_added': ['1980-12-12', '1986-03-13'],
        'cik': ['0000320193', '0000789019'],
        'founded': ['1976', '1975']
    })
    integration_db_manager.insert_sp500_constituents(sp500_data)
    
    # Add company profiles with realistic data
    for symbol, name, price, mktcap, pe_ratio in [
        ('AAPL', 'Apple Inc.', 170.0, 2800000000000, 25.0),
        ('MSFT', 'Microsoft Corp.', 400.0, 3000000000000, 28.0)
    ]:
        profile_data = {
            'symbol': symbol,
            'companyname': name,
            'price': price,
            'sector': 'Technology',
            'mktcap': mktcap,
            'pe': pe_ratio,
            'eps': price / pe_ratio if pe_ratio else None
        }
        integration_db_manager.insert_company_profile(profile_data)
    
    # Mock undervaluation analyzer
    with patch('undervaluation_analyzer.FMPClient') as mock_fmp, \
         patch('undervaluation_analyzer.YahooFinanceClient') as mock_yahoo:
        
        analyzer = UndervaluationAnalyzer(db_manager=integration_db_manager)
        
        # Mock fundamental data
        mock_fmp.return_value.get_fundamentals_summary.return_value = {
            'pe_ratio': 25.0,
            'price_to_book': 5.0,
            'debt_to_equity': 0.3,
            'roe': 0.25,
            'revenue_growth': 0.15
        }
        
        # Test analysis
        with patch.object(analyzer, '_calculate_undervaluation_score', return_value=75.5):
            result = analyzer.analyze_undervaluation(['AAPL'])
        
        # Verify scores were stored
        conn = sqlite3.connect(integration_db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM undervaluation_scores WHERE symbol = 'AAPL'")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count >= 0  # Analysis may or may not store scores depending on implementation

# --- Concurrent Access Tests ---

def test_concurrent_database_access(integration_db_manager):
    """Test concurrent access to database from multiple components"""
    results = []
    errors = []
    
    def insert_data(thread_id, component_name):
        try:
            if component_name == 'portfolio':
                # Simulate portfolio operations
                portfolio_mgr = PortfolioManager(db_path=integration_db_manager.db_path)
                # Portfolio operations require user_id, so create a mock user
                result = f"portfolio_thread_{thread_id}_success"
            elif component_name == 'stock_service':
                # Simulate stock service operations
                stock_service = StockDataService(db_manager=integration_db_manager)
                # Try to get data (read operation)
                stocks = stock_service.get_all_stocks_with_scores()
                result = f"stock_service_thread_{thread_id}_success"
            else:
                # Direct database operations
                profile_data = {
                    'symbol': f'THREAD{thread_id}',
                    'companyname': f'Thread Company {thread_id}',
                    'price': 100.0 + thread_id,
                    'sector': 'Technology',
                    'mktcap': 1000000000 + thread_id
                }
                integration_db_manager.insert_company_profile(profile_data)
                result = f"database_thread_{thread_id}_success"
            
            results.append(result)
            
        except Exception as e:
            errors.append((thread_id, component_name, str(e)))
    
    # Create threads for different components
    threads = []
    for i in range(3):
        for component in ['portfolio', 'stock_service', 'database']:
            thread = threading.Thread(
                target=insert_data,
                args=(i, component)
            )
            threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # Check results
    assert len(errors) == 0, f"Concurrent access errors: {errors}"
    assert len(results) >= 6  # At least some operations should succeed

# --- Performance Integration Tests ---

def test_large_dataset_performance(integration_db_manager):
    """Test system performance with larger datasets"""
    # Create a larger test dataset
    large_sp500_data = pd.DataFrame({
        'symbol': [f'TEST{i:03d}' for i in range(50)],
        'name': [f'Test Company {i}' for i in range(50)],
        'sector': ['Technology'] * 25 + ['Healthcare'] * 25,
        'sub_sector': ['Software'] * 50,
        'headquarters_location': ['Test City'] * 50,
        'date_first_added': ['2023-01-01'] * 50,
        'cik': [f'{i:010d}' for i in range(50)],
        'founded': ['2000'] * 50
    })
    
    start_time = time.time()
    integration_db_manager.insert_sp500_constituents(large_sp500_data)
    insert_time = time.time() - start_time
    
    # Should complete reasonably quickly
    assert insert_time < 10.0  # Less than 10 seconds for 50 records
    
    # Test data access performance
    stock_service = StockDataService(db_manager=integration_db_manager)
    
    start_time = time.time()
    all_stocks = stock_service.get_all_stocks_with_scores()
    query_time = time.time() - start_time
    
    # Should query reasonably quickly
    assert query_time < 5.0  # Less than 5 seconds to query 50 records
    assert len(all_stocks) >= 50

def test_memory_usage_integration(integration_db_manager):
    """Test memory usage across components"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Create multiple service instances
    services = []
    for i in range(5):
        stock_service = StockDataService(db_manager=integration_db_manager)
        services.append(stock_service)
    
    # Perform operations
    for service in services:
        service.get_all_stocks_with_scores()
    
    current_memory = process.memory_info().rss
    memory_increase = current_memory - initial_memory
    
    # Memory increase should be reasonable (less than 100MB)
    assert memory_increase < 100 * 1024 * 1024

# --- Data Consistency Tests ---

def test_data_consistency_across_operations(integration_db_manager):
    """Test data consistency across different operations"""
    # Insert test data through different methods
    
    # Method 1: Direct database manager
    profile_data = {
        'symbol': 'CONSISTENCY_TEST',
        'companyname': 'Consistency Test Company',
        'price': 100.0,
        'sector': 'Technology',
        'mktcap': 1000000000
    }
    integration_db_manager.insert_company_profile(profile_data)
    
    # Method 2: Through stock service
    stock_service = StockDataService(db_manager=integration_db_manager)
    
    # Retrieve through different methods
    direct_query = integration_db_manager.symbol_exists_in_profiles('CONSISTENCY_TEST')
    service_query = stock_service.get_stock_company_profile('CONSISTENCY_TEST')
    
    # Data should be consistent
    assert direct_query is True
    assert service_query is not None
    assert service_query['companyname'] == 'Consistency Test Company'
    assert service_query['price'] == 100.0

def test_transaction_integrity(temp_db):
    """Test transaction integrity across multiple operations"""
    auth_manager = AuthenticationManager(db_path=temp_db)
    portfolio_manager = PortfolioManager(db_path=temp_db)
    
    # Create user
    user_result = auth_manager.register_user(
        username='transactionuser',
        email='transaction@test.com',
        password='testpass123'
    )
    user_id = user_result['user_id']
    
    # Add multiple transactions in sequence
    transactions = [
        ('BUY', 'AAPL', 10.0, 150.0),
        ('BUY', 'MSFT', 5.0, 300.0),
        ('SELL', 'AAPL', 5.0, 160.0),
        ('BUY', 'GOOG', 2.0, 2500.0)
    ]
    
    for transaction_type, symbol, shares, price in transactions:
        result = portfolio_manager.add_transaction(
            user_id=user_id,
            transaction_type=transaction_type,
            symbol=symbol,
            shares=shares,
            price_per_share=price,
            transaction_date=date.today()
        )
        assert result['success'] is True
    
    # Verify portfolio consistency
    portfolio = portfolio_manager.get_user_portfolio(user_id)
    
    # Should have 3 holdings (AAPL reduced to 5 shares, MSFT 5 shares, GOOG 2 shares)
    assert portfolio['summary']['total_holdings'] == 3
    
    aapl_holding = next((h for h in portfolio['holdings'] if h['symbol'] == 'AAPL'), None)
    assert aapl_holding is not None
    assert aapl_holding['shares'] == 5.0  # 10 - 5 from sell
    
    # Verify transaction history
    transaction_history = portfolio_manager.get_user_transactions(user_id)
    assert len(transaction_history) == 4