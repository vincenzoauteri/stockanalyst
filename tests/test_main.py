import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, call
import os

# Mock environment variables before importing main
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'DATABASE_PATH': ':memory:',
        'FMP_API_KEY': 'test_fmp_key'
    }):
        yield

# Mock all imports before importing main module
@pytest.fixture(autouse=True)
def mock_imports():
    with patch.multiple(
        'main',
        FMPClient=MagicMock(),
        DatabaseManager=MagicMock(),
        get_config=MagicMock(),
        setup_logging=MagicMock(),
        get_logger=MagicMock()
    ):
        yield

from main import StockAnalyst, main

@pytest.fixture
def mock_config():
    """Mock configuration object"""
    config = MagicMock()
    config.FMP_RATE_LIMIT_DELAY = 0.1  # Fast for testing
    config.INITIAL_SETUP_COMPANY_PROFILES_LIMIT = 5
    config.INITIAL_SETUP_HISTORICAL_DATA_LIMIT = 3
    return config

@pytest.fixture
def stock_analyst(mock_config):
    """Create StockAnalyst instance with mocked dependencies"""
    with patch('main.FMPClient') as mock_fmp_client, \
         patch('main.DatabaseManager') as mock_db_manager, \
         patch('main.get_config', return_value=mock_config), \
         patch('main.setup_logging'), \
         patch('main.get_logger'):
        
        analyst = StockAnalyst()
        
        # Configure mocks
        analyst.fmp_client = mock_fmp_client.return_value
        analyst.db_manager = mock_db_manager.return_value
        analyst.config = mock_config
        
        yield analyst

# --- StockAnalyst Class Tests ---

def test_stock_analyst_initialization():
    """Test StockAnalyst initialization"""
    with patch('main.FMPClient') as mock_fmp, \
         patch('main.DatabaseManager') as mock_db, \
         patch('main.get_config') as mock_config, \
         patch('main.setup_logging'), \
         patch('main.get_logger'):
        
        analyst = StockAnalyst()
        
        mock_fmp.assert_called_once()
        mock_db.assert_called_once()
        mock_config.assert_called_once()
        
        assert analyst.fmp_client is not None
        assert analyst.db_manager is not None
        assert analyst.config is not None

def test_fetch_and_store_sp500_constituents_success(stock_analyst):
    """Test successful S&P 500 constituents fetching"""
    # Mock data
    mock_df = pd.DataFrame({
        'Symbol': ['AAPL', 'MSFT'],
        'Name': ['Apple Inc.', 'Microsoft Corp.'],
        'Sector': ['Technology', 'Technology']
    })
    
    stock_analyst.fmp_client.get_sp500_constituents.return_value = mock_df
    
    result = stock_analyst.fetch_and_store_sp500_constituents()
    
    assert result is True
    stock_analyst.fmp_client.get_sp500_constituents.assert_called_once()
    stock_analyst.db_manager.insert_sp500_constituents.assert_called_once()
    
    # Check that column names were cleaned (lowercase, underscore)
    args = stock_analyst.db_manager.insert_sp500_constituents.call_args[0][0]
    assert 'symbol' in args.columns
    assert 'name' in args.columns

def test_fetch_and_store_sp500_constituents_failure(stock_analyst):
    """Test S&P 500 constituents fetching failure"""
    stock_analyst.fmp_client.get_sp500_constituents.return_value = pd.DataFrame()
    
    result = stock_analyst.fetch_and_store_sp500_constituents()
    
    assert result is False
    stock_analyst.db_manager.insert_sp500_constituents.assert_not_called()

def test_fetch_and_store_company_profiles_success(stock_analyst):
    """Test successful company profiles fetching"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT', 'GOOG']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    
    # Mock profile data
    mock_profile = {
        'symbol': 'AAPL',
        'companyName': 'Apple Inc.',
        'price': 170.0,
        'marketCap': 2800000000000
    }
    stock_analyst.fmp_client.get_company_profile.return_value = mock_profile
    
    with patch('time.sleep'):  # Mock sleep for faster test
        stock_analyst.fetch_and_store_company_profiles()
    
    # Should be called for each symbol
    assert stock_analyst.fmp_client.get_company_profile.call_count == 3
    assert stock_analyst.db_manager.insert_company_profile.call_count == 3
    
    # Check that profile data was cleaned (lowercase, underscore)
    args = stock_analyst.db_manager.insert_company_profile.call_args[0][0]
    assert 'companyname' in args  # Should be converted from 'companyName'

def test_fetch_and_store_company_profiles_with_limit(stock_analyst):
    """Test company profiles fetching with limit"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    stock_analyst.fmp_client.get_company_profile.return_value = {'symbol': 'AAPL'}
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_company_profiles(limit=2)
    
    # Should only be called for first 2 symbols
    assert stock_analyst.fmp_client.get_company_profile.call_count == 2

