import pytest
from unittest.mock import patch, MagicMock
from data_fetcher import DataFetcher


class TestDataFetcherShortInterest:
    """Test suite for DataFetcher short interest functionality"""
    
    @pytest.fixture
    def data_fetcher(self):
        """Create a DataFetcher instance with mocked dependencies"""
        with patch('data_fetcher.DatabaseManager') as mock_db, \
             patch('data_fetcher.FMPClient') as mock_fmp:
            
            fetcher = DataFetcher()
            fetcher.db_manager = mock_db.return_value
            fetcher.fmp_client = mock_fmp.return_value
            
            # Mock yahoo client
            fetcher.fmp_client.yahoo_client = MagicMock()
            
            return fetcher
    
    def test_fetch_short_interest_data_success(self, data_fetcher):
        """Test successful short interest data fetching"""
        # Mock short interest data
        mock_short_data = {
            'symbol': 'AAPL',
            'report_date': '2025-07-13',
            'short_interest': 50000000,
            'float_shares': 300000000,
            'short_ratio': 2.5,
            'short_percent_of_float': 16.67,
            'average_daily_volume': 20000000,
            'source': 'yahoo_finance',
            'timestamp': '2025-07-13T12:00:00'
        }
        
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.return_value = mock_short_data
        
        # Test fetching
        symbols = ['AAPL']
        result = data_fetcher.fetch_short_interest_data(symbols)
        
        # Verify method was called
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.assert_called_once_with('AAPL')
        
        # Verify database insertion was called with correct data (without timestamp/source)
        expected_db_data = {k: v for k, v in mock_short_data.items() 
                           if k not in ['timestamp', 'source']}
        data_fetcher.db_manager.insert_short_interest_data.assert_called_once_with('AAPL', expected_db_data)
        
        # Verify return value
        assert result == 1
    
    def test_fetch_short_interest_data_no_data(self, data_fetcher):
        """Test handling when no short interest data is available"""
        # Mock empty response
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.return_value = {
            'symbol': 'AAPL',
            'report_date': '2025-07-13',
            'short_interest': None,
            'float_shares': None,
            'short_ratio': None,
            'short_percent_of_float': None,
            'average_daily_volume': None,
            'source': 'yahoo_finance',
            'timestamp': '2025-07-13T12:00:00'
        }
        
        symbols = ['AAPL']
        result = data_fetcher.fetch_short_interest_data(symbols)
        
        # Verify no database insertion was called
        data_fetcher.db_manager.insert_short_interest_data.assert_not_called()
        
        # Verify return value
        assert result == 0
    
    def test_fetch_short_interest_data_partial_data(self, data_fetcher):
        """Test handling when partial short interest data is available"""
        # Mock partial data
        mock_short_data = {
            'symbol': 'MSFT',
            'report_date': '2025-07-13',
            'short_interest': 25000000,  # Has data
            'float_shares': None,        # No data
            'short_ratio': 1.8,          # Has data
            'short_percent_of_float': None,  # No data
            'average_daily_volume': 15000000,  # Has data
            'source': 'yahoo_finance',
            'timestamp': '2025-07-13T12:00:00'
        }
        
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.return_value = mock_short_data
        
        symbols = ['MSFT']
        result = data_fetcher.fetch_short_interest_data(symbols)
        
        # Verify database insertion was called (since some data is available)
        expected_db_data = {k: v for k, v in mock_short_data.items() 
                           if k not in ['timestamp', 'source']}
        data_fetcher.db_manager.insert_short_interest_data.assert_called_once_with('MSFT', expected_db_data)
        
        # Verify return value
        assert result == 1
    
    def test_fetch_short_interest_data_no_yahoo_client(self, data_fetcher):
        """Test handling when Yahoo Finance client is not available"""
        # Remove yahoo client
        data_fetcher.fmp_client.yahoo_client = None
        
        symbols = ['AAPL']
        result = data_fetcher.fetch_short_interest_data(symbols)
        
        # Verify no processing occurred
        assert result == 0
        data_fetcher.db_manager.insert_short_interest_data.assert_not_called()
    
    def test_fetch_short_interest_data_api_error(self, data_fetcher):
        """Test handling when API call raises an exception"""
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.side_effect = Exception("API Error")
        
        symbols = ['AAPL']
        result = data_fetcher.fetch_short_interest_data(symbols)
        
        # Verify error was handled gracefully
        assert result == 0
        data_fetcher.db_manager.insert_short_interest_data.assert_not_called()
    
    def test_fetch_short_interest_data_database_error(self, data_fetcher):
        """Test handling when database insertion raises an exception"""
        mock_short_data = {
            'symbol': 'AAPL',
            'report_date': '2025-07-13',
            'short_interest': 50000000,
            'source': 'yahoo_finance',
            'timestamp': '2025-07-13T12:00:00'
        }
        
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.return_value = mock_short_data
        data_fetcher.db_manager.insert_short_interest_data.side_effect = Exception("Database Error")
        
        symbols = ['AAPL']
        result = data_fetcher.fetch_short_interest_data(symbols)
        
        # Verify error was handled gracefully
        assert result == 0
    
    def test_fetch_short_interest_data_multiple_symbols(self, data_fetcher):
        """Test fetching short interest data for multiple symbols"""
        def mock_get_short_interest(symbol):
            return {
                'symbol': symbol,
                'short_interest': 10000000,
                'source': 'yahoo_finance',
                'timestamp': '2025-07-13T12:00:00'
            }
        
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.side_effect = mock_get_short_interest
        
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        result = data_fetcher.fetch_short_interest_data(symbols)
        
        # Verify all symbols were processed
        assert result == 3
        assert data_fetcher.fmp_client.yahoo_client.get_short_interest_data.call_count == 3
        assert data_fetcher.db_manager.insert_short_interest_data.call_count == 3
    
    def test_fetch_short_interest_data_max_requests_limit(self, data_fetcher):
        """Test that max_requests limit is respected"""
        def mock_get_short_interest(symbol):
            return {
                'symbol': symbol,
                'short_interest': 10000000,
                'source': 'yahoo_finance',
                'timestamp': '2025-07-13T12:00:00'
            }
        
        data_fetcher.fmp_client.yahoo_client.get_short_interest_data.side_effect = mock_get_short_interest
        
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'META']
        result = data_fetcher.fetch_short_interest_data(symbols, max_requests=3)
        
        # Verify only max_requests symbols were processed
        assert result == 3
        assert data_fetcher.fmp_client.yahoo_client.get_short_interest_data.call_count == 3
    
    def test_fetch_all_new_data_types_includes_short_interest(self, data_fetcher):
        """Test that fetch_all_new_data_types includes short interest data"""
        # Mock symbol retrieval
        data_fetcher.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
        
        # Mock all fetch methods to return 1 (successful processing)
        with patch.object(data_fetcher, 'fetch_corporate_actions', return_value=1), \
             patch.object(data_fetcher, 'fetch_financial_statements', return_value=1), \
             patch.object(data_fetcher, 'fetch_analyst_recommendations', return_value=1), \
             patch.object(data_fetcher, 'fetch_short_interest_data', return_value=1):
            
            result = data_fetcher.fetch_all_new_data_types()
            
            # Verify short interest is included in results
            assert 'short_interest' in result
            assert result['short_interest'] == 1
            assert result['total_symbols'] == 2
            
            # Verify short interest fetch method was called
            data_fetcher.fetch_short_interest_data.assert_called_once()