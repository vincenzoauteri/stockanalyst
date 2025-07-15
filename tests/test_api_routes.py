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
        mock_stock_service.get_stocks_count.return_value = 2  # Mock the count method
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
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'price': 170.0, 'mktcap': 2.8e12, 'undervaluation_score': 75.5},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'Technology', 'price': 400.0, 'mktcap': 3.0e12, 'undervaluation_score': 60.2}
        ]
        mock_stock_service.get_stocks_count.return_value = 2
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
        assert "Internal server error" in data['error']  # Generic error message for security

# --- Additional Edge Cases and Error Handling Tests ---

def test_api_v2_get_stocks_invalid_parameters(client):
    """Test API stocks endpoint with edge case parameters"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stocks_count.return_value = 0
        mock_stock_service.get_all_stocks_with_scores.return_value = []
        mock_get_service.return_value = mock_stock_service

        # Test that API handles invalid parameters gracefully (Flask converts to None/defaults)
        response = client.get('/api/v2/stocks?page=invalid&min_score=invalid')
        assert response.status_code == 200  # Flask handles gracefully
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 0

def test_api_v2_get_stocks_service_unavailable(client):
    """Test API stocks endpoint when service is unavailable"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_get_service.side_effect = AttributeError("Service method not available")

        response = client.get('/api/v2/stocks')
        assert response.status_code == 503
        data = json.loads(response.data)
        assert not data['success']
        assert 'Service temporarily unavailable' in data['error']

def test_api_v2_get_stocks_connection_error(client):
    """Test API stocks endpoint with database connection error"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_get_service.side_effect = ConnectionError("Database connection failed")

        response = client.get('/api/v2/stocks')
        assert response.status_code == 503
        data = json.loads(response.data)
        assert not data['success']
        assert 'Database connection error' in data['error']

def test_api_v2_get_stocks_empty_result(client):
    """Test API stocks endpoint with empty results"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = []
        mock_stock_service.get_stocks_count.return_value = 0
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 0
        assert data['pagination']['total_count'] == 0

def test_api_v2_get_stocks_malformed_data(client):
    """Test API stocks endpoint with malformed stock data"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'price': 170.0},
            {'invalid': 'data'},  # Malformed entry
            None,  # None entry
        ]
        mock_stock_service.get_stocks_count.return_value = 3
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) >= 1  # At least valid entry should be included
        assert data['data'][0]['symbol'] == 'AAPL'

def test_api_v2_get_stock_history_no_data(client):
    """Test API stock history endpoint with no historical data"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stock_historical_prices.return_value = None
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/history')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert not data['success']
        assert 'No historical data found' in data['error']

def test_api_v2_get_stock_undervaluation_not_found(client):
    """Test API stock undervaluation endpoint with no data"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_stock_undervaluation_score.return_value = None
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/analysis/undervaluation/AAPL')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert not data['success']
        assert 'No undervaluation data found' in data['error']

def test_api_v2_get_undervaluation_summary_no_scores(client):
    """Test API undervaluation summary with no scores available"""
    with patch('api_routes.get_undervaluation_analyzer') as mock_get_analyzer, \
         patch('api_routes.get_stock_service') as mock_get_service:
        mock_analyzer = MagicMock()
        mock_stock_service = MagicMock()
        mock_analyzer.get_cache_stats.return_value = {'total_entries': 0, 'valid_entries': 0}
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'undervaluation_score': None},
            {'no_score_field': 'data'}
        ]
        mock_get_analyzer.return_value = mock_analyzer
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/analysis/undervaluation')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['stocks_with_scores'] == 0
        assert 'No undervaluation scores available' in data['data']['message']

def test_api_v2_health_check_unhealthy(client):
    """Test API health check when system is unhealthy"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_get_service.side_effect = Exception("Database connection failed")

        response = client.get('/api/v2/health')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert not data['success']
        assert data['status'] == 'unhealthy'
        assert 'Database connection failed' in data['error']

# --- Financial Data Endpoints Tests ---

