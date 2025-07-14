import pytest
import pandas as pd
import os
from unittest.mock import patch
from sqlalchemy import text

# Mock environment variables before importing DatabaseManager
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {}):
        yield

from database import DatabaseManager

@pytest.fixture
def db_manager():
    # Use test database for testing
    with patch.dict(os.environ, {
        'TESTING': 'true',
        'POSTGRES_HOST': 'test-postgres',
        'POSTGRES_DB': 'stockanalyst_test'
    }):
        manager = DatabaseManager()
        yield manager
        manager.cleanup_connections()

def test_create_tables(db_manager):
    """Test that all required tables are created"""
    with db_manager.engine.connect() as conn:
        tables = [
            'sp500_constituents',
            'company_profiles',
            'historical_prices',
            'undervaluation_scores'
        ]
        
        for table in tables:
            result = conn.execute(text(f"SELECT table_name FROM information_schema.tables WHERE table_name='{table}';"))
            assert result.fetchone() is not None, f"Table {table} was not created"

def test_insert_sp500_constituents(db_manager):
    """Test inserting S&P 500 constituents"""
    data = {
        'symbol': ['AAPL', 'MSFT'],
        'name': ['Apple Inc.', 'Microsoft Corp.'],
        'sector': ['Technology', 'Technology'],
        'sub_sector': ['Consumer Electronics', 'Software'],
        'headquarters_location': ['Cupertino, California', 'Redmond, Washington'],
        'date_first_added': ['1980-12-12', '1986-03-13'],
        'cik': ['0000320193', '0000789019'],
        'founded': ['1976', '1975']
    }
    df = pd.DataFrame(data)
    
    db_manager.insert_sp500_constituents(df)
    
    with db_manager.engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM sp500_constituents"))
        assert result.fetchone()[0] == 2
        
        result = conn.execute(text("SELECT name FROM sp500_constituents WHERE symbol = 'AAPL'"))
        assert result.fetchone()[0] == 'Apple Inc.'

def test_insert_company_profile(db_manager):
    """Test inserting company profile"""
    profile_data = {
        'symbol': 'SIMPLE',  # Use a unique symbol
        'companyname': 'Simple Test Corp',
        'price': 77.89,
        'sector': 'Technology',
        'mktcap': 9876543210
    }
    
    # Get initial count
    with db_manager.engine.connect() as conn:
        initial_result = conn.execute(text("SELECT COUNT(*) FROM company_profiles"))
        initial_count = initial_result.fetchone()[0]
    
    # Insert the profile
    db_manager.insert_company_profile(profile_data)
    
    with db_manager.engine.connect() as conn:
        # Check that count increased by 1 (new record)
        result = conn.execute(text("SELECT COUNT(*) FROM company_profiles"))
        assert result.fetchone()[0] == initial_count + 1
        
        # Check that the specific record was inserted correctly
        result = conn.execute(text("SELECT companyname FROM company_profiles WHERE symbol = 'SIMPLE'"))
        assert result.fetchone()[0] == 'Simple Test Corp'

def test_get_sp500_symbols(db_manager):
    """Test getting S&P 500 symbols"""
    data = {
        'symbol': ['AAPL', 'MSFT'],
        'name': ['Apple Inc.', 'Microsoft Corp.'],
        'sector': ['Technology', 'Technology'],
        'sub_sector': ['Consumer Electronics', 'Software'],
        'headquarters_location': ['Cupertino, California', 'Redmond, Washington'],
        'date_first_added': ['1980-12-12', '1986-03-13'],
        'cik': ['0000320193', '0000789019'],
        'founded': ['1976', '1975']
    }
    df = pd.DataFrame(data)
    db_manager.insert_sp500_constituents(df)

    symbols = db_manager.get_sp500_symbols()
    assert sorted(symbols) == ['AAPL', 'MSFT']

def test_symbol_exists_in_profiles(db_manager):
    """Test checking if symbol exists in profiles"""
    profile_data = {
        'symbol': 'GOOG',
        'companyname': 'Alphabet Inc.',
        'price': 150.0,
        'sector': 'Technology',
        'mktcap': 1000000000000
    }
    db_manager.insert_company_profile(profile_data)

    assert db_manager.symbol_exists_in_profiles('GOOG')
    assert not db_manager.symbol_exists_in_profiles('NONEXISTENT')