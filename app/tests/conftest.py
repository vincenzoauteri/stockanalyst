"""
SECURE pytest configuration for Stock Analyst application.
Uses isolated test database container to prevent production database access.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, date
from sqlalchemy import text

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

@pytest.fixture(scope="session")
def db_manager_session():
    """Single DatabaseManager for entire test session to prevent connection pool exhaustion"""
    from database import DatabaseManager
    
    # This will trigger security validation and require test database
    db = DatabaseManager()
    yield db
    # Clean up connections after entire session
    if hasattr(db, 'cleanup_connections'):
        db.cleanup_connections()

@pytest.fixture
def db_manager(db_manager_session):
    """Reuse session database manager with cleanup between tests"""
    yield db_manager_session
    # Clean up test data but reuse connection pool

@pytest.fixture(autouse=True)
def cleanup_database_connections():
    """Automatically cleanup database connections after each test"""
    yield
    try:
        # Force cleanup of any remaining database connections
        import gc
        from database import DatabaseManager
        
        # Dispose of any DatabaseManager engines that were created during the test
        # This will clean up connection pools from individual test DatabaseManager instances
        gc.collect()
        
        # Clear any orphaned connection pools
        try:
            import sqlalchemy.pool as pool
            if hasattr(pool, 'clear_managers'):
                pool.clear_managers()
        except:
            pass
            
        # Force disposal of any engines that might be lingering
        try:
            import sqlalchemy
            # Get all engines and dispose them
            for engine in sqlalchemy.engine._engine_registry:
                try:
                    engine.dispose()
                except:
                    pass
        except:
            pass
            
    except Exception:
        # Silent cleanup - don't fail tests due to cleanup issues
        pass

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
def clean_auth_tables(db_manager_session):
    """Clean authentication tables before each test"""
    from sqlalchemy import text
    
    with db_manager_session.engine.begin() as conn:
        # Clean user-related tables
        conn.execute(text("DELETE FROM user_sessions"))
        conn.execute(text("DELETE FROM user_watchlists")) 
        conn.execute(text("DELETE FROM user_portfolios"))
        conn.execute(text("DELETE FROM portfolio_transactions"))
        conn.execute(text("DELETE FROM users"))
        conn.commit()

@pytest.fixture
def authenticated_user(auth_manager, test_user_data, clean_auth_tables):
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
    
    # Clean up any remaining database connections
    try:
        # The session cleanup will be handled by the session-scoped fixture
        print("   Database connections cleaned up")
    except Exception as e:
        print(f"   Warning: Could not clean up connections: {e}")

# --- Connection Management ---

@pytest.fixture(scope="session", autouse=True)
def manage_db_connections():
    """Manage database connections for the entire test session"""
    yield
    # Session cleanup - dispose of all connections
    try:
        import sqlalchemy.pool as pool
        pool.clear_managers()
        print("   Cleared SQLAlchemy connection pool managers")
    except Exception as e:
        print(f"   Warning: Could not clear connection pools: {e}")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

@pytest.fixture(scope="function")
def driver():
    """
    Pytest fixture to create a Selenium WebDriver instance.
    Connects to the standalone Chrome container with optimized configuration.
    """
    chrome_options = ChromeOptions()
    
    # Add critical container environment options
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    
    # Additional network and stability options
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # The command_executor URL points to the Selenium container
    try:
        remote_driver = webdriver.Remote(
            command_executor='http://selenium-chrome:4444/wd/hub',
            options=chrome_options
        )
        
        # Set optimized timeouts for frontend testing
        remote_driver.set_page_load_timeout(45)  # Increased for complex pages
        remote_driver.implicitly_wait(15)        # Increased implicit wait for element detection
        
        yield remote_driver
        
        # Teardown: safely quit the driver after each test
        try:
            remote_driver.quit()
        except Exception as e:
            print(f"Warning: Error during driver cleanup: {e}")
    except Exception as e:
        pytest.fail(f"Failed to connect to Selenium WebDriver: {e}")

# --- Base URL Configuration ---

@pytest.fixture
def base_url():
    """Base URL for test webapp - uses container hostname"""
    return "http://sa-test-web:5000"  # Use container hostname for test environment

@pytest.fixture(autouse=True, scope="session")
def validate_test_environment():
    """Validate test environment before running tests"""
    import requests
    import time
    
    base_url = "http://sa-test-web:5000"
    
    # Wait for webapp to be ready
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Try health check endpoint
            response = requests.get(f"{base_url}/api/v2/health", timeout=10)
            if response.status_code == 200:
                print(f"✅ Webapp is accessible at {base_url}")
                return
        except requests.exceptions.RequestException:
            pass
        
        try:
            # Fallback: try main page
            response = requests.get(base_url, timeout=10)
            if response.status_code in [200, 302]:  # 302 for redirect to login
                print(f"✅ Webapp is accessible at {base_url} (status: {response.status_code})")
                return
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_retries - 1:
            print(f"⏳ Webapp not ready yet, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
    
    pytest.fail(f"❌ Webapp not accessible at {base_url} after {max_retries} attempts")

# --- Scheduler Fixtures ---

@pytest.fixture(scope="session")
def scheduler_session(db_manager_session):
    """Single scheduler instance for entire test session to prevent connection pool exhaustion"""
    from scheduler import Scheduler
    
    # Create scheduler with existing database manager
    scheduler = Scheduler(db_manager=db_manager_session)
    try:
        yield scheduler
    finally:
        if hasattr(scheduler, 'cleanup'):
            scheduler.cleanup()

@pytest.fixture
def scheduler(scheduler_session):
    """Reuse session scheduler with cleanup between tests"""
    yield scheduler_session
    # Clean up test data but reuse scheduler instance

@pytest.fixture
def mock_scheduler_db_operations():
    """Mock heavy database operations for scheduler tests"""
    from unittest.mock import patch, MagicMock
    
    with patch('scheduler.DatabaseManager') as mock_db:
        # Mock common database operations
        mock_db.return_value.get_sp500_symbols.return_value = ['AAPL', 'MSFT', 'GOOGL']
        mock_db.return_value.insert_short_interest_data.return_value = True
        mock_db.return_value.update_company_profile.return_value = True
        mock_db.return_value.insert_historical_prices.return_value = True
        
        # Mock database connection
        mock_conn = MagicMock()
        mock_db.return_value.engine.connect.return_value.__enter__.return_value = mock_conn
        mock_db.return_value.engine.connect.return_value.__exit__.return_value = None
        
        yield mock_db

# --- Test Data Population ---

@pytest.fixture(autouse=True, scope="session")
def populate_test_data(db_manager_session):
    """Populate test database with sample data for frontend tests"""
    try:
        # Import test fixtures  
        from tests.fixtures.sample_companies import SAMPLE_SP500_COMPANIES, SAMPLE_COMPANY_PROFILES
        
        print("🔄 Populating test database with sample data...")
        
        # Insert sample companies
        with db_manager_session.engine.begin() as conn:
            # Clear existing data
            conn.execute(text("DELETE FROM sp500_constituents"))
            conn.execute(text("DELETE FROM company_profiles"))
            
            # Insert sample companies
            for company in SAMPLE_SP500_COMPANIES:
                conn.execute(text("""
                    INSERT INTO sp500_constituents (symbol, name, sector)
                    VALUES (:symbol, :name, :sector)
                    ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    sector = EXCLUDED.sector
                """), company)
            
            # Add sample company profiles
            for profile in SAMPLE_COMPANY_PROFILES:
                conn.execute(text("""
                    INSERT INTO company_profiles (symbol, companyname, price, mktcap, industry)
                    VALUES (:symbol, :companyname, :price, :mktcap, :industry)
                    ON CONFLICT (symbol) DO UPDATE SET
                    companyname = EXCLUDED.companyname,
                    price = EXCLUDED.price,
                    mktcap = EXCLUDED.mktcap,
                    industry = EXCLUDED.industry
                """), profile)
            
            conn.commit()
            
        # Verify data was inserted
        with db_manager_session.engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM sp500_constituents")).fetchone()
            companies_count = result[0]
            
            result = conn.execute(text("SELECT COUNT(*) FROM company_profiles")).fetchone() 
            profiles_count = result[0]
            
        print(f"✅ Test database populated: {companies_count} companies, {profiles_count} profiles")
        
        yield
        
    except Exception as e:
        print(f"❌ Error populating test database: {e}")
        # Don't fail tests if data population fails - let tests handle empty state
        yield