"""
Global pytest configuration and fixtures for the Stock Analyst application.
PostgreSQL-only configuration for containerized environment.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, date

# --- Global Environment Setup ---

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Set up global test environment variables for PostgreSQL testing"""
    test_env = {
        'POSTGRES_HOST': 'postgres',
        'POSTGRES_PORT': '5432', 
        'POSTGRES_DB': 'stockanalyst',
        'POSTGRES_USER': 'stockanalyst',
        'POSTGRES_PASSWORD': 'defaultpassword',
        'FMP_API_KEY': 'test_fmp_key',
        'SECRET_KEY': 'test-secret-key-for-testing',
        'LOG_LEVEL': 'ERROR',  # Reduce logging noise in tests
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        yield

# --- Database Fixtures ---

@pytest.fixture
def db_manager():
    """Create a DatabaseManager with test database"""
    from database import DatabaseManager
    return DatabaseManager()

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
def auth_manager(db_manager):
    """Create AuthenticationManager with test database"""
    from auth import AuthenticationManager
    return AuthenticationManager(db_manager=db_manager)

@pytest.fixture
def authenticated_user(auth_manager, test_user_data):
    """Create and authenticate a test user"""
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

# --- Portfolio Fixtures ---

@pytest.fixture
def portfolio_manager(db_manager):
    """Create PortfolioManager with test database"""
    from portfolio import PortfolioManager
    return PortfolioManager(db_manager=db_manager)

@pytest.fixture
def portfolio_manager_with_user(portfolio_manager, authenticated_user):
    """Create a PortfolioManager with an authenticated user and sample transactions"""
    
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
        
        yield mock_instance

# --- Service Fixtures ---

@pytest.fixture
def stock_data_service(db_manager):
    """Create a StockDataService with test database"""
    from data_access_layer import StockDataService
    return StockDataService(db_manager=db_manager)

# --- Flask App Fixtures ---

@pytest.fixture
def flask_test_client():
    """Create Flask test client with PostgreSQL test database"""
    test_env = {
        'POSTGRES_HOST': 'postgres',
        'POSTGRES_DB': 'stockanalyst',
        'SECRET_KEY': 'test-secret-key',
        'FMP_API_KEY': 'test_fmp_key',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        from app import app
        
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.test_client() as client:
            with app.app_context():
                yield client

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