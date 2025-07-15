import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime, date
from short_squeeze_analyzer import ShortSqueezeAnalyzer


class TestShortSqueezeAnalyzer:
    """Test suite for ShortSqueezeAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a ShortSqueezeAnalyzer instance with mocked database"""
        with patch('short_squeeze_analyzer.DatabaseManager') as mock_db:
            analyzer = ShortSqueezeAnalyzer()
            analyzer.db = mock_db.return_value
            return analyzer
    
    @pytest.fixture
    def sample_short_data(self):
        """Sample short interest data"""
        return {
            'symbol': 'AAPL',
            'report_date': date.today(),
            'short_interest': 50000000,
            'float_shares': 100000000,
            'short_ratio': 5.0,
            'short_percent_of_float': 25.0,
            'average_daily_volume': 10000000
        }
    
    @pytest.fixture
    def sample_price_data(self):
        """Sample historical price data for RSI calculation"""
        dates = pd.date_range(start='2025-01-01', periods=30, freq='D')
        prices = [100 + i + np.random.normal(0, 2) for i in range(30)]
        volumes = [1000000 + i * 10000 for i in range(30)]
        
        return pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'close': prices,
            'volume': volumes
        })
    
    def test_normalize_si_score(self, analyzer):
        """Test SI% score normalization"""
        # Below threshold
        assert analyzer.normalize_si_score(5.0) == 0.0
        assert analyzer.normalize_si_score(10.0) == 0.0
        
        # Above threshold
        assert analyzer.normalize_si_score(40.0) == 100.0
        assert analyzer.normalize_si_score(50.0) == 100.0
        
        # Linear scaling
        assert analyzer.normalize_si_score(25.0) == 50.0  # Midpoint between 10 and 40
        assert analyzer.normalize_si_score(20.0) == pytest.approx(33.33, rel=1e-2)
    
    def test_normalize_dtc_score(self, analyzer):
        """Test Days to Cover score normalization"""
        # Below threshold
        assert analyzer.normalize_dtc_score(1.0) == 0.0
        assert analyzer.normalize_dtc_score(2.0) == 0.0
        
        # Above threshold
        assert analyzer.normalize_dtc_score(10.0) == 100.0
        assert analyzer.normalize_dtc_score(15.0) == 100.0
        
        # Linear scaling
        assert analyzer.normalize_dtc_score(6.0) == 50.0  # Midpoint between 2 and 10
    
    def test_normalize_float_score(self, analyzer):
        """Test Float score normalization (inverse scale)"""
        # Small float (high score)
        assert analyzer.normalize_float_score(5_000_000) == 100.0
        assert analyzer.normalize_float_score(10_000_000) == 100.0
        
        # Large float (low score)
        assert analyzer.normalize_float_score(200_000_000) == 0.0
        assert analyzer.normalize_float_score(300_000_000) == 0.0
        
        # Mid-range
        assert analyzer.normalize_float_score(105_000_000) == 50.0  # Midpoint
    
    def test_normalize_rvol_score(self, analyzer):
        """Test Relative Volume score normalization"""
        # Below threshold
        assert analyzer.normalize_rvol_score(1.0) == 0.0
        assert analyzer.normalize_rvol_score(1.5) == 0.0
        
        # Above threshold
        assert analyzer.normalize_rvol_score(5.0) == 100.0
        assert analyzer.normalize_rvol_score(10.0) == 100.0
        
        # Linear scaling
        assert analyzer.normalize_rvol_score(3.25) == 50.0  # Midpoint between 1.5 and 5
    
    def test_normalize_rsi_score(self, analyzer):
        """Test RSI score normalization (inverse scale)"""
        # Oversold (high score)
        assert analyzer.normalize_rsi_score(20.0) == 100.0
        assert analyzer.normalize_rsi_score(30.0) == 100.0
        
        # Overbought (low score)
        assert analyzer.normalize_rsi_score(70.0) == 0.0
        assert analyzer.normalize_rsi_score(80.0) == 0.0
        
        # Neutral
        assert analyzer.normalize_rsi_score(50.0) == 50.0  # Midpoint between 30 and 70
    
    def test_calculate_rsi_valid_data(self, analyzer, sample_price_data):
        """Test RSI calculation with valid price data"""
        prices = sample_price_data['close']
        rsi = analyzer.calculate_rsi(prices)
        
        # RSI should be between 0 and 100
        assert 0 <= rsi <= 100
        assert isinstance(rsi, float)
    
    def test_calculate_rsi_insufficient_data(self, analyzer):
        """Test RSI calculation with insufficient data"""
        # Less than 14 days of data
        prices = pd.Series([100, 101, 99, 102, 98])
        rsi = analyzer.calculate_rsi(prices)
        
        # Should return neutral RSI
        assert rsi == 50.0
    
    def test_calculate_rsi_empty_data(self, analyzer):
        """Test RSI calculation with empty data"""
        prices = pd.Series([])
        rsi = analyzer.calculate_rsi(prices)
        
        # Should return neutral RSI
        assert rsi == 50.0
    
    def test_assess_data_quality_high(self, analyzer, sample_short_data, sample_price_data):
        """Test data quality assessment - high quality"""
        quality = analyzer.assess_data_quality('AAPL', sample_short_data, sample_price_data)
        assert quality == 'high'
    
    def test_assess_data_quality_medium(self, analyzer, sample_price_data):
        """Test data quality assessment - medium quality"""
        # Missing some short interest fields
        incomplete_short_data = {
            'short_percent_of_float': 25.0,
            'short_ratio': None,  # Missing
            'float_shares': 100000000,
            'average_daily_volume': None  # Missing
        }
        
        quality = analyzer.assess_data_quality('AAPL', incomplete_short_data, sample_price_data)
        assert quality == 'medium'
    
    def test_assess_data_quality_insufficient(self, analyzer):
        """Test data quality assessment - insufficient quality"""
        empty_short_data = {}
        empty_price_data = pd.DataFrame()
        
        quality = analyzer.assess_data_quality('AAPL', empty_short_data, empty_price_data)
        assert quality == 'insufficient'
    
    def test_get_short_interest_data_success(self, analyzer, sample_short_data):
        """Test successful short interest data retrieval"""
        # Mock database response
        mock_row = MagicMock()
        mock_row.symbol = sample_short_data['symbol']
        mock_row.report_date = sample_short_data['report_date']
        mock_row.short_interest = sample_short_data['short_interest']
        mock_row.float_shares = sample_short_data['float_shares']
        mock_row.short_ratio = sample_short_data['short_ratio']
        mock_row.short_percent_of_float = sample_short_data['short_percent_of_float']
        mock_row.average_daily_volume = sample_short_data['average_daily_volume']
        
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        analyzer.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        result = analyzer.get_short_interest_data('AAPL')
        
        assert result['symbol'] == 'AAPL'
        assert result['short_percent_of_float'] == 25.0
        assert result['short_ratio'] == 5.0
    
    def test_get_short_interest_data_not_found(self, analyzer):
        """Test short interest data retrieval when no data found"""
        # Mock empty database response
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        analyzer.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        result = analyzer.get_short_interest_data('INVALID')
        
        assert result == {}
    
    def test_calculate_squeeze_score_complete_data(self, analyzer):
        """Test squeeze score calculation with complete data"""
        # Mock all required data
        with patch.object(analyzer, 'get_short_interest_data') as mock_short, \
             patch.object(analyzer, 'get_historical_prices') as mock_prices, \
             patch.object(analyzer, 'calculate_rsi') as mock_rsi, \
             patch.object(analyzer, 'calculate_relative_volume') as mock_rvol:
            
            mock_short.return_value = {
                'symbol': 'GME',
                'short_percent_of_float': 30.0,  # High short interest
                'short_ratio': 8.0,              # High days to cover
                'float_shares': 50_000_000,      # Medium float
                'average_daily_volume': 10_000_000,  # Include for high quality
                'report_date': date.today()
            }
            
            mock_prices.return_value = pd.DataFrame({
                'close': [100 + i for i in range(20)]  # Sufficient for RSI
            })
            
            mock_rsi.return_value = 25.0  # Oversold
            mock_rvol.return_value = 3.0  # High relative volume
            
            result = analyzer.calculate_squeeze_score('GME')
            
            assert result['symbol'] == 'GME'
            assert result['squeeze_score'] is not None
            assert result['squeeze_score'] > 0
            assert result['data_quality'] == 'high'
            assert 'si_score' in result
            assert 'dtc_score' in result
            assert 'float_score' in result
            assert 'momentum_score' in result
    
    def test_calculate_squeeze_score_insufficient_data(self, analyzer):
        """Test squeeze score calculation with insufficient data"""
        with patch.object(analyzer, 'get_short_interest_data') as mock_short:
            mock_short.return_value = {}  # No short interest data
            
            result = analyzer.calculate_squeeze_score('INVALID')
            
            assert result['symbol'] == 'INVALID'
            assert result['squeeze_score'] is None
            assert result['data_quality'] == 'insufficient'
            assert 'error' in result
    
    def test_calculate_batch_scores(self, analyzer):
        """Test batch score calculation"""
        with patch.object(analyzer, 'calculate_squeeze_score') as mock_calc:
            # Mock responses for different symbols
            mock_calc.side_effect = [
                {'symbol': 'AAPL', 'squeeze_score': 75.5, 'data_quality': 'high'},
                {'symbol': 'MSFT', 'squeeze_score': 45.0, 'data_quality': 'medium'},
                {'symbol': 'INVALID', 'squeeze_score': None, 'data_quality': 'insufficient', 'error': 'No data'}
            ]
            
            symbols = ['AAPL', 'MSFT', 'INVALID']
            results = analyzer.calculate_batch_scores(symbols)
            
            assert len(results) == 3
            assert results[0]['symbol'] == 'AAPL'
            assert results[1]['symbol'] == 'MSFT'
            assert results[2]['symbol'] == 'INVALID'
            
            # Verify calculation method was called for each symbol
            assert mock_calc.call_count == 3
    
    def test_store_squeeze_scores(self, analyzer):
        """Test storing squeeze scores to database"""
        results = [
            {
                'symbol': 'AAPL',
                'squeeze_score': 75.5,
                'si_score': 80.0,
                'dtc_score': 70.0,
                'float_score': 60.0,
                'momentum_score': 85.0,
                'data_quality': 'high'
            },
            {
                'symbol': 'MSFT',
                'squeeze_score': 45.0,
                'si_score': 40.0,
                'dtc_score': 50.0,
                'float_score': 30.0,
                'momentum_score': 55.0,
                'data_quality': 'medium'
            },
            {
                'symbol': 'INVALID',
                'squeeze_score': None,  # Should be skipped
                'data_quality': 'insufficient'
            }
        ]
        
        stored_count = analyzer.store_squeeze_scores(results)
        
        # Should store 2 valid scores and skip the invalid one
        assert stored_count == 2
        assert analyzer.db.insert_short_squeeze_score.call_count == 2
    
    def test_weighted_score_calculation(self, analyzer):
        """Test that the weighted score calculation follows SQUEEZE.md methodology"""
        # Test specific case where we can verify the calculation
        si_score = 80.0      # 40% weight
        dtc_score = 60.0     # 30% weight  
        float_score = 40.0   # 15% weight
        momentum_score = 20.0 # 15% weight
        
        expected_score = (si_score * 0.40) + (dtc_score * 0.30) + (float_score * 0.15) + (momentum_score * 0.15)
        expected_score = 32.0 + 18.0 + 6.0 + 3.0  # = 59.0
        
        # Mock the component calculations to return known values
        with patch.object(analyzer, 'get_short_interest_data') as mock_short, \
             patch.object(analyzer, 'get_historical_prices') as mock_prices, \
             patch.object(analyzer, 'normalize_si_score', return_value=si_score), \
             patch.object(analyzer, 'normalize_dtc_score', return_value=dtc_score), \
             patch.object(analyzer, 'normalize_float_score', return_value=float_score), \
             patch.object(analyzer, 'calculate_rsi', return_value=50.0), \
             patch.object(analyzer, 'calculate_relative_volume', return_value=2.0), \
             patch.object(analyzer, 'normalize_rsi_score', return_value=20.0), \
             patch.object(analyzer, 'normalize_rvol_score', return_value=20.0):
            
            mock_short.return_value = {
                'symbol': 'TEST',
                'short_percent_of_float': 25.0,
                'short_ratio': 5.0,
                'float_shares': 100_000_000,
                'report_date': date.today()
            }
            
            mock_prices.return_value = pd.DataFrame({'close': [100] * 20})
            
            result = analyzer.calculate_squeeze_score('TEST')
            
            assert result['squeeze_score'] == round(expected_score, 2)
            assert result['si_score'] == si_score
            assert result['dtc_score'] == dtc_score
            assert result['float_score'] == float_score
            assert result['momentum_score'] == momentum_score
    
    @pytest.mark.integration
    def test_short_squeeze_analyzer_integration(self, analyzer):
        """Integration test with database operations (marked as integration test)"""
        # This test uses real database operations but in the test environment
        test_symbol = "TSLA"
        
        # Mock database methods to simulate real data
        sample_short_data = {
            'symbol': test_symbol,
            'report_date': date.today(),
            'short_interest': 50000000,
            'float_shares': 300000000,
            'short_ratio': 5.0,
            'short_percent_of_float': 16.67,
            'average_daily_volume': 10000000
        }
        
        sample_price_data = pd.DataFrame({
            'date': pd.date_range(end=date.today(), periods=20, freq='D'),
            'close': [200 + i for i in range(20)],
            'volume': [8000000 + i * 100000 for i in range(20)]
        })
        
        with patch.object(analyzer, 'get_short_interest_data', return_value=sample_short_data), \
             patch.object(analyzer, 'get_historical_prices', return_value=sample_price_data), \
             patch.object(analyzer, 'calculate_relative_volume', return_value=1.2):
            
            # Test the complete calculation flow
            result = analyzer.calculate_squeeze_score(test_symbol)
            
            # Verify the result structure
            assert result['symbol'] == test_symbol
            assert result['squeeze_score'] is not None
            assert isinstance(result['squeeze_score'], float)
            assert 0 <= result['squeeze_score'] <= 100
            assert result['data_quality'] in ['high', 'medium', 'low', 'insufficient']
            
            # Verify all component scores are present
            assert 'si_score' in result
            assert 'dtc_score' in result
            assert 'float_score' in result
            assert 'momentum_score' in result
            assert 'raw_metrics' in result
            assert 'calculated_at' in result
            
            # Test storing the result
            if result['squeeze_score'] is not None:
                results = [result]
                stored_count = analyzer.store_squeeze_scores(results)
                assert stored_count == 1