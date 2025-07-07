"""
Global pytest configuration and fixtures for the Stock Analyst application.
This file provides common fixtures and configuration for all tests.
"""

import pytest
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, date, timedelta

# --- Global Environment Setup ---

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Set up global test environment variables"""
    test_env = {
        'DATABASE_PATH': ':memory:',
        'FMP_API_KEY': 'test_fmp_key',
        'SECRET_KEY': 'test-secret-key-for-testing',
        'LOG_LEVEL': 'ERROR',  # Reduce logging noise in tests
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        yield

# --- Database Fixtures ---

@pytest.fixture
def temp_database():
    """Create a temporary database file for tests that need persistence"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass

@pytest.fixture
def in_memory_database():
    """Create an in-memory database for fast tests"""
    return ":memory:"

@pytest.fixture
def populated_database(temp_database):
    """Create a database with sample test data"""
    from database import DatabaseManager
    
    db_manager = DatabaseManager(db_path=temp_database)
    
    # Add sample S&P 500 data
    sp500_data = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA'],
        'name': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Amazon.com Inc.', 'Tesla Inc.'],
        'sector': ['Technology', 'Technology', 'Technology', 'Consumer Discretionary', 'Consumer Discretionary'],
        'sub_sector': ['Consumer Electronics', 'Software', 'Internet', 'Internet Retail', 'Automobiles'],
        'headquarters_location': ['Cupertino, CA', 'Redmond, WA', 'Mountain View, CA', 'Seattle, WA', 'Austin, TX'],
        'date_first_added': ['1980-12-12', '1986-03-13', '2006-04-03', '2005-05-26', '2020-12-21'],
        'cik': ['0000320193', '0000789019', '0001652044', '0001018724', '0001318605'],
        'founded': ['1976', '1975', '1998', '1994', '2003']
    })
    db_manager.insert_sp500_constituents(sp500_data)
    
    # Add company profiles
    companies = [
        ('AAPL', 'Apple Inc.', 170.0, 'Technology', 2800000000000),
        ('MSFT', 'Microsoft Corp.', 400.0, 'Technology', 3000000000000),
        ('GOOG', 'Alphabet Inc.', 2800.0, 'Technology', 1800000000000),
        ('AMZN', 'Amazon.com Inc.', 3200.0, 'Consumer Discretionary', 1600000000000),
        ('TSLA', 'Tesla Inc.', 250.0, 'Consumer Discretionary', 800000000000)
    ]
    
    for symbol, name, price, sector, mktcap in companies:
        profile_data = {
            'symbol': symbol,
            'companyname': name,
            'price': price,
            'sector': sector,
            'mktcap': mktcap
        }
        db_manager.insert_company_profile(profile_data)
    
    # Add historical prices for each symbol
    for symbol in ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA']:
        prices_data = pd.DataFrame({
            'date': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'],
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [102.0, 103.0, 104.0, 105.0, 106.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0],
            'volume': [100000, 120000, 110000, 130000, 125000]
        })
        db_manager.insert_historical_prices(symbol, prices_data)
    
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
    db_manager.insert_undervaluation_scores(scores_data)
    
    yield temp_database, db_manager

# --- Authentication Fixtures ---