def test_fetch_and_store_company_profiles_skip_existing(stock_analyst):
    """Test company profiles fetching skips existing profiles"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
    stock_analyst.db_manager.symbol_exists_in_profiles.side_effect = [True, False]  # AAPL exists, MSFT doesn't
    stock_analyst.fmp_client.get_company_profile.return_value = {'symbol': 'MSFT'}
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_company_profiles()
    
    # Should only be called for MSFT (AAPL was skipped)
    stock_analyst.fmp_client.get_company_profile.assert_called_once_with('MSFT')

def test_fetch_and_store_company_profiles_no_data(stock_analyst):
    """Test company profiles fetching handles no data"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['INVALID']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    stock_analyst.fmp_client.get_company_profile.return_value = None
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_company_profiles()
    
    stock_analyst.fmp_client.get_company_profile.assert_called_once_with('INVALID')
    stock_analyst.db_manager.insert_company_profile.assert_not_called()

def test_fetch_and_store_historical_data_success(stock_analyst):
    """Test successful historical data fetching"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
    stock_analyst.db_manager.symbol_has_historical_data.return_value = False
    
    # Mock historical data
    mock_df = pd.DataFrame({
        'Date': ['2023-01-01', '2023-01-02'],
        'Open': [100.0, 101.0],
        'High': [102.0, 103.0],
        'Low': [99.0, 100.0],
        'Close': [101.0, 102.0],
        'Volume': [100000, 120000]
    })
    stock_analyst.fmp_client.get_historical_prices.return_value = mock_df
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_historical_data()
    
    assert stock_analyst.fmp_client.get_historical_prices.call_count == 2
    assert stock_analyst.db_manager.insert_historical_prices.call_count == 2
    
    # Check that column names were cleaned
    calls = stock_analyst.db_manager.insert_historical_prices.call_args_list
    for call in calls:
        symbol, df_arg = call[0]
        assert 'date' in df_arg.columns  # Should be lowercase

def test_fetch_and_store_historical_data_custom_symbols(stock_analyst):
    """Test historical data fetching with custom symbols"""
    custom_symbols = ['AAPL', 'GOOG']
    stock_analyst.db_manager.symbol_has_historical_data.return_value = False
    stock_analyst.fmp_client.get_historical_prices.return_value = pd.DataFrame({'Date': ['2023-01-01']})
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_historical_data(symbols=custom_symbols)
    
    # Should use custom symbols, not call get_sp500_symbols
    stock_analyst.db_manager.get_sp500_symbols.assert_not_called()
    assert stock_analyst.fmp_client.get_historical_prices.call_count == 2

def test_fetch_and_store_historical_data_skip_existing(stock_analyst):
    """Test historical data fetching skips existing data"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
    stock_analyst.db_manager.symbol_has_historical_data.side_effect = [True, False]  # AAPL exists, MSFT doesn't
    stock_analyst.fmp_client.get_historical_prices.return_value = pd.DataFrame({'Date': ['2023-01-01']})
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_historical_data()
    
    # Should only be called for MSFT
    stock_analyst.fmp_client.get_historical_prices.assert_called_once_with('MSFT')

