import pytest
import os
import json
from unittest.mock import patch, mock_open
from datetime import datetime, date, timedelta
import pandas as pd

# Mock the os.getenv for FMP_API_KEY before importing FMPClient
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {'FMP_API_KEY': 'test_api_key', 'DATABASE_PATH': ':memory:'}):
        yield

# Import FMPClient after mocking env vars
from fmp_client import FMPClient, APIUsageTracker

@pytest.fixture
def fmp_client():
    # Use a temporary file for API usage tracking
    with patch('fmp_client.Path') as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.open = mock_open()
        client = FMPClient()
        yield client

@pytest.fixture
def usage_tracker():
    # Use a temporary file for API usage tracking
    with patch('fmp_client.Path') as mock_path:
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.open = mock_open()
        tracker = APIUsageTracker()
        yield tracker

# --- APIUsageTracker Tests ---

def test_usage_tracker_initialization(usage_tracker):
    assert usage_tracker.get_daily_usage() == 0
    assert usage_tracker.get_remaining_budget() == 250

def test_usage_tracker_record_request(usage_tracker):
    assert usage_tracker.record_request(5)
    assert usage_tracker.get_daily_usage() == 5
    assert usage_tracker.get_remaining_budget() == 245

    assert usage_tracker.record_request(240) # Exceeds limit
    assert usage_tracker.get_daily_usage() == 245
    assert usage_tracker.get_remaining_budget() == 5
    assert not usage_tracker.can_make_request(6)

def test_usage_tracker_reset_new_day(usage_tracker):
    # Simulate usage on day 1
    usage_tracker.record_request(10)
    assert usage_tracker.get_daily_usage() == 10

    # Simulate new day
    with patch('fmp_client.date') as mock_date:
        mock_date.today.return_value = date.today() + timedelta(days=1)
        mock_date.side_effect = lambda *args, **kw: date.today() + timedelta(days=1) if not args else date(*args, **kw)
        
        # Accessing any method that calls _reset_if_new_day will trigger reset
        assert usage_tracker.get_daily_usage() == 0
        assert usage_tracker.get_remaining_budget() == 250

def test_usage_tracker_get_usage_summary(usage_tracker):
    usage_tracker.record_request(50)
    summary = usage_tracker.get_usage_summary()
    assert summary['used_today'] == 50
    assert summary['remaining_today'] == 200
    assert summary['percentage_used'] == 20.0
    assert summary['daily_limit'] == 250

def test_usage_tracker_get_usage_recommendation(usage_tracker):
    usage_tracker.record_request(10)
    assert "OK" in usage_tracker.get_usage_recommendation()

    usage_tracker.record_request(150) # 160 total (64%)
    assert "CAUTION" in usage_tracker.get_usage_recommendation()

    usage_tracker.record_request(30) # 190 total (76%)
    assert "WARNING" in usage_tracker.get_usage_recommendation()

    usage_tracker.record_request(40) # 230 total (92%)
    assert "CRITICAL" in usage_tracker.get_usage_recommendation()

# --- FMPClient Tests ---