@pytest.fixture
def test_user_data():
    """Standard test user data"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'securepassword123'
    }

@pytest.fixture
def authenticated_user(temp_database, test_user_data):
    """Create and authenticate a test user"""
    from auth import AuthenticationManager
    
    auth_manager = AuthenticationManager(db_path=temp_database)
    
    # Register user
    registration_result = auth_manager.register_user(
        username=test_user_data['username'],
        email=test_user_data['email'],
        password=test_user_data['password']
    )
    
    # Authenticate user
    login_result = auth_manager.authenticate_user(
        username=test_user_data['username'],
        password=test_user_data['password']
    )
    
    yield {
        'user_id': registration_result['user_id'],
        'username': test_user_data['username'],
        'email': test_user_data['email'],
        'session_token': login_result['session_token'],
        'auth_manager': auth_manager
    }

# --- API Mock Fixtures ---

@pytest.fixture
def mock_fmp_client():
    """Mock FMP client with realistic responses"""
    with patch('fmp_client.FMPClient') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Mock S&P 500 constituents
        mock_sp500_df = pd.DataFrame({
            'Symbol': ['AAPL', 'MSFT'],
            'Name': ['Apple Inc.', 'Microsoft Corp.'],
            'Sector': ['Technology', 'Technology']
        })
        mock_instance.get_sp500_constituents.return_value = mock_sp500_df
        
        # Mock company profile
        mock_instance.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'companyName': 'Apple Inc.',
            'price': 170.0,
            'sector': 'Technology',
            'marketCap': 2800000000000
        }
        
        # Mock historical prices
        mock_historical_df = pd.DataFrame({
            'Date': ['2023-01-01', '2023-01-02'],
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [100000, 120000]
        })
        mock_instance.get_historical_prices.return_value = mock_historical_df
        
        # Mock fundamentals
        mock_instance.get_fundamentals_summary.return_value = {
            'pe_ratio': 25.0,
            'price_to_book': 5.0,
            'roe': 0.20,
            'debt_to_equity': 0.30
        }
        
        # Mock usage tracking
        mock_instance.get_usage_summary.return_value = {
            'used_today': 50,
            'remaining_today': 200,
            'percentage_used': 20.0
        }
        
        yield mock_instance

@pytest.fixture
def mock_yahoo_client():
    """Mock Yahoo Finance client with realistic responses"""
    with patch('yahoo_finance_client.YahooFinanceClient') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Mock quote data
        mock_instance.get_quote.return_value = {
            'symbol': 'AAPL',
            'price': 170.0,
            'market_cap': 2800000000000,
            'pe_ratio': 25.0,
            'source': 'yahoo_finance'
        }
        
        # Mock company profile
        mock_instance.get_company_profile.return_value = {
            'symbol': 'AAPL',
            'companyname': 'Apple Inc.',
            'sector': 'Technology',
            'description': 'Technology company',
            'source': 'yahoo_finance'
        }
        
        # Mock historical prices
        mock_historical_df = pd.DataFrame({
            'date': [date(2023, 1, 1), date(2023, 1, 2)],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [100000, 120000]
        })
        mock_instance.get_historical_prices.return_value = mock_historical_df
        
        # Mock availability
        mock_instance.is_available.return_value = True
        
        yield mock_instance

# --- Service Fixtures ---

@pytest.fixture
def stock_data_service(populated_database):
    """Create a StockDataService with populated database"""
    from data_access_layer import StockDataService
    
    db_path, db_manager = populated_database
    return StockDataService(db_manager=db_manager)

@pytest.fixture
def portfolio_manager_with_user(temp_database, authenticated_user):
    """Create a PortfolioManager with an authenticated user"""
    from portfolio import PortfolioManager
    
    portfolio_manager = PortfolioManager(db_path=temp_database)
    
    # Add some sample transactions
    transactions = [
        ('BUY', 'AAPL', 10.0, 150.0, date(2023, 1, 1)),
        ('BUY', 'MSFT', 5.0, 300.0, date(2023, 1, 2)),
        ('SELL', 'AAPL', 2.0, 160.0, date(2023, 1, 3))
    ]
    
    for transaction_type, symbol, shares, price, transaction_date in transactions:
        portfolio_manager.add_transaction(
            user_id=authenticated_user['user_id'],
            transaction_type=transaction_type,
            symbol=symbol,
            shares=shares,
            price_per_share=price,
            transaction_date=transaction_date
        )
    
    yield portfolio_manager, authenticated_user

# --- Flask App Fixtures ---

@pytest.fixture
def flask_test_client():
    """Create Flask test client with mocked dependencies"""
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_PATH': ':memory:',
        'FMP_API_KEY': 'test_fmp_key',
        'TESTING': 'true'
    }):
        from app import app
        
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.test_client() as client:
            with app.app_context():
                yield client

# --- Temporary File Fixtures ---

@pytest.fixture
def temp_files():
    """Create temporary files for testing file operations"""
    files = {}
    
    # Create temporary files
    for name in ['pid', 'status', 'log', 'config']:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{name}') as f:
            files[name] = Path(f.name)
    
    yield files
    
    # Cleanup
    for file_path in files.values():
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass

# --- Performance Fixtures ---

@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
            return self
        
        def stop(self):
            self.end_time = time.time()
            return self
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
        
        def assert_under(self, max_seconds, message="Operation took too long"):
            assert self.elapsed < max_seconds, f"{message}: {self.elapsed:.2f}s > {max_seconds}s"
    
    return Timer()

# --- Test Data Fixtures ---

@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing"""
    return {
        'symbol': 'AAPL',
        'name': 'Apple Inc.',
        'sector': 'Technology',
        'price': 170.0,
        'market_cap': 2800000000000,
        'pe_ratio': 25.0,
        'historical_prices': [
            {'date': '2023-01-01', 'close': 170.0},
            {'date': '2023-01-02', 'close': 171.0},
            {'date': '2023-01-03', 'close': 169.0}
        ]
    }

@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing"""
    return {
        'holdings': [
            {'symbol': 'AAPL', 'shares': 10, 'avg_price': 150.0},
            {'symbol': 'MSFT', 'shares': 5, 'avg_price': 300.0}
        ],
        'transactions': [
            {'type': 'BUY', 'symbol': 'AAPL', 'shares': 10, 'price': 150.0, 'date': '2023-01-01'},
            {'type': 'BUY', 'symbol': 'MSFT', 'shares': 5, 'price': 300.0, 'date': '2023-01-02'}
        ]
    }

# --- Utility Fixtures ---

@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing"""
    fixed_datetime = datetime(2023, 7, 1, 12, 0, 0)
    fixed_date = date(2023, 7, 1)
    
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_datetime
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        with patch('datetime.date') as mock_d:
            mock_d.today.return_value = fixed_date
            mock_d.side_effect = lambda *args, **kw: date(*args, **kw)
            
            yield fixed_datetime, fixed_date

# --- Pytest Hooks ---

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Add custom markers
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "external: mark test as requiring external services")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file names"""
    for item in items:
        # Auto-mark tests based on file names
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        if "external" in item.nodeid:
            item.add_marker(pytest.mark.external)

def pytest_runtest_setup(item):
    """Setup before each test"""
    # Skip external tests if running in CI without network access
    if "external" in item.keywords and os.environ.get("SKIP_EXTERNAL_TESTS"):
        pytest.skip("Skipping external test in CI environment")

def pytest_runtest_teardown(item):
    """Cleanup after each test"""
    # Could add cleanup logic here if needed
    pass