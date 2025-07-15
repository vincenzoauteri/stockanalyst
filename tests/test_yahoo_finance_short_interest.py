import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from yahoo_finance_client import YahooFinanceClient


class TestYahooFinanceShortInterest:
    """Test suite for Yahoo Finance short interest data collection"""
    
    @pytest.fixture
    def client(self):
        """Create a YahooFinanceClient instance"""
        return YahooFinanceClient()
    
    def test_get_short_interest_data_success(self, client):
        """Test successful short interest data retrieval"""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            'sharesShort': 50000000,
            'floatShares': 300000000,
            'shortRatio': 2.5,
            'shortPercentOfFloat': 0.1667,  # 16.67%
            'averageDailyVolume10Day': 20000000,
            'averageVolume': 18000000
        }
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            result = client.get_short_interest_data("AAPL")
            
            assert result is not None
            assert result['symbol'] == "AAPL"
            assert result['short_interest'] == 50000000
            assert result['float_shares'] == 300000000
            assert result['short_ratio'] == 2.5
            assert result['short_percent_of_float'] == 0.1667
            assert result['average_daily_volume'] == 20000000
            assert result['source'] == 'yahoo_finance'
            assert 'report_date' in result
            assert 'timestamp' in result
    
    def test_get_short_interest_data_partial_data(self, client):
        """Test short interest data retrieval with partial data"""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            'sharesShort': 50000000,
            'floatShares': None,  # Missing data
            'shortRatio': 2.5,
            'shortPercentOfFloat': None,  # Missing data
            'averageVolume': 18000000  # Only fallback volume available
        }
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            result = client.get_short_interest_data("MSFT")
            
            assert result is not None
            assert result['symbol'] == "MSFT"
            assert result['short_interest'] == 50000000
            assert result['float_shares'] is None
            assert result['short_ratio'] == 2.5
            assert result['short_percent_of_float'] is None
            assert result['average_daily_volume'] == 18000000
    
    def test_get_short_interest_data_no_info(self, client):
        """Test short interest data retrieval when no info is available"""
        mock_ticker = MagicMock()
        mock_ticker.info = None
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            result = client.get_short_interest_data("INVALID")
            
            assert result is None
    
    def test_get_short_interest_data_empty_info(self, client):
        """Test short interest data retrieval with empty info"""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            result = client.get_short_interest_data("GOOGL")
            
            assert result is not None
            assert result['symbol'] == "GOOGL"
            assert result['short_interest'] is None
            assert result['float_shares'] is None
            assert result['short_ratio'] is None
            assert result['short_percent_of_float'] is None
            assert result['average_daily_volume'] is None
    
    def test_get_short_interest_data_ticker_creation_fails(self, client):
        """Test short interest data retrieval when ticker creation fails"""
        with patch('yahoo_finance_client.yf.Ticker', side_effect=Exception("Network error")):
            result = client.get_short_interest_data("FAIL")
            
            assert result is None
    
    def test_get_short_interest_data_info_access_fails(self, client):
        """Test short interest data retrieval when info access fails"""
        mock_ticker = MagicMock()
        
        # Configure mock to raise exception when accessing info
        type(mock_ticker).info = PropertyMock(side_effect=Exception("Access error"))
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            result = client.get_short_interest_data("ERROR")
            
            assert result is None
    
    def test_get_short_interest_data_with_string_values(self, client):
        """Test short interest data retrieval with string values that need conversion"""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            'sharesShort': '50000000',  # String that should convert to int
            'floatShares': '300000000',
            'shortRatio': '2.5',  # String that should convert to float
            'shortPercentOfFloat': '0.1667',
            'averageDailyVolume10Day': '20000000'
        }
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            result = client.get_short_interest_data("TSLA")
            
            assert result is not None
            assert result['short_interest'] == 50000000
            assert result['float_shares'] == 300000000
            assert result['short_ratio'] == 2.5
            assert result['short_percent_of_float'] == 0.1667
            assert result['average_daily_volume'] == 20000000
    
    def test_get_short_interest_data_with_invalid_values(self, client):
        """Test short interest data retrieval with invalid values"""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            'sharesShort': 'invalid',  # Invalid string
            'floatShares': float('inf'),  # Infinite value
            'shortRatio': '',  # Empty string
            'shortPercentOfFloat': 'N/A',  # Non-numeric string
            'averageDailyVolume10Day': None
        }
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            result = client.get_short_interest_data("META")
            
            assert result is not None
            assert result['short_interest'] is None
            assert result['float_shares'] is None
            assert result['short_ratio'] is None
            assert result['short_percent_of_float'] is None
            assert result['average_daily_volume'] is None
    
    def test_rate_limiting_applied(self, client):
        """Test that rate limiting is applied"""
        mock_ticker = MagicMock()
        mock_ticker.info = {'sharesShort': 1000000}
        
        with patch('yahoo_finance_client.yf.Ticker', return_value=mock_ticker):
            with patch('yahoo_finance_client.time.sleep') as mock_sleep:
                client.get_short_interest_data("AAPL")
                
                mock_sleep.assert_called_once_with(client.request_delay)
    
    @pytest.mark.integration
    def test_get_short_interest_data_real_symbol(self, client):
        """Integration test with real Yahoo Finance data (marked as integration test)"""
        # This test uses real Yahoo Finance data and may be slow
        # Skip if we want to avoid external API calls
        result = client.get_short_interest_data("AAPL")
        
        # We can't assert specific values since they change, but we can verify structure
        if result is not None:  # Data might not always be available
            assert 'symbol' in result
            assert result['symbol'] == "AAPL"
            assert 'source' in result
            assert result['source'] == 'yahoo_finance'
            assert 'report_date' in result
            assert 'timestamp' in result
            
            # All numeric fields should be either None or valid numbers
            numeric_fields = ['short_interest', 'float_shares', 'average_daily_volume']
            for field in numeric_fields:
                if result.get(field) is not None:
                    assert isinstance(result[field], int)
                    assert result[field] >= 0
            
            ratio_fields = ['short_ratio', 'short_percent_of_float']
            for field in ratio_fields:
                if result.get(field) is not None:
                    assert isinstance(result[field], float)
                    assert result[field] >= 0