def test_api_v2_get_corporate_actions(client):
    """Test corporate actions endpoint for specific symbol"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_corporate_actions.return_value = [
            {'action_type': 'dividend', 'amount': 0.50, 'ex_date': date(2023, 3, 15)},
            {'action_type': 'split', 'split_ratio': '2:1', 'ex_date': date(2023, 6, 10)}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/corporate-actions?limit=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['symbol'] == 'AAPL'
        assert len(data['corporate_actions']) == 2
        assert data['count'] == 2
        assert data['corporate_actions'][0]['action_type'] == 'dividend'

def test_api_v2_get_all_corporate_actions(client):
    """Test getting all corporate actions across symbols"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_corporate_actions.return_value = [
            {'symbol': 'AAPL', 'action_type': 'dividend', 'amount': 0.50},
            {'symbol': 'MSFT', 'action_type': 'dividend', 'amount': 0.75}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/corporate-actions?limit=50')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['corporate_actions']) == 2
        assert data['count'] == 2

def test_api_v2_get_financial_statements(client):
    """Test comprehensive financial statements endpoint"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_income_statements.return_value = [
            {'period': 'Q4 2023', 'revenue': 1000000000, 'net_income': 200000000}
        ]
        mock_stock_service.get_balance_sheets.return_value = [
            {'period': 'Q4 2023', 'total_assets': 5000000000, 'total_equity': 2000000000}
        ]
        mock_stock_service.get_cash_flow_statements.return_value = [
            {'period': 'Q4 2023', 'operating_cash_flow': 300000000, 'free_cash_flow': 250000000}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/financial-statements?limit=3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['symbol'] == 'AAPL'
        assert len(data['data']['income_statements']) == 1
        assert len(data['data']['balance_sheets']) == 1
        assert len(data['data']['cash_flow_statements']) == 1

def test_api_v2_get_income_statements(client):
    """Test income statements endpoint"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_income_statements.return_value = [
            {'period': 'Q4 2023', 'revenue': 1000000000, 'net_income': 200000000, 'report_date': date(2023, 12, 31)}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/income-statements')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['symbol'] == 'AAPL'
        assert len(data['income_statements']) == 1
        assert data['income_statements'][0]['revenue'] == 1000000000
        assert data['income_statements'][0]['report_date'] == '2023-12-31'  # Date serialization

def test_api_v2_get_balance_sheets(client):
    """Test balance sheets endpoint"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_balance_sheets.return_value = [
            {'period': 'Q4 2023', 'total_assets': 5000000000, 'total_equity': 2000000000}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/balance-sheets')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['symbol'] == 'AAPL'
        assert len(data['balance_sheets']) == 1
        assert data['balance_sheets'][0]['total_assets'] == 5000000000

def test_api_v2_get_cash_flow_statements(client):
    """Test cash flow statements endpoint"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_cash_flow_statements.return_value = [
            {'period': 'Q4 2023', 'operating_cash_flow': 300000000, 'free_cash_flow': 250000000}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/cash-flow-statements')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['symbol'] == 'AAPL'
        assert len(data['cash_flow_statements']) == 1
        assert data['cash_flow_statements'][0]['operating_cash_flow'] == 300000000

def test_api_v2_get_analyst_recommendations(client):
    """Test analyst recommendations endpoint"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_analyst_recommendations.return_value = [
            {'period': '2023-12', 'strong_buy': 15, 'buy': 10, 'hold': 5, 'sell': 2, 'strong_sell': 1}
        ]
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/analyst-recommendations')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['symbol'] == 'AAPL'
        assert len(data['analyst_recommendations']) == 1
        assert data['analyst_recommendations'][0]['strong_buy'] == 15

def test_api_v2_get_financial_summary(client):
    """Test comprehensive financial summary endpoint"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_financial_summary.return_value = {
            'symbol': 'AAPL',
            'financial_health': 'Strong',
            'recent_revenue': 1000000000,
            'recent_net_income': 200000000,
            'debt_to_equity': 0.5,
            'current_ratio': 1.2
        }
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/financial-summary')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['symbol'] == 'AAPL'
        assert data['data']['financial_health'] == 'Strong'
        assert data['data']['recent_revenue'] == 1000000000

