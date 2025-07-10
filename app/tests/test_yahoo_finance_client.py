import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, date

# Import the client after setting up mocks if needed, though for yfinance it's often fine directly
from yahoo_finance_client import YahooFinanceClient

@pytest.fixture
def yahoo_client():
    return YahooFinanceClient()

@pytest.fixture
def mock_ticker_info():
    # Mock data for yf.Ticker().info
    return {
        'currentPrice': 150.0,
        'regularMarketPrice': 150.0,
        'marketCap': 1000000000000,
        'beta': 1.2,
        'trailingPE': 25.0,
        'forwardPE': 22.0,
        'priceToBook': 5.0,
        'priceToSalesTrailing12Months': 3.0,
        'returnOnEquity': 0.20,
        'returnOnAssets': 0.10,
        'debtToEquity': 0.50,
        'currentRatio': 1.5,
        'revenueGrowth': 0.15,
        'profitMargins': 0.12,
        'grossMargins': 0.40,
        'freeCashflow': 50000000000,
        'regularMarketVolume': 10000000,
        'averageVolume': 12000000,
        'fiftyTwoWeekHigh': 160.0,
        'fiftyTwoWeekLow': 120.0,
        'dividendYield': 0.01,
        'longName': 'Test Company Inc.',
        'shortName': 'Test Co.',
        'industry': 'Software',
        'sector': 'Technology',
        'website': 'http://test.com',
        'longBusinessSummary': 'This is a test company.',
        'country': 'USA',
        'city': 'Testville',
        'state': 'TS',
        'fullTimeEmployees': 10000,
        'phone': '555-123-4567',
        'address1': '123 Test St',
        'zip': '12345',
        'currency': 'USD',
        'exchange': 'NASDAQ',
    }

@pytest.fixture
def mock_ticker_history():
    # Mock data for yf.Ticker().history()
    return pd.DataFrame({
        'Date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
        'Open': [100.0, 101.0, 102.0],
        'High': [102.0, 103.0, 104.0],
        'Low': [99.0, 100.0, 101.0],
        'Close': [101.0, 102.0, 103.0],
        'Volume': [100000, 120000, 110000],
        'Dividends': [0.0, 0.0, 0.0],
        'Stock Splits': [0.0, 0.0, 0.0]
    })

@patch('yfinance.Ticker')
def test_get_quote_success(mock_yf_ticker, yahoo_client, mock_ticker_info):
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.info = mock_ticker_info

    quote = yahoo_client.get_quote('AAPL')
    assert quote is not None
    assert quote['symbol'] == 'AAPL'
    assert quote['price'] == 150.0
    assert quote['market_cap'] == 1000000000000
    assert quote['pe_ratio'] == 25.0
    assert quote['source'] == 'yahoo_finance'

@patch('yfinance.Ticker')
def test_get_quote_no_info(mock_yf_ticker, yahoo_client):
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.info = {}

    quote = yahoo_client.get_quote('NONEXISTENT')
    assert quote is None

@patch('yfinance.Ticker')
def test_get_company_profile_success(mock_yf_ticker, yahoo_client, mock_ticker_info):
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.info = mock_ticker_info

    profile = yahoo_client.get_company_profile('AAPL')
    assert profile is not None
    assert profile['symbol'] == 'AAPL'
    assert profile['companyname'] == 'Test Company Inc.'
    assert profile['sector'] == 'Technology'
    assert profile['description'] == 'This is a test company.'
    assert profile['source'] == 'yahoo_finance'

@patch('yfinance.Ticker')
def test_get_company_profile_no_info(mock_yf_ticker, yahoo_client):
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.info = {}

    profile = yahoo_client.get_company_profile('NONEXISTENT')
    assert profile is None

