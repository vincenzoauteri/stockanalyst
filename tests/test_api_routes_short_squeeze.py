#!/usr/bin/env python3
"""
Test suite for Short Squeeze API endpoints
Tests the API routes for short squeeze analysis functionality
"""

import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, date
import os

# Mock environment variables before importing app and api_routes
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key',
        'FMP_API_KEY': 'test_fmp_key'
    }):
        yield

# Import app and api_v2 after env vars are mocked
from app import app
from api_routes import api_v2

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            # Only register blueprint if not already registered
            if 'api_v2' not in app.blueprints:
                app.register_blueprint(api_v2)
            yield client

@pytest.fixture
def mock_squeeze_rankings():
    return [
        {
            'symbol': 'GME',
            'company_name': 'GameStop Corp.',
            'sector': 'Consumer Discretionary',
            'price': 150.50,
            'market_cap': 4.5e9,
            'squeeze_score': 85.5,
            'si_score': 90.0,
            'dtc_score': 85.0,
            'float_score': 80.0,
            'momentum_score': 75.0,
            'data_quality': 'high',
            'calculated_at': '2025-07-13T10:00:00',
            'short_percent_of_float': 35.5,
            'short_ratio': 8.5,
            'float_shares': 50000000,
            'report_date': '2025-07-10'
        },
        {
            'symbol': 'AMC',
            'company_name': 'AMC Entertainment Holdings Inc.',
            'sector': 'Consumer Discretionary',
            'price': 8.75,
            'market_cap': 1.2e9,
            'squeeze_score': 72.3,
            'si_score': 75.0,
            'dtc_score': 70.0,
            'float_score': 85.0,
            'momentum_score': 60.0,
            'data_quality': 'medium',
            'calculated_at': '2025-07-13T10:00:00',
            'short_percent_of_float': 28.0,
            'short_ratio': 6.2,
            'float_shares': 40000000,
            'report_date': '2025-07-10'
        }
    ]

@pytest.fixture
def mock_squeeze_stats():
    return {
        'total_scores': 50,
        'high_quality_scores': 25,
        'medium_quality_scores': 20,
        'low_quality_scores': 5,
        'avg_squeeze_score': 45.8,
        'max_squeeze_score': 85.5,
        'high_risk_count': 5,
        'medium_risk_count': 15,
        'low_risk_count': 30,
        'total_short_interest_records': 45,
        'avg_short_percent': 15.5,
        'max_short_percent': 35.5
    }

@pytest.fixture
def mock_short_interest_data():
    return [
        {
            'symbol': 'GME',
            'company_name': 'GameStop Corp.',
            'report_date': '2025-07-10',
            'short_interest': 17750000,
            'float_shares': 50000000,
            'short_ratio': 8.5,
            'short_percent_of_float': 35.5,
            'average_daily_volume': 2088235,
            'created_at': '2025-07-13T08:00:00'
        },
        {
            'symbol': 'AMC',
            'company_name': 'AMC Entertainment Holdings Inc.',
            'report_date': '2025-07-10',
            'short_interest': 11200000,
            'float_shares': 40000000,
            'short_ratio': 6.2,
            'short_percent_of_float': 28.0,
            'average_daily_volume': 1806452,
            'created_at': '2025-07-13T08:00:00'
        }
    ]