def test_api_v2_financial_endpoints_error_handling(client):
    """Test error handling in financial data endpoints"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_corporate_actions.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks/AAPL/corporate-actions')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert not data['success']
        assert 'Database error' in data['error']

# --- Portfolio Transactions Filtering Tests ---

def test_api_v2_get_portfolio_transactions_filtered(logged_in_client):
    """Test portfolio transactions with filtering"""
    with patch('api_routes.get_portfolio_manager') as mock_get_manager:
        mock_portfolio_mgr = MagicMock()
        mock_portfolio_mgr.get_user_transactions.return_value = [
            {'id': 1, 'symbol': 'AAPL', 'transaction_type': 'BUY', 'shares': 10, 'transaction_date': date(2023,1,1)},
            {'id': 2, 'symbol': 'AAPL', 'transaction_type': 'SELL', 'shares': 5, 'transaction_date': date(2023,2,1)},
            {'id': 3, 'symbol': 'MSFT', 'transaction_type': 'BUY', 'shares': 8, 'transaction_date': date(2023,3,1)}
        ]
        mock_get_manager.return_value = mock_portfolio_mgr

        # Test filtering by transaction type
        response = logged_in_client.get('/api/v2/portfolio/transactions?type=BUY')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 2  # Only BUY transactions
        assert all(t['transaction_type'] == 'BUY' for t in data['data'])

def test_api_v2_portfolio_endpoints_authentication_required(client):
    """Test that portfolio endpoints require authentication"""
    endpoints = [
        '/api/v2/portfolio',
        '/api/v2/portfolio/transactions',
        '/api/v2/portfolio/performance'
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 302  # Redirect to login

# --- Date Serialization Tests ---

def test_serialize_dates_in_dict_function():
    """Test the serialize_dates_in_dict utility function"""
    from api_routes import serialize_dates_in_dict
    
    test_data = {
        'date_field': date(2023, 1, 1),
        'datetime_field': datetime(2023, 1, 1, 10, 30, 0),
        'string_field': 'test',
        'number_field': 123,
        'nested_dict': {
            'inner_date': date(2023, 2, 1)
        },
        'list_field': [
            {'item_date': date(2023, 3, 1)},
            'string_item',
            456
        ]
    }
    
    result = serialize_dates_in_dict(test_data)
    
    assert result['date_field'] == '2023-01-01'
    assert result['datetime_field'] == '2023-01-01T10:30:00'
    assert result['string_field'] == 'test'
    assert result['number_field'] == 123
    assert result['nested_dict']['inner_date'] == '2023-02-01'
    assert result['list_field'][0]['item_date'] == '2023-03-01'
    assert result['list_field'][1] == 'string_item'
    assert result['list_field'][2] == 456

# --- Sort Type Error Handling Tests ---

def test_api_v2_get_stocks_sort_type_error(client):
    """Test API stocks endpoint with sort field type mismatch"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'symbol': 'AAPL', 'price': 170.0, 'undervaluation_score': 75.5},
            {'symbol': 'MSFT', 'price': 'N/A', 'undervaluation_score': 60.2}  # String price causing TypeError
        ]
        mock_stock_service.get_stocks_count.return_value = 2
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks?sort=price&order=desc')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 2  # Should still return data with fallback sorting

# --- Parameter Validation Edge Cases ---