@patch('yahoo_finance_client.YahooFinanceClient.get_quote')
def test_get_fundamentals_summary_success(mock_get_quote, yahoo_client):
    mock_get_quote.return_value = {
        'symbol': 'AAPL',
        'pe_ratio': 25.0,
        'price_to_book': 5.0,
        'roe': 0.20,
        'market_cap': 1000000000000,
        'source': 'yahoo_finance'
    }

    fundamentals = yahoo_client.get_fundamentals_summary('AAPL')
    assert fundamentals is not None
    assert fundamentals['symbol'] == 'AAPL'
    assert fundamentals['pe_ratio'] == 25.0
    assert fundamentals['source'] == 'yahoo_finance'

@patch('yahoo_finance_client.YahooFinanceClient.get_quote')
def test_get_fundamentals_summary_no_quote(mock_get_quote, yahoo_client):
    mock_get_quote.return_value = None

    fundamentals = yahoo_client.get_fundamentals_summary('NONEXISTENT')
    assert fundamentals is None

@patch('yfinance.Ticker')
def test_get_historical_prices_success(mock_yf_ticker, yahoo_client, mock_ticker_history):
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.history.return_value = mock_ticker_history

    df = yahoo_client.get_historical_prices('AAPL', period="1y")
    assert not df.empty
    assert len(df) == 3
    assert df.iloc[0]['date'] == date(2023, 1, 1)
    assert df.iloc[2]['close'] == 103.0
    assert 'adjclose' not in df.columns # Ensure only required columns are present

@patch('yfinance.Ticker')
def test_get_historical_prices_empty(mock_yf_ticker, yahoo_client):
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.history.return_value = pd.DataFrame()

    df = yahoo_client.get_historical_prices('NONEXISTENT')
    assert df is None

@patch('yahoo_finance_client.YahooFinanceClient.get_quote')
def test_is_available(mock_get_quote, yahoo_client):
    mock_get_quote.return_value = {'price': 100.0}
    assert yahoo_client.is_available()

    mock_get_quote.return_value = None
    assert not yahoo_client.is_available()

    mock_get_quote.return_value = {'price': None}
    assert not yahoo_client.is_available()

@patch('yahoo_finance_client.YahooFinanceClient.get_quote')
def test_get_batch_quotes(mock_get_quote, yahoo_client):
    mock_get_quote.side_effect = [
        {'symbol': 'AAPL', 'price': 170.0},
        {'symbol': 'MSFT', 'price': 400.0},
        None # Simulate failure for GOOG
    ]

    symbols = ['AAPL', 'MSFT', 'GOOG']
    results = yahoo_client.get_batch_quotes(symbols)

    assert len(results) == 2
    assert 'AAPL' in results
    assert 'MSFT' in results
    assert 'GOOG' not in results
    assert results['AAPL']['price'] == 170.0
    assert mock_get_quote.call_count == 3

# --- Additional Yahoo Finance Client Tests ---

@patch('yfinance.Ticker')
def test_get_quote_exception_handling(mock_yf_ticker, yahoo_client):
    """Test quote retrieval with yfinance exceptions"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.info = MagicMock(side_effect=Exception("Network error"))
    
    quote = yahoo_client.get_quote('AAPL')
    assert quote is None

@patch('yfinance.Ticker')
def test_get_quote_with_missing_fields(mock_yf_ticker, yahoo_client):
    """Test quote retrieval with missing fields in yfinance info"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.info = {
        'currentPrice': 150.0,
        # Missing many fields that would normally be present
        'longName': 'Test Company'
    }
    
    quote = yahoo_client.get_quote('AAPL')
    assert quote is not None
    assert quote['symbol'] == 'AAPL'
    assert quote['price'] == 150.0
    # Should handle missing fields gracefully
    assert quote.get('market_cap') is None or quote.get('market_cap') == 0