def test_fetch_and_store_historical_data_empty_data(stock_analyst):
    """Test historical data fetching handles empty data"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['INVALID']
    stock_analyst.db_manager.symbol_has_historical_data.return_value = False
    stock_analyst.fmp_client.get_historical_prices.return_value = pd.DataFrame()
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_historical_data()
    
    stock_analyst.fmp_client.get_historical_prices.assert_called_once_with('INVALID')
    stock_analyst.db_manager.insert_historical_prices.assert_not_called()

def test_run_initial_setup_success(stock_analyst):
    """Test successful initial setup run"""
    # Mock all methods to succeed
    stock_analyst.fetch_and_store_sp500_constituents = MagicMock(return_value=True)
    stock_analyst.fetch_and_store_company_profiles = MagicMock()
    stock_analyst.fetch_and_store_historical_data = MagicMock()
    
    stock_analyst.run_initial_setup()
    
    stock_analyst.fetch_and_store_sp500_constituents.assert_called_once()
    stock_analyst.fetch_and_store_company_profiles.assert_called_once_with(
        limit=stock_analyst.config.INITIAL_SETUP_COMPANY_PROFILES_LIMIT
    )
    stock_analyst.fetch_and_store_historical_data.assert_called_once_with(
        limit=stock_analyst.config.INITIAL_SETUP_HISTORICAL_DATA_LIMIT
    )

def test_run_initial_setup_sp500_failure(stock_analyst):
    """Test initial setup aborts on S&P 500 fetch failure"""
    stock_analyst.fetch_and_store_sp500_constituents = MagicMock(return_value=False)
    stock_analyst.fetch_and_store_company_profiles = MagicMock()
    stock_analyst.fetch_and_store_historical_data = MagicMock()
    
    stock_analyst.run_initial_setup()
    
    stock_analyst.fetch_and_store_sp500_constituents.assert_called_once()
    stock_analyst.fetch_and_store_company_profiles.assert_not_called()
    stock_analyst.fetch_and_store_historical_data.assert_not_called()

def test_analyze_data_success(stock_analyst):
    """Test data analysis execution"""
    # Mock database connection and query results
    mock_connection = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ('AAPL', 'Apple Inc.', 2800000000000),
        ('MSFT', 'Microsoft Corp.', 2400000000000)
    ]
    
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.execute.return_value = mock_result
    stock_analyst.db_manager.engine.connect.return_value = mock_connection
    
    stock_analyst.analyze_data()
    
    mock_connection.execute.assert_called_once()
    mock_result.fetchall.assert_called_once()

def test_analyze_data_database_error(stock_analyst):
    """Test data analysis handles database errors"""
    mock_connection = MagicMock()
    mock_connection.__enter__.side_effect = Exception("Database connection failed")
    stock_analyst.db_manager.engine.connect.return_value = mock_connection
    
    # Should not raise exception, should handle gracefully
    with pytest.raises(Exception):
        stock_analyst.analyze_data()

# --- Rate Limiting Tests ---

@patch('time.sleep')
def test_rate_limiting_company_profiles(mock_sleep, stock_analyst):
    """Test rate limiting is applied during company profile fetching"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    stock_analyst.fmp_client.get_company_profile.return_value = {'symbol': 'TEST'}
    
    stock_analyst.fetch_and_store_company_profiles()
    
    # Should sleep after each API call
    assert mock_sleep.call_count == 2
    mock_sleep.assert_has_calls([
        call(stock_analyst.config.FMP_RATE_LIMIT_DELAY),
        call(stock_analyst.config.FMP_RATE_LIMIT_DELAY)
    ])