@pytest.fixture
def mock_comprehensive_squeeze_data():
    return {
        'symbol': 'GME',
        'short_interest': {
            'symbol': 'GME',
            'report_date': '2025-07-10',
            'short_interest': 17750000,
            'float_shares': 50000000,
            'short_ratio': 8.5,
            'short_percent_of_float': 35.5,
            'average_daily_volume': 2088235,
            'created_at': '2025-07-13T08:00:00',
            'updated_at': '2025-07-13T08:00:00'
        },
        'squeeze_score': {
            'symbol': 'GME',
            'squeeze_score': 85.5,
            'si_score': 90.0,
            'dtc_score': 85.0,
            'float_score': 80.0,
            'momentum_score': 75.0,
            'data_quality': 'high',
            'raw_metrics': {
                'short_percent_of_float': 35.5,
                'days_to_cover': 8.5,
                'float_shares': 50000000,
                'rsi': 25.5,
                'relative_volume': 3.2,
                'report_date': '2025-07-10'
            },
            'calculated_at': '2025-07-13T10:00:00',
            'created_at': '2025-07-13T10:00:00',
            'updated_at': '2025-07-13T10:00:00'
        },
        'basic_info': {
            'symbol': 'GME',
            'name': 'GameStop Corp.',
            'sector': 'Consumer Discretionary',
            'sub_sector': 'Specialty Retail',
            'headquarters': 'Grapevine, Texas'
        },
        'profile': {
            'symbol': 'GME',
            'price': 150.50,
            'mktcap': 4.5e9,
            'companyname': 'GameStop Corp.',
            'industry': 'Specialty Retail',
            'website': 'https://www.gamestop.com'
        },
        'data_availability': {
            'has_short_interest': True,
            'has_squeeze_score': True,
            'has_basic_info': True,
            'has_profile': True
        }
    }

class TestShortSqueezeRankingsAPI:
    """Test short squeeze rankings endpoint"""
    
    def test_get_squeeze_rankings_success(self, client, mock_squeeze_rankings):
        """Test successful squeeze rankings retrieval"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_rankings.return_value = mock_squeeze_rankings
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/rankings')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['data']) == 2
            assert data['data'][0]['symbol'] == 'GME'
            assert data['data'][0]['squeeze_score'] == 85.5
            assert data['count'] == 2
            
            # Verify service was called with default parameters
            mock_stock_service.get_short_squeeze_rankings.assert_called_once_with(
                limit=50,
                order_by='squeeze_score',
                min_score=None,
                min_data_quality=None
            )
    
    def test_get_squeeze_rankings_with_filters(self, client, mock_squeeze_rankings):
        """Test squeeze rankings with query parameters"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_rankings.return_value = mock_squeeze_rankings
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/rankings?limit=25&order_by=si_score&min_score=70.0&min_data_quality=high')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['filters']['limit'] == 25
            assert data['filters']['order_by'] == 'si_score'
            assert data['filters']['min_score'] == 70.0
            assert data['filters']['min_data_quality'] == 'high'
            
            mock_stock_service.get_short_squeeze_rankings.assert_called_once_with(
                limit=25,
                order_by='si_score',
                min_score=70.0,
                min_data_quality='high'
            )
    
    def test_get_squeeze_rankings_invalid_parameters(self, client):
        """Test squeeze rankings with invalid parameters"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_rankings.return_value = []
            mock_get_service.return_value = mock_stock_service
            
            # Test invalid limit (should be corrected to 50)
            response = client.get('/api/v2/squeeze/rankings?limit=1000')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['filters']['limit'] == 50
            
            # Test invalid order_by (should default to squeeze_score)
            response = client.get('/api/v2/squeeze/rankings?order_by=invalid_field')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['filters']['order_by'] == 'squeeze_score'
    
    def test_get_squeeze_rankings_service_error(self, client):
        """Test squeeze rankings endpoint with service error"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_rankings.side_effect = Exception("Database error")
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/rankings')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

class TestShortSqueezeStatsAPI:
    """Test short squeeze statistics endpoint"""
    
    def test_get_squeeze_stats_success(self, client, mock_squeeze_stats):
        """Test successful squeeze stats retrieval"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_summary_stats.return_value = mock_squeeze_stats
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/stats')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['total_scores'] == 50
            assert data['data']['avg_squeeze_score'] == 45.8
            assert data['data']['high_risk_count'] == 5
    
    def test_get_squeeze_stats_service_error(self, client):
        """Test squeeze stats endpoint with service error"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_summary_stats.side_effect = Exception("Database error")
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/stats')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

class TestShortInterestAPI:
    """Test short interest data endpoints"""
    
    def test_get_all_short_interest_success(self, client, mock_short_interest_data):
        """Test successful all short interest data retrieval"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_all_short_interest_data.return_value = mock_short_interest_data
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/short-interest')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['data']) == 2
            assert data['data'][0]['symbol'] == 'GME'
            assert data['data'][0]['short_percent_of_float'] == 35.5
            assert data['count'] == 2
            assert data['limit'] == 100
    
    def test_get_all_short_interest_with_limit(self, client, mock_short_interest_data):
        """Test all short interest data with custom limit"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_all_short_interest_data.return_value = mock_short_interest_data
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/short-interest?limit=25')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['limit'] == 25
            
            mock_stock_service.get_all_short_interest_data.assert_called_once_with(limit=25)

