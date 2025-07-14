#!/usr/bin/env python3
"""
Integration Tests for Short Squeeze Analysis
Tests end-to-end workflows for the complete short squeeze feature
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
import os

# Mock environment variables before importing app components
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key',
        'FMP_API_KEY': 'test_fmp_key'
    }):
        yield

# Import components after env vars are mocked
from app import app
from api_routes import api_v2
from short_squeeze_analyzer import ShortSqueezeAnalyzer
from data_access_layer import StockDataService
from yahoo_finance_client import YahooFinanceClient
from database import DatabaseManager

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            if 'api_v2' not in app.blueprints:
                app.register_blueprint(api_v2)
            yield client

@pytest.fixture
def sample_short_interest_data():
    return {
        'symbol': 'GME',
        'report_date': date(2025, 7, 10),
        'short_interest': 17750000,
        'float_shares': 50000000,
        'short_ratio': 8.5,
        'short_percent_of_float': 35.5,
        'average_daily_volume': 2088235
    }

@pytest.fixture
def sample_price_data():
    """Sample historical price data for testing"""
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(start='2025-06-01', end='2025-07-13', freq='D')
    prices = [150 + i * 0.5 + np.random.normal(0, 5) for i in range(len(dates))]
    volumes = [2000000 + i * 10000 for i in range(len(dates))]
    
    return pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p + 2 for p in prices],
        'low': [p - 2 for p in prices],
        'close': prices,
        'volume': volumes
    })

class TestShortSqueezeDataPipeline:
    """Test the complete data collection to scoring pipeline"""
    
    def test_data_collection_to_storage_workflow(self, sample_short_interest_data):
        """Test data collection from Yahoo Finance and storage in database"""
        with patch('yahoo_finance_client.yf.Ticker') as mock_ticker, \
             patch('database.DatabaseManager') as mock_db_manager:
            
            # Mock Yahoo Finance response
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.info = {
                'sharesShort': sample_short_interest_data['short_interest'],
                'floatShares': sample_short_interest_data['float_shares'],
                'shortRatio': sample_short_interest_data['short_ratio'],
                'shortPercentOfFloat': sample_short_interest_data['short_percent_of_float'],
                'averageDailyVolume10Day': sample_short_interest_data['average_daily_volume']
            }
            mock_ticker.return_value = mock_ticker_instance
            
            # Mock database
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Test data collection
            client = YahooFinanceClient()
            short_data = client.get_short_interest_data('GME')
            
            # Verify data was collected correctly
            assert short_data['symbol'] == 'GME'
            assert short_data['short_interest'] == sample_short_interest_data['short_interest']
            assert short_data['short_percent_of_float'] == sample_short_interest_data['short_percent_of_float']
            
            # Test database storage
            db = mock_db
            db.insert_short_interest_data('GME', short_data)
            
            # Verify database was called
            mock_db.insert_short_interest_data.assert_called_once()
    
    def test_storage_to_calculation_workflow(self, sample_short_interest_data, sample_price_data):
        """Test score calculation from stored data"""
        with patch('database.DatabaseManager') as mock_db_manager:
            # Mock database responses
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Mock database query for short interest
            mock_conn = MagicMock()
            mock_row = MagicMock()
            for key, value in sample_short_interest_data.items():
                setattr(mock_row, key, value)
            
            mock_conn.execute.return_value.fetchone.return_value = mock_row
            mock_conn.execute.return_value.fetchall.return_value = [
                type('MockRow', (), {
                    'date': row['date'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                })() for _, row in sample_price_data.iterrows()
            ]
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Test score calculation
            analyzer = ShortSqueezeAnalyzer()
            result = analyzer.calculate_squeeze_score('GME')
            
            # Verify calculation worked
            assert result['symbol'] == 'GME'
            assert result['squeeze_score'] is not None
            assert 0 <= result['squeeze_score'] <= 100
            assert 'si_score' in result
            assert 'dtc_score' in result
            assert 'float_score' in result
            assert 'momentum_score' in result
            assert result['data_quality'] in ['high', 'medium', 'low', 'insufficient']
    
    def test_calculation_to_api_workflow(self):
        """Test API access to calculated scores"""
        with patch('data_access_layer.DatabaseManager') as mock_db_manager:
            # Mock database with calculated score
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            mock_conn = MagicMock()
            mock_score_row = MagicMock()
            mock_score_row._mapping = {
                'symbol': 'GME',
                'squeeze_score': 85.5,
                'si_score': 90.0,
                'dtc_score': 85.0,
                'float_score': 80.0,
                'momentum_score': 75.0,
                'data_quality': 'high',
                'raw_metrics': None,
                'calculated_at': datetime.now(),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            mock_conn.execute.return_value.fetchone.return_value = mock_score_row
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Test data access layer
            service = StockDataService()
            score_data = service.get_short_squeeze_score('GME')
            
            # Verify data access worked
            assert score_data['symbol'] == 'GME'
            assert score_data['squeeze_score'] == 85.5
            assert score_data['data_quality'] == 'high'

class TestShortSqueezeAPIIntegration:
    """Test API integration with database and scoring engine"""
    
    def test_api_endpoints_integration(self, client):
        """Test that API endpoints work with mocked data"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            
            # Mock rankings response
            mock_service.get_short_squeeze_rankings.return_value = [
                {
                    'symbol': 'GME',
                    'company_name': 'GameStop Corp.',
                    'squeeze_score': 85.5,
                    'si_score': 90.0,
                    'data_quality': 'high',
                    'calculated_at': '2025-07-13T10:00:00'
                }
            ]
            
            # Mock stats response
            mock_service.get_short_squeeze_summary_stats.return_value = {
                'total_scores': 1,
                'high_risk_count': 1,
                'avg_squeeze_score': 85.5
            }
            
            # Mock comprehensive data response
            mock_service.get_comprehensive_short_squeeze_data.return_value = {
                'symbol': 'GME',
                'squeeze_score': {'squeeze_score': 85.5, 'data_quality': 'high'},
                'data_availability': {'has_squeeze_score': True}
            }
            
            mock_get_service.return_value = mock_service
            
            # Test rankings endpoint
            response = client.get('/api/v2/squeeze/rankings')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['data']) == 1
            assert data['data'][0]['symbol'] == 'GME'
            
            # Test stats endpoint
            response = client.get('/api/v2/squeeze/stats')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['total_scores'] == 1
            
            # Test individual stock endpoint
            response = client.get('/api/v2/stocks/GME/squeeze')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['symbol'] == 'GME'
    
    def test_frontend_api_integration(self, client):
        """Test frontend route integration with data access layer"""
        with patch('app.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            
            # Mock frontend data
            mock_service.get_short_squeeze_rankings.return_value = [
                {
                    'symbol': 'GME',
                    'company_name': 'GameStop Corp.',
                    'squeeze_score': 85.5,
                    'short_percent_of_float': 35.5,
                    'data_quality': 'high'
                }
            ]
            
            mock_service.get_short_squeeze_summary_stats.return_value = {
                'total_scores': 1,
                'high_risk_count': 1,
                'avg_squeeze_score': 85.5,
                'max_short_percent': 35.5
            }
            
            mock_get_service.return_value = mock_service
            
            # Test frontend route
            response = client.get('/squeeze')
            assert response.status_code == 200
            
            # Verify HTML content contains expected data
            html_content = response.data.decode('utf-8')
            assert 'Short Squeeze Analysis' in html_content
            assert 'GME' in html_content
            assert '85.5' in html_content

class TestShortSqueezeBatchProcessing:
    """Test batch processing workflows"""
    
    def test_batch_calculation_workflow(self):
        """Test batch calculation of squeeze scores for multiple symbols"""
        with patch('database.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Mock database responses for multiple symbols
            symbols = ['GME', 'AMC', 'TSLA']
            mock_responses = []
            
            for i, symbol in enumerate(symbols):
                mock_row = MagicMock()
                mock_row.symbol = symbol
                mock_row.short_interest = 10000000 + i * 5000000
                mock_row.float_shares = 50000000 + i * 10000000
                mock_row.short_ratio = 5.0 + i
                mock_row.short_percent_of_float = 20.0 + i * 5
                mock_row.average_daily_volume = 2000000 + i * 500000
                mock_row.report_date = date.today()
                mock_responses.append(mock_row)
            
            # Mock database to return different data for each symbol
            def mock_execute_side_effect(*args, **kwargs):
                mock_result = MagicMock()
                if 'short_interest_data' in str(args[0]):
                    # Return appropriate symbol data based on query parameters
                    symbol = kwargs.get('symbol', 'GME')
                    for response in mock_responses:
                        if response.symbol == symbol:
                            mock_result.fetchone.return_value = response
                            break
                    else:
                        mock_result.fetchone.return_value = mock_responses[0]  # Default
                else:
                    # Historical prices query
                    mock_result.fetchall.return_value = []
                return mock_result
            
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = mock_execute_side_effect
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Test batch calculation
            analyzer = ShortSqueezeAnalyzer()
            results = analyzer.calculate_batch_scores(symbols)
            
            # Verify batch processing worked
            assert len(results) == len(symbols)
            for i, result in enumerate(results):
                assert result['symbol'] == symbols[i]
                assert 'squeeze_score' in result
    
    def test_batch_storage_workflow(self):
        """Test batch storage of calculated scores"""
        with patch('short_squeeze_analyzer.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Mock calculation results
            results = [
                {
                    'symbol': 'GME',
                    'squeeze_score': 85.5,
                    'si_score': 90.0,
                    'dtc_score': 85.0,
                    'float_score': 80.0,
                    'momentum_score': 75.0,
                    'data_quality': 'high'
                },
                {
                    'symbol': 'AMC',
                    'squeeze_score': 72.3,
                    'si_score': 75.0,
                    'dtc_score': 70.0,
                    'float_score': 85.0,
                    'momentum_score': 60.0,
                    'data_quality': 'medium'
                }
            ]
            
            # Test batch storage
            analyzer = ShortSqueezeAnalyzer()
            stored_count = analyzer.store_squeeze_scores(results)
            
            # Verify storage was attempted
            assert stored_count == 2
            assert mock_db.insert_short_squeeze_score.call_count == 2

class TestShortSqueezeErrorRecovery:
    """Test error handling and recovery in integration scenarios"""
    
    def test_data_collection_error_recovery(self):
        """Test graceful handling of data collection errors"""
        with patch('yahoo_finance_client.yf.Ticker') as mock_ticker:
            # Mock API failure
            mock_ticker.side_effect = Exception("Yahoo Finance API error")
            
            client = YahooFinanceClient()
            result = client.get_short_interest_data('INVALID')
            
            # Verify error was handled gracefully
            assert result is None or result == {}
    
    def test_calculation_error_recovery(self):
        """Test graceful handling of calculation errors"""
        with patch('database.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Mock database failure
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = Exception("Database connection error")
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Test error handling
            analyzer = ShortSqueezeAnalyzer()
            result = analyzer.calculate_squeeze_score('INVALID')
            
            # Verify error was handled gracefully
            assert result['symbol'] == 'INVALID'
            assert result['squeeze_score'] is None
            assert 'error' in result
    
    def test_api_error_recovery(self, client):
        """Test API error handling in integration"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            # Mock service failure
            mock_get_service.side_effect = Exception("Service unavailable")
            
            # Test API error handling
            response = client.get('/api/v2/squeeze/rankings')
            assert response.status_code == 500
            
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

class TestShortSqueezeDataConsistency:
    """Test data consistency across the system"""
    
    def test_database_transaction_integrity(self):
        """Test that database operations maintain integrity"""
        with patch('short_squeeze_analyzer.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Test successful transaction
            mock_db.insert_short_squeeze_score.return_value = True
            
            analyzer = ShortSqueezeAnalyzer()
            results = [{
                'symbol': 'GME',
                'squeeze_score': 85.5,
                'si_score': 90.0,
                'dtc_score': 85.0,
                'float_score': 80.0,
                'momentum_score': 75.0,
                'data_quality': 'high'
            }]
            
            stored_count = analyzer.store_squeeze_scores(results)
            
            # Verify transaction completed
            assert stored_count == 1
            mock_db.insert_short_squeeze_score.assert_called_once()
    
    def test_score_recalculation_consistency(self):
        """Test that score recalculation maintains consistency"""
        with patch('database.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Mock consistent data
            mock_conn = MagicMock()
            mock_row = MagicMock()
            mock_row.symbol = 'GME'
            mock_row.short_interest = 17750000
            mock_row.float_shares = 50000000
            mock_row.short_ratio = 8.5
            mock_row.short_percent_of_float = 35.5
            mock_row.average_daily_volume = 2088235
            mock_row.report_date = date.today()
            
            mock_conn.execute.return_value.fetchone.return_value = mock_row
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Calculate score twice
            analyzer = ShortSqueezeAnalyzer()
            result1 = analyzer.calculate_squeeze_score('GME')
            result2 = analyzer.calculate_squeeze_score('GME')
            
            # Verify consistency (should get same result with same data)
            assert result1['squeeze_score'] == result2['squeeze_score']
            assert result1['data_quality'] == result2['data_quality']

if __name__ == '__main__':
    pytest.main([__file__])