@patch('fmp_client.requests.get')
def test_get_sp500_constituents_success(mock_get, fmp_client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = """
    <table id="constituents">
        <tr><th>Symbol</th><th>Company</th><th>Sector</th><th>Sub-Industry</th><th>Headquarters</th></tr>
        <tr><td>AAPL</td><td>Apple Inc.</td><td>Technology</td><td>Consumer Electronics</td><td>Cupertino</td></tr>
        <tr><td>MSFT</td><td>Microsoft Corp.</td><td>Technology</td><td>Software</td><td>Redmond</td></tr>
    </table>
    """
    
    df = fmp_client.get_sp500_constituents()
    assert not df.empty
    assert len(df) == 2
    assert df.iloc[0]['symbol'] == 'AAPL'
    assert df.iloc[1]['name'] == 'Microsoft Corp.'
    mock_get.assert_called_once_with("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")

@patch('fmp_client.requests.get')
def test_get_sp500_constituents_no_table(mock_get, fmp_client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "<html><body>No table here</body></html>"
    
    df = fmp_client.get_sp500_constituents()
    assert df.empty

@patch('fmp_client.requests.get')
def test_get_company_profile_fmp_success(mock_get, fmp_client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{
        'symbol': 'AAPL',
        'companyName': 'Apple Inc.',
        'price': 170.0,
        'sector': 'Technology'
    }]
    
    profile = fmp_client.get_company_profile('AAPL')
    assert profile['symbol'] == 'AAPL'
    assert profile['companyName'] == 'Apple Inc.'
    mock_get.assert_called_once()
    assert fmp_client.usage_tracker.get_daily_usage() == 1

@patch('fmp_client.requests.get')
def test_get_company_profile_fmp_api_key_missing(mock_get):
    with patch.dict(os.environ, {'FMP_API_KEY': ''}): # Temporarily remove API key
        with patch('yahoo_finance_client.YahooFinanceClient') as mock_yahoo_class:
            mock_yahoo_client = mock_yahoo_class.return_value
            mock_yahoo_client.get_company_profile.return_value = {
                'symbol': 'AAPL',
                'companyName': 'Apple Inc.',
                'source': 'yahoo_finance'
            }
            
            client = FMPClient()
            profile = client.get_company_profile('AAPL')
            assert profile is not None # Fallback should be used
            assert profile.get('source') == 'yahoo_finance'
            mock_get.assert_not_called() # FMP API should not be called

@patch('fmp_client.requests.get')
@patch('yahoo_finance_client.YahooFinanceClient')
def test_get_company_profile_fmp_fallback(mock_yahoo_client, mock_get, fmp_client):
    # Simulate FMP API failure or limit exceeded
    mock_get.return_value.status_code = 403 # Forbidden, e.g., API limit
    mock_get.return_value.json.return_value = {"error": "API limit reached"}

    # Mock Yahoo Finance client response
    mock_yahoo_client_instance = mock_yahoo_client.return_value
    mock_yahoo_client_instance.get_company_profile.return_value = {
        'symbol': 'AAPL',
        'companyname': 'Apple Inc. (Yahoo)',
        'source': 'yahoo_finance'
    }
    
    profile = fmp_client.get_company_profile('AAPL')
    assert profile['companyname'] == 'Apple Inc. (Yahoo)'
    assert profile['source'] == 'yahoo_finance'
    mock_get.assert_called_once() # FMP was attempted
    mock_yahoo_client_instance.get_company_profile.assert_called_once_with('AAPL')

@patch('fmp_client.requests.get')
def test_get_historical_prices(mock_get, fmp_client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'historical': [
            {'date': '2023-01-01', 'open': 100, 'high': 105, 'low': 99, 'close': 104, 'volume': 100000},
            {'date': '2023-01-02', 'open': 104, 'high': 106, 'low': 103, 'close': 105, 'volume': 120000},
        ]
    }
    
    df = fmp_client.get_historical_prices('AAPL')
    assert not df.empty
    assert len(df) == 2
    assert df.iloc[0]['date'].strftime('%Y-%m-%d') == '2023-01-01'
    assert df.iloc[1]['close'] == 105
    assert fmp_client.usage_tracker.get_daily_usage() == 1

@patch('fmp_client.requests.get')
@patch('fmp_client.YahooFinanceClient')
def test_get_fundamentals_summary_fmp_fallback(mock_yahoo_client, mock_get, fmp_client):
    # Simulate FMP API failure for all fundamental calls
    mock_get.side_effect = [None, None, None] # Simulate 3 failures for key_metrics, ratios, income_statement

    # Mock Yahoo Finance client response
    mock_yahoo_client_instance = mock_yahoo_client.return_value
    mock_yahoo_client_instance.get_fundamentals_summary.return_value = {
        'symbol': 'AAPL',
        'pe_ratio': 25.0,
        'source': 'yahoo_finance'
    }

    summary = fmp_client.get_fundamentals_summary('AAPL')
    assert summary['source'] == 'yahoo_finance'
    assert summary['pe_ratio'] == 25.0
    mock_yahoo_client_instance.get_fundamentals_summary.assert_called_once_with('AAPL')

@patch('fmp_client.requests.get')
def test_get_fundamentals_summary_fmp_success(mock_get, fmp_client):
    # Mock successful FMP responses for each fundamental call
    mock_get.side_effect = [
        # key_metrics
        MagicMock(status_code=200, json=lambda: [{'date': '2023-01-01', 'marketCap': 2.8e12, 'peRatio': 30.0, 'roe': 0.5}]),
        # ratios
        MagicMock(status_code=200, json=lambda: [{'date': '2023-01-01', 'grossProfitMargin': 0.4, 'netProfitMargin': 0.2}]),
        # income_statement
        MagicMock(status_code=200, json=lambda: [{'date': '2023-01-01', 'revenue': 100e9, 'netIncome': 20e9, 'eps': 1.5}])
    ]

    summary = fmp_client.get_fundamentals_summary('AAPL')
    assert summary['symbol'] == 'AAPL'
    assert summary['market_cap'] == 2.8e12
    assert summary['pe_ratio'] == 30.0
    assert summary['gross_profit_margin'] == 0.4
    assert summary['revenue'] == 100e9
    assert fmp_client.usage_tracker.get_daily_usage() == 3 # 3 API calls for fundamentals

@patch('fmp_client.requests.get')
def test_get_price_targets(mock_get, fmp_client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {'symbol': 'AAPL', 'publishedDate': '2023-01-01', 'priceTarget': 180.0},
        {'symbol': 'AAPL', 'publishedDate': '2023-02-01', 'priceTarget': 185.0},
    ]
    
    targets = fmp_client.get_price_targets('AAPL')
    assert len(targets) == 2
    assert targets[0]['priceTarget'] == 180.0
    assert fmp_client.usage_tracker.get_daily_usage() == 1

@patch('fmp_client.requests.get')
def test_api_request_blocked_by_limit(mock_get, fmp_client):
    # Exhaust the daily limit
    fmp_client.usage_tracker.record_request(250)
    
    profile = fmp_client.get_company_profile('AAPL')
    assert profile is not None # Fallback should be used
    assert profile.get('source') == 'yahoo_finance'
    mock_get.assert_not_called() # FMP API should not be called if limit is reached

@patch('fmp_client.requests.get')
def test_api_request_no_api_key(mock_get):
    with patch.dict(os.environ, {'FMP_API_KEY': ''}):
        client = FMPClient()
        profile = client.get_company_profile('AAPL')
        assert profile is not None # Fallback should be used
        assert profile.get('source') == 'yahoo_finance'
        mock_get.assert_not_called()