@patch('time.sleep')
def test_rate_limiting_historical_data(mock_sleep, stock_analyst):
    """Test rate limiting is applied during historical data fetching"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
    stock_analyst.db_manager.symbol_has_historical_data.return_value = False
    stock_analyst.fmp_client.get_historical_prices.return_value = pd.DataFrame({'Date': ['2023-01-01']})
    
    stock_analyst.fetch_and_store_historical_data()
    
    # Should sleep after each API call
    assert mock_sleep.call_count == 2
    mock_sleep.assert_has_calls([
        call(stock_analyst.config.FMP_RATE_LIMIT_DELAY),
        call(stock_analyst.config.FMP_RATE_LIMIT_DELAY)
    ])

# --- Main Function Tests ---

@patch('main.StockAnalyst')
def test_main_function_success(mock_stock_analyst_class):
    """Test main function successful execution"""
    mock_analyst = MagicMock()
    mock_stock_analyst_class.return_value = mock_analyst
    
    main()
    
    mock_stock_analyst_class.assert_called_once()
    mock_analyst.run_initial_setup.assert_called_once()
    mock_analyst.analyze_data.assert_called_once()

@patch('main.StockAnalyst')
def test_main_function_exception_handling(mock_stock_analyst_class):
    """Test main function exception handling"""
    mock_analyst = MagicMock()
    mock_analyst.run_initial_setup.side_effect = Exception("Setup failed")
    mock_stock_analyst_class.return_value = mock_analyst
    
    with pytest.raises(Exception, match="Setup failed"):
        main()

# --- Integration Tests ---

def test_data_flow_integration(stock_analyst):
    """Test data flow from S&P 500 fetch to analysis"""
    # Mock the entire flow
    mock_sp500_df = pd.DataFrame({
        'Symbol': ['AAPL', 'MSFT'],
        'Name': ['Apple Inc.', 'Microsoft Corp.']
    })
    
    stock_analyst.fmp_client.get_sp500_constituents.return_value = mock_sp500_df
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    stock_analyst.db_manager.symbol_has_historical_data.return_value = False
    
    # Mock profile and historical data
    stock_analyst.fmp_client.get_company_profile.return_value = {'symbol': 'TEST'}
    stock_analyst.fmp_client.get_historical_prices.return_value = pd.DataFrame({'Date': ['2023-01-01']})
    
    # Mock analysis query
    mock_connection = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [('AAPL', 'Apple Inc.', 2800000000000)]
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.execute.return_value = mock_result
    stock_analyst.db_manager.engine.connect.return_value = mock_connection
    
    with patch('time.sleep'):
        stock_analyst.run_initial_setup()
        stock_analyst.analyze_data()
    
    # Verify complete flow
    stock_analyst.fmp_client.get_sp500_constituents.assert_called_once()
    stock_analyst.db_manager.insert_sp500_constituents.assert_called_once()
    stock_analyst.fmp_client.get_company_profile.assert_called()
    stock_analyst.fmp_client.get_historical_prices.assert_called()
    mock_connection.execute.assert_called_once()

# --- Configuration Tests ---

def test_configuration_usage(stock_analyst):
    """Test that configuration values are used correctly"""
    # Test rate limit delay
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    stock_analyst.fmp_client.get_company_profile.return_value = {'symbol': 'AAPL'}
    
    with patch('time.sleep') as mock_sleep:
        stock_analyst.fetch_and_store_company_profiles()
        
        mock_sleep.assert_called_with(stock_analyst.config.FMP_RATE_LIMIT_DELAY)
    
    # Test initial setup limits
    stock_analyst.fetch_and_store_company_profiles = MagicMock()
    stock_analyst.fetch_and_store_historical_data = MagicMock()
    stock_analyst.fetch_and_store_sp500_constituents = MagicMock(return_value=True)
    
    stock_analyst.run_initial_setup()
    
    stock_analyst.fetch_and_store_company_profiles.assert_called_with(
        limit=stock_analyst.config.INITIAL_SETUP_COMPANY_PROFILES_LIMIT
    )
    stock_analyst.fetch_and_store_historical_data.assert_called_with(
        limit=stock_analyst.config.INITIAL_SETUP_HISTORICAL_DATA_LIMIT
    )

# --- Error Recovery Tests ---

def test_partial_failure_recovery(stock_analyst):
    """Test system continues after partial failures"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT', 'GOOG']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    
    # Make middle call fail
    stock_analyst.fmp_client.get_company_profile.side_effect = [
        {'symbol': 'AAPL'},  # Success
        None,                # Failure (no data)
        {'symbol': 'GOOG'}   # Success
    ]
    
    with patch('time.sleep'):
        stock_analyst.fetch_and_store_company_profiles()
    
    # Should continue processing all symbols despite middle failure
    assert stock_analyst.fmp_client.get_company_profile.call_count == 3
    assert stock_analyst.db_manager.insert_company_profile.call_count == 2  # Only successful ones

def test_api_exception_handling(stock_analyst):
    """Test handling of API exceptions"""
    stock_analyst.db_manager.get_sp500_symbols.return_value = ['AAPL']
    stock_analyst.db_manager.symbol_exists_in_profiles.return_value = False
    stock_analyst.fmp_client.get_company_profile.side_effect = Exception("API Error")
    
    with patch('time.sleep'):
        # Should not raise exception, should continue
        stock_analyst.fetch_and_store_company_profiles()
    
    stock_analyst.fmp_client.get_company_profile.assert_called_once()
    stock_analyst.db_manager.insert_company_profile.assert_not_called()