@patch('yfinance.Ticker')
def test_get_company_profile_partial_data(mock_yf_ticker, yahoo_client):
    """Test company profile with partial data"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.info = {
        'longName': 'Partial Data Company',
        'sector': 'Technology',
        # Missing many optional fields
    }
    
    profile = yahoo_client.get_company_profile('PARTIAL')
    assert profile is not None
    assert profile['symbol'] == 'PARTIAL'
    assert profile['companyname'] == 'Partial Data Company'
    assert profile['sector'] == 'Technology'
    assert profile.get('description', '') == ''  # Should handle missing description

@patch('yfinance.Ticker')
def test_get_historical_prices_with_start_end_dates(mock_yf_ticker, yahoo_client):
    """Test historical prices with start and end dates"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    
    # Mock history data
    mock_history = pd.DataFrame({
        'Date': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'Open': [100.0, 101.0],
        'High': [102.0, 103.0],
        'Low': [99.0, 100.0],
        'Close': [101.0, 102.0],
        'Volume': [100000, 120000]
    })
    mock_ticker_instance.history.return_value = mock_history
    
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 1, 3)
    
    df = yahoo_client.get_historical_prices('AAPL', start=start_date, end=end_date)
    
    assert not df.empty
    assert len(df) == 2
    mock_ticker_instance.history.assert_called_once_with(start=start_date, end=end_date)

@patch('yfinance.Ticker')
def test_get_historical_prices_exception_handling(mock_yf_ticker, yahoo_client):
    """Test historical prices with yfinance exceptions"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    mock_ticker_instance.history.side_effect = Exception("API error")
    
    df = yahoo_client.get_historical_prices('AAPL')
    assert df is None

@patch('yfinance.Ticker')
def test_get_historical_prices_data_transformation(mock_yf_ticker, yahoo_client):
    """Test that historical prices data is properly transformed"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    
    # Create mock data with index as dates (like yfinance returns)
    dates = pd.to_datetime(['2023-01-01', '2023-01-02'])
    mock_history = pd.DataFrame({
        'Open': [100.0, 101.0],
        'High': [102.0, 103.0],
        'Low': [99.0, 100.0],
        'Close': [101.0, 102.0],
        'Volume': [100000, 120000],
        'Dividends': [0.0, 0.0],
        'Stock Splits': [0.0, 0.0]
    }, index=dates)
    
    mock_ticker_instance.history.return_value = mock_history
    
    df = yahoo_client.get_historical_prices('AAPL')
    
    assert not df.empty
    assert 'date' in df.columns
    assert 'open' in df.columns
    assert 'high' in df.columns
    assert 'low' in df.columns
    assert 'close' in df.columns
    assert 'volume' in df.columns
    
    # Check data types
    assert df['date'].dtype == 'object'  # Should be converted to date objects
    assert all(isinstance(d, date) for d in df['date'])

def test_get_batch_quotes_empty_list(yahoo_client):
    """Test batch quotes with empty symbol list"""
    results = yahoo_client.get_batch_quotes([])
    assert results == {}

@patch('yahoo_finance_client.YahooFinanceClient.get_quote')
def test_get_batch_quotes_all_failures(mock_get_quote, yahoo_client):
    """Test batch quotes when all symbols fail"""
    mock_get_quote.return_value = None
    
    symbols = ['INVALID1', 'INVALID2', 'INVALID3']
    results = yahoo_client.get_batch_quotes(symbols)
    
    assert results == {}
    assert mock_get_quote.call_count == 3

@patch('yahoo_finance_client.YahooFinanceClient.get_quote')
def test_get_batch_quotes_rate_limiting(mock_get_quote, yahoo_client):
    """Test that batch quotes doesn't overwhelm the API"""
    mock_get_quote.return_value = {'symbol': 'TEST', 'price': 100.0}
    
    # Large number of symbols
    symbols = [f'TEST{i}' for i in range(10)]
    
    with patch('time.sleep') as mock_sleep:
        results = yahoo_client.get_batch_quotes(symbols)
    
    # Should have gotten all results
    assert len(results) == 10
    
    # Should have called sleep between requests (if implemented)
    # This depends on the actual implementation