def test_api_v2_get_stocks_parameter_edge_cases(client):
    """Test API stocks endpoint with edge case parameters"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'symbol': 'AAPL', 'sector': 'Technology', 'undervaluation_score': 75.5},
            {'symbol': 'MSFT', 'sector': 'technology', 'undervaluation_score': 60.2}  # Different case
        ]
        mock_stock_service.get_stocks_count.return_value = 2
        mock_get_service.return_value = mock_stock_service

        # Test case-insensitive sector filtering
        response = client.get('/api/v2/stocks?sector=TECHNOLOGY')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 2  # Both should match case-insensitive filter

def test_api_v2_get_stocks_limit_parameter(client):
    """Test API stocks endpoint with limit parameter"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.get_all_stocks_with_scores.return_value = [
            {'symbol': 'AAPL', 'undervaluation_score': 75.5},
            {'symbol': 'MSFT', 'undervaluation_score': 60.2},
            {'symbol': 'GOOGL', 'undervaluation_score': 88.1}
        ]
        mock_stock_service.get_stocks_count.return_value = 3
        mock_get_service.return_value = mock_stock_service

        response = client.get('/api/v2/stocks?per_page=2')  # Use per_page instead of limit
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        # Note: Mock returns all data, service layer would normally handle limiting
        assert data['pagination']['per_page'] == 2

# --- Comprehensive Error Testing ---

def test_api_v2_all_endpoints_exception_handling(client, logged_in_client):
    """Test that all endpoints handle exceptions gracefully"""
    # Public endpoints that should return 500 on exception
    public_endpoints = [
        '/api/v2/stocks',
        '/api/v2/stocks/AAPL',
        '/api/v2/stocks/AAPL/history',
        '/api/v2/sectors',
        '/api/v2/analysis/undervaluation',
        '/api/v2/analysis/undervaluation/AAPL',
        '/api/v2/health',
        '/api/v2/stocks/AAPL/corporate-actions',
        '/api/v2/corporate-actions',
        '/api/v2/stocks/AAPL/financial-statements',
        '/api/v2/stocks/AAPL/income-statements',
        '/api/v2/stocks/AAPL/balance-sheets',
        '/api/v2/stocks/AAPL/cash-flow-statements',
        '/api/v2/stocks/AAPL/analyst-recommendations',
        '/api/v2/stocks/AAPL/financial-summary'
    ]
    
    # Endpoints that don't depend on services
    simple_endpoints = [
        '/api/v2/auth/status'
    ]
    
    # Authenticated endpoints that should return 500 on exception (after login)
    auth_endpoints = [
        '/api/v2/portfolio',
        '/api/v2/portfolio/transactions',
        '/api/v2/portfolio/performance'
    ]
    
    with patch('api_routes.get_stock_service') as mock_get_service, \
         patch('api_routes.get_portfolio_manager') as mock_get_portfolio:
        
        # Make all service calls raise exceptions
        mock_get_service.side_effect = Exception("Service error")
        mock_get_portfolio.side_effect = Exception("Portfolio error")
        
        # Test public endpoints
        for endpoint in public_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 500, f"Endpoint {endpoint} should return 500 on exception"
            data = json.loads(response.data)
            assert not data['success'], f"Endpoint {endpoint} should return success=False"
            assert 'error' in data, f"Endpoint {endpoint} should include error message"
        
        # Test simple endpoints that should work normally
        for endpoint in simple_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Endpoint {endpoint} should return 200 normally"
        
        # Test authenticated endpoints
        for endpoint in auth_endpoints:
            response = logged_in_client.get(endpoint)
            assert response.status_code == 500, f"Endpoint {endpoint} should return 500 on exception"
            data = json.loads(response.data)
            assert not data['success'], f"Endpoint {endpoint} should return success=False"
            assert 'error' in data, f"Endpoint {endpoint} should include error message"

def test_api_v2_get_symbols(client):
    """Test the symbols endpoint for stock comparison feature"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.db_manager.get_sp500_symbols.return_value = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'
        ]
        mock_get_service.return_value = mock_stock_service
        
        response = client.get('/api/v2/symbols')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'data' in data
        assert len(data['data']) == 5
        assert 'AAPL' in data['data']
        assert 'count' in data
        assert data['count'] == 5

def test_api_v2_get_symbols_error(client):
    """Test symbols endpoint error handling"""
    with patch('api_routes.get_stock_service') as mock_get_service:
        mock_stock_service = MagicMock()
        mock_stock_service.db_manager.get_sp500_symbols.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_stock_service
        
        response = client.get('/api/v2/symbols')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'error' in data
        assert 'message' in data
