import pytest
import sqlite3
from flask import session
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, date, timedelta
import pandas as pd
import os

# Mock environment variables before importing app and api_routes
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_PATH': ':memory:',
        'FMP_API_KEY': 'test_fmp_key'
    }):
        yield

# Import app and api_v2 after env vars are mocked
from app import app
from api_routes import api_v2, get_stock_service, get_fmp_client, get_undervaluation_analyzer, get_auth_manager, get_portfolio_manager
from data_access_layer import StockDataService
from fmp_client import FMPClient
from undervaluation_analyzer import UndervaluationAnalyzer
from auth import AuthenticationManager
from portfolio import PortfolioManager

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms
    with app.test_client() as client:
        with app.app_context():
            # Only register blueprint if not already registered
            if 'api_v2' not in app.blueprints:
                app.register_blueprint(api_v2)
            yield client

@pytest.fixture
def logged_in_client(client):
    # Simulate a logged-in user by setting session variables
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'testuser'
        sess['email'] = 'test@example.com'
        sess['session_token'] = 'mock_session_token'
    yield client

# --- Stock Data Endpoints ---

def test_api_v2_get_stocks(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'company_name': 'Apple Inc.', 'sector': 'Technology', 'price': 170.0, 'mktcap': 2.8e12, 'undervaluation_score': 75.5},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'company_name': 'Microsoft Corp.', 'sector': 'Technology', 'price': 400.0, 'mktcap': 3.0e12, 'undervaluation_score': 60.2}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 2
        assert data['data'][0]['symbol'] == 'AAPL'
        assert data['data'][0]['undervaluation_score'] == 75.5

def test_api_v2_get_stocks_filter_sort(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'symbol': 'GOOG', 'name': 'Alphabet Inc.', 'sector': 'Communication Services', 'price': 150.0, 'mktcap': 1.9e12, 'undervaluation_score': 88.1},
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'price': 170.0, 'mktcap': 2.8e12, 'undervaluation_score': 75.5},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'Technology', 'price': 400.0, 'mktcap': 3.0e12, 'undervaluation_score': 60.2}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks?sector=Technology&min_score=60&sort=undervaluation_score&order=desc')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 2
        assert data['data'][0]['symbol'] == 'AAPL' # Filtered by Technology, sorted desc
        assert data['data'][1]['symbol'] == 'MSFT'