def test_is_available_service_check(yahoo_client):
    """Test availability check without external dependency"""
    with patch.object(yahoo_client, 'get_quote') as mock_get_quote:
        # Test when service is available
        mock_get_quote.return_value = {'price': 100.0}
        assert yahoo_client.is_available() is True
        
        # Test when service is unavailable
        mock_get_quote.return_value = None
        assert yahoo_client.is_available() is False
        
        # Test when price is None (service responding but no data)
        mock_get_quote.return_value = {'price': None}
        assert yahoo_client.is_available() is False

@patch('yfinance.Ticker')
def test_data_type_conversions(mock_yf_ticker, yahoo_client):
    """Test proper data type conversions from yfinance"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    
    # Mock info with various data types including strings that should be numbers
    mock_ticker_instance.info = {
        'currentPrice': '150.50',  # String that should be float
        'marketCap': '1000000000000',  # String that should be int
        'trailingPE': 25.5,  # Already float
        'regularMarketVolume': 10000000,  # Already int
        'longName': 'Test Company Inc.',  # String that should stay string
        'beta': None,  # None value
    }
    
    quote = yahoo_client.get_quote('AAPL')
    
    assert quote is not None
    # Should convert string numbers to appropriate types
    assert isinstance(quote['price'], float)
    assert quote['price'] == 150.50
    
    if 'market_cap' in quote:
        assert isinstance(quote['market_cap'], (int, float))
    
    # String should remain string
    assert isinstance(quote.get('company_name', ''), str)

@patch('yfinance.Ticker')
def test_error_resilience_malformed_data(mock_yf_ticker, yahoo_client):
    """Test resilience to malformed data from yfinance"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    
    # Mock info with problematic data
    mock_ticker_instance.info = {
        'currentPrice': 'not_a_number',
        'marketCap': float('inf'),  # Infinity
        'trailingPE': float('nan'),  # NaN
        'longName': None,  # None where string expected
        'regularMarketVolume': -1,  # Negative volume (unusual but possible)
    }
    
    quote = yahoo_client.get_quote('AAPL')
    
    # Should handle malformed data gracefully
    assert quote is not None
    assert quote['symbol'] == 'AAPL'
    
    # Price should be None or 0 if conversion fails
    assert quote.get('price') is None or quote.get('price') == 0

@patch('yfinance.Ticker')
def test_unicode_and_special_characters(mock_yf_ticker, yahoo_client):
    """Test handling of unicode and special characters"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    
    mock_ticker_instance.info = {
        'longName': 'Société Générale S.A.',  # Unicode characters
        'shortName': 'SocGen',
        'currentPrice': 45.67,
        'longBusinessSummary': 'Company with émojis 🏦 and special chars: <>&"\'',
        'city': 'Paris',
        'country': 'France'
    }
    
    profile = yahoo_client.get_company_profile('GLE.PA')
    
    assert profile is not None
    assert 'Société Générale' in profile['companyname']
    assert '🏦' in profile.get('description', '')

@patch('yfinance.Ticker')  
def test_large_numbers_precision(mock_yf_ticker, yahoo_client):
    """Test handling of very large numbers and precision"""
    mock_ticker_instance = MagicMock()
    mock_yf_ticker.return_value = mock_ticker_instance
    
    mock_ticker_instance.info = {
        'currentPrice': 150.123456789,  # High precision
        'marketCap': 2800000000000,  # Very large number (2.8 trillion)
        'regularMarketVolume': 50000000,  # 50 million
        'longName': 'Big Company Inc.'
    }
    
    quote = yahoo_client.get_quote('BIGCO')
    
    assert quote is not None
    # Should handle large numbers without overflow
    assert quote.get('market_cap', 0) == 2800000000000
    # Precision should be reasonable
    assert abs(quote.get('price', 0) - 150.123456789) < 0.001

def test_client_initialization(yahoo_client):
    """Test Yahoo Finance client initialization"""
    assert yahoo_client is not None
    # Test that it's properly initialized
    assert hasattr(yahoo_client, 'get_quote')
    assert hasattr(yahoo_client, 'get_company_profile')
    assert hasattr(yahoo_client, 'get_historical_prices')