class TestStockSqueezeAPI:
    """Test individual stock squeeze analysis endpoints"""
    
    def test_get_stock_squeeze_analysis_success(self, client, mock_comprehensive_squeeze_data):
        """Test successful stock squeeze analysis retrieval"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_comprehensive_short_squeeze_data.return_value = mock_comprehensive_squeeze_data
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/stocks/GME/squeeze')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['symbol'] == 'GME'
            assert data['data']['squeeze_score']['squeeze_score'] == 85.5
            assert data['data']['data_availability']['has_squeeze_score'] is True
            
            mock_stock_service.get_comprehensive_short_squeeze_data.assert_called_once_with('GME')
    
    def test_get_stock_squeeze_analysis_not_found(self, client):
        """Test stock squeeze analysis for non-existent stock"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_comprehensive_short_squeeze_data.return_value = {}
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/stocks/INVALID/squeeze')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data
    
    def test_get_stock_short_interest_success(self, client):
        """Test successful stock short interest retrieval"""
        mock_short_interest = {
            'symbol': 'GME',
            'report_date': '2025-07-10',
            'short_interest': 17750000,
            'short_percent_of_float': 35.5,
            'short_ratio': 8.5
        }
        
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_interest_data.return_value = mock_short_interest
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/stocks/GME/short-interest')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['symbol'] == 'GME'
            assert data['data']['short_percent_of_float'] == 35.5
    
    def test_get_stock_short_interest_not_found(self, client):
        """Test stock short interest for stock with no data"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_interest_data.return_value = None
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/stocks/AAPL/short-interest')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data
    
    def test_get_stock_squeeze_score_success(self, client):
        """Test successful stock squeeze score retrieval"""
        mock_squeeze_score = {
            'symbol': 'GME',
            'squeeze_score': 85.5,
            'si_score': 90.0,
            'dtc_score': 85.0,
            'data_quality': 'high'
        }
        
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_score.return_value = mock_squeeze_score
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/stocks/GME/squeeze-score')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['symbol'] == 'GME'
            assert data['data']['squeeze_score'] == 85.5
            assert data['data']['data_quality'] == 'high'
    
    def test_get_stock_squeeze_score_not_found(self, client):
        """Test stock squeeze score for stock with no score"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_score.return_value = None
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/stocks/AAPL/squeeze-score')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data

class TestShortSqueezeAPIIntegration:
    """Integration tests for short squeeze API endpoints"""
    
    def test_squeeze_rankings_response_format(self, client, mock_squeeze_rankings):
        """Test that squeeze rankings response has correct format"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_stock_service = MagicMock()
            mock_stock_service.get_short_squeeze_rankings.return_value = mock_squeeze_rankings
            mock_get_service.return_value = mock_stock_service
            
            response = client.get('/api/v2/squeeze/rankings')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Check response structure
            assert 'success' in data
            assert 'data' in data
            assert 'count' in data
            assert 'filters' in data
            
            # Check data structure
            if data['data']:
                ranking = data['data'][0]
                required_fields = ['symbol', 'squeeze_score', 'si_score', 'dtc_score', 'float_score', 'momentum_score', 'data_quality']
                for field in required_fields:
                    assert field in ranking
    
    def test_squeeze_api_error_handling(self, client):
        """Test error handling across squeeze API endpoints"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_get_service.side_effect = Exception("Service unavailable")
            
            # Test all endpoints handle errors gracefully
            endpoints = [
                '/api/v2/squeeze/rankings',
                '/api/v2/squeeze/stats',
                '/api/v2/squeeze/short-interest',
                '/api/v2/stocks/GME/squeeze',
                '/api/v2/stocks/GME/short-interest',
                '/api/v2/stocks/GME/squeeze-score'
            ]
            
            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'error' in data

if __name__ == '__main__':
    pytest.main([__file__])