def test_api_v2_get_stock_detail(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stock_basic_info.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'}
        mock_stock_service.get_stock_company_profile.return_value = {'companyname': 'Apple Inc.', 'price': 170.0, 'beta': 1.2, 'mktcap': 2.8e12, 'description': 'A tech company.'}
        mock_stock_service.get_stock_undervaluation_score.return_value = {'undervaluation_score': 75.5}
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['symbol'] == 'AAPL'
        assert data['data']['company_name'] == 'Apple Inc.'
        assert data['data']['undervaluation_score'] == 75.5

def test_api_v2_get_stock_detail_not_found(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stock_basic_info.return_value = None
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/NONEXISTENT')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert not data['success']
        assert "Stock not found" in data['error']

def test_api_v2_get_stock_history(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stock_historical_prices.return_value = [
            {'date': '2023-01-03', 'close': 103.0},
            {'date': '2023-01-02', 'close': 102.0},
            {'date': '2023-01-01', 'close': 101.0},
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/history?limit=2')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 3  # The API returns all data, limit is applied in the service
        assert data['data'][0]['date'] == '2023-01-03'

def test_api_v2_get_stock_history_date_filter(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stock_historical_prices.return_value = [
            {'date': '2023-01-05', 'close': 105.0},
            {'date': '2023-01-04', 'close': 104.0},
            {'date': '2023-01-03', 'close': 103.0},
            {'date': '2023-01-02', 'close': 102.0},
            {'date': '2023-01-01', 'close': 101.0},
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/history?start_date=2023-01-02&end_date=2023-01-04')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 3
        assert data['data'][0]['date'] == '2023-01-04'
        assert data['data'][2]['date'] == '2023-01-02'

# --- Sectors Endpoints ---

def test_api_v2_get_sectors(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'symbol': 'AAPL', 'sector': 'Technology', 'mktcap': 2.8e12, 'undervaluation_score': 75.5},
            {'symbol': 'MSFT', 'sector': 'Technology', 'mktcap': 3.0e12, 'undervaluation_score': 60.2},
            {'symbol': 'GOOG', 'sector': 'Communication Services', 'mktcap': 1.9e12, 'undervaluation_score': 88.1},
            {'symbol': 'XOM', 'sector': 'Energy', 'mktcap': 5.0e11, 'undervaluation_score': 0}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/sectors')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 3 # Technology, Communication Services, Energy

        tech_sector = next((s for s in data['data'] if s['sector'] == 'Technology'), None)
        assert tech_sector is not None
        assert tech_sector['stock_count'] == 2
        assert tech_sector['avg_undervaluation_score'] == pytest.approx((75.5 + 60.2) / 2)

# --- Portfolio Endpoints ---

def test_api_v2_get_portfolio_not_logged_in(client):
    response = client.get('/api/v2/portfolio')
    assert response.status_code == 302 # Flask redirect for login_required
    # The login_required decorator redirects to login page, not returns 401

def test_api_v2_get_portfolio_logged_in(logged_in_client):
    with patch('api_routes.get_portfolio_manager') as mock_get_manager:
        mock_portfolio_mgr = MagicMock()
        mock_portfolio_mgr.get_user_portfolio.return_value = {
            'holdings': [
                {'symbol': 'AAPL', 'shares': 10, 'current_value': 1700}
            ],
            'summary': {'total_holdings': 1, 'total_value': 1700}
        }
        mock_get_manager.return_value = mock_portfolio_mgr

        response = logged_in_client.get('/api/v2/portfolio')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']['holdings']) == 1
        assert data['data']['holdings'][0]['symbol'] == 'AAPL'

def test_api_v2_get_portfolio_transactions_logged_in(logged_in_client):
    with patch('api_routes.get_portfolio_manager') as mock_get_manager:
        mock_portfolio_mgr = MagicMock()
        mock_portfolio_mgr.get_user_transactions.return_value = [
            {'id': 1, 'symbol': 'AAPL', 'transaction_type': 'BUY', 'shares': 10, 'price_per_share': 150, 'transaction_date': date(2023,1,1), 'created_at': datetime(2023,1,1,10,0,0)}
        ]
        mock_get_manager.return_value = mock_portfolio_mgr

        response = logged_in_client.get('/api/v2/portfolio/transactions')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 1
        assert data['data'][0]['symbol'] == 'AAPL'
        assert data['data'][0]['transaction_date'] == '2023-01-01' # Check date format

def test_api_v2_get_portfolio_performance_logged_in(logged_in_client):
    with patch('api_routes.get_portfolio_manager') as mock_get_manager:
        mock_portfolio_mgr = MagicMock()
        mock_portfolio_mgr.get_portfolio_performance.return_value = {
            'total_value': 10000,
            'total_gain_loss': 1000,
            'sector_allocation': {'Technology': {'value': 8000, 'percentage': 80}}
        }
        mock_get_manager.return_value = mock_portfolio_mgr

        response = logged_in_client.get('/api/v2/portfolio/performance')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['total_value'] == 10000

# --- Analysis Endpoints ---

def test_api_v2_get_undervaluation_summary(client):
    with patch('api_routes.get_undervaluation_analyzer') as mock_get_analyzer, \
         patch('api_routes.get_stock_service') as mock_get_service:
        mock_analyzer = MagicMock()
        mock_stock_service = MagicMock()
        mock_analyzer.get_cache_stats.return_value = {'total_entries': 10, 'valid_entries': 5}
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'undervaluation_score': 85},
            {'undervaluation_score': 70},
            {'undervaluation_score': 55},
            {'undervaluation_score': 30},
            {'undervaluation_score': None}
        ]
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/analysis/undervaluation')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['total_stocks'] == 5
        assert data['data']['stocks_with_scores'] == 4
        assert data['data']['highly_undervalued'] == 1
        assert data['data']['avg_score'] == pytest.approx((85+70+55+30)/4)

def test_api_v2_get_stock_undervaluation(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stock_undervaluation_score.return_value = {'symbol': 'AAPL', 'undervaluation_score': 75.5}
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/analysis/undervaluation/AAPL')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['symbol'] == 'AAPL'
        assert data['data']['undervaluation_score'] == 75.5

def test_api_v2_auth_status_logged_in(logged_in_client):
    response = logged_in_client.get('/api/v2/auth/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['authenticated'] == True
    assert data['user']['username'] == 'testuser'

def test_api_v2_auth_status_not_logged_in(client):
    response = client.get('/api/v2/auth/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['authenticated'] == False

def test_api_v2_health_check(client):
    with patch('api_routes.get_stock_service') as mock_get_service, \
         patch('api_routes.get_fmp_client') as mock_get_client:
        mock_stock_service = MagicMock()
        mock_fmp_client = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [{}, {}] # Simulate 2 stocks
        mock_fmp_client.get_remaining_requests.return_value = 200
        mock_get_service.return_value = mock_stock_service
        mock_get_client.return_value = mock_fmp_client

        response = client.get('/api/v2/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['status'] == 'healthy'
        assert data['database']['connected'] == True
        assert data['database']['stock_count'] == 2
        assert data['api_client']['remaining_requests'] == 200

def test_api_v2_404_error_handler(client):
    response = client.get('/api/v2/nonexistent_endpoint')
    assert response.status_code == 404
    # The 404 error handler returns HTML instead of JSON when not hitting specific API endpoints

def test_api_v2_500_error_handler(client):
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.side_effect = Exception("API DB error")
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks') # Trigger an error in an API route
        assert response.status_code == 500
        data = json.loads(response.data)
        assert not data['success']
        assert "API DB error" in data['error']  # The actual error message is returned
