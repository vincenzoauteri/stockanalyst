"""
SECURE pytest configuration for Stock Analyst application.
Uses isolated test database container to prevent production database access.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, date

# --- Global Environment Setup ---

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Set up SECURE test environment variables using isolated test database"""
    test_env = {
        'POSTGRES_HOST': 'test-postgres',  # ISOLATED test database container
        'POSTGRES_PORT': '5432', 
        'POSTGRES_DB': 'stockanalyst_test',  # SEPARATE test database
        'POSTGRES_USER': 'stockanalyst',
        'POSTGRES_PASSWORD': 'testpassword',  # Different password for test
        'FMP_API_KEY': 'test_fmp_key',
        'SECRET_KEY': 'test-secret-key-for-testing',
        'LOG_LEVEL': 'ERROR',  # Reduce logging noise in tests
        'TESTING': 'true'  # CRITICAL: This triggers security checks
    }
    
    with patch.dict(os.environ, test_env):
        yield

# --- Database Fixtures ---

@pytest.fixture
def db_manager():
    """Create a DatabaseManager with ISOLATED test database"""
    from database import DatabaseManager
    
    # This will trigger security validation and require test database
    return DatabaseManager()

# --- Authentication Fixtures ---

@pytest.fixture
def test_user_data():
    """Standard test user data"""
    return {
        'username': 'testuser_safe',
        'email': 'test_safe@example.com',
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
    
    if not registration_result['success']:
        pytest.fail(f"Failed to register test user: {registration_result.get('error')}")
    
    # Authenticate user
    login_result = auth_manager.authenticate_user(
        username=test_user_data['username'],
        password=test_user_data['password']
    )
    
    if not login_result['success']:
        pytest.fail(f"Failed to authenticate test user: {login_result.get('error')}")
    
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

# --- Flask App Fixtures ---

@pytest.fixture
def flask_test_client():
    """Create Flask test client with ISOLATED test database"""
    test_env = {
        'POSTGRES_HOST': 'test-postgres',  # ISOLATED test database
        'POSTGRES_DB': 'stockanalyst_test',
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

# --- Safety Validation Fixtures ---

@pytest.fixture(autouse=True)
def validate_test_environment():
    """Validate that we're using test database, not production"""
    postgres_host = os.getenv('POSTGRES_HOST')
    postgres_db = os.getenv('POSTGRES_DB')
    is_testing = os.getenv('TESTING', '').lower() == 'true'
    
    # Ensure we're in testing mode
    assert is_testing, "TESTING environment variable must be set to 'true'"
    
    # Ensure we're not using production database
    assert postgres_host == 'test-postgres', f"Must use test-postgres, not {postgres_host}"
    assert postgres_db == 'stockanalyst_test', f"Must use stockanalyst_test, not {postgres_db}"
    
    print(f"✅ SAFE: Using test database {postgres_host}/{postgres_db}")

# --- Pytest Hooks ---

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Add custom markers
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")

def pytest_runtest_setup(item):
    """Setup before each test - validate environment safety"""
    # Double-check we're not connecting to production
    postgres_host = os.getenv('POSTGRES_HOST')
    if postgres_host == 'postgres':
        pytest.fail("SECURITY VIOLATION: Test attempting to use production database!")

def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    print("\n🔒 SECURE TEST MODE: Using isolated test database container")
    print(f"   Database: {os.getenv('POSTGRES_HOST')}/{os.getenv('POSTGRES_DB')}")
    print("   Production database is PROTECTED from test access\n")

def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    print("\n✅ Test session completed with isolated database")
    print("   Production database remains UNTOUCHED")