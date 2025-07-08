import pytest
from flask import session
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, date, timedelta
import pandas as pd
import os

# Mock environment variables before importing app
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_PATH': ':memory:',
        'FMP_API_KEY': 'test_fmp_key'
    }):
        yield

# Import app and other modules after env vars are mocked
from app import app
from services import get_stock_service, get_fmp_client, get_undervaluation_analyzer, get_auth_manager, get_portfolio_manager
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
            # Ensure services are re-initialized for each test with mocks

            # Mock the underlying dependencies for services
            mock_db_manager = MagicMock()
            mock_db_manager.db_path = ":memory:"
            mock_db_manager.engine = MagicMock()
            mock_db_manager.engine.connect.return_value.__enter__.return_value = MagicMock()

            mock_stock_service_instance = MagicMock(spec=StockDataService)
            mock_stock_service_instance.db_manager = mock_db_manager
            mock_fmp_client_instance = MagicMock(spec=FMPClient)
            mock_undervaluation_analyzer_instance = MagicMock(spec=UndervaluationAnalyzer)
            mock_auth_manager_instance = MagicMock(spec=AuthenticationManager)
            mock_auth_manager_instance.db_path = ":memory:"
            mock_portfolio_manager_instance = MagicMock(spec=PortfolioManager)

            with patch.multiple(
                'services',
                get_stock_service=MagicMock(return_value=mock_stock_service_instance),
                get_fmp_client=MagicMock(return_value=mock_fmp_client_instance),
                get_undervaluation_analyzer=MagicMock(return_value=mock_undervaluation_analyzer_instance),
                get_auth_manager=MagicMock(return_value=mock_auth_manager_instance),
                get_portfolio_manager=MagicMock(return_value=mock_portfolio_manager_instance)
            ):
                # Call the getters to ensure the global instances in app.py are set
                get_stock_service()
                get_fmp_client()
                get_undervaluation_analyzer()
                get_auth_manager()
                get_portfolio_manager()

                # Mock internal dependencies of the mocked services if necessary
                mock_stock_service_instance.db_manager = mock_db_manager
                with patch('data_access_layer.DatabaseManager', return_value=mock_db_manager):
                    pass # This patch is needed for data_access_layer.py to use the mocked db_manager

                pass

        yield client

@pytest.fixture
def logged_in_client(client):
    # Mock the authentication manager to simulate a logged-in user
    auth_mgr = get_auth_manager()
    auth_mgr.authenticate_user.return_value = {
        'success': True,
        'user_id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'session_token': 'mock_session_token'
    }
    auth_mgr.validate_session.return_value = {
        'success': True,
        'user_id': 1,
        'username': 'testuser',
        'email': 'test@example.com'
    }

    # Perform a login request to set the session cookie
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'testuser'
        sess['email'] = 'test@example.com'
        sess['session_token'] = 'mock_session_token'
    
    yield client

# --- Test Web Routes ---

def test_index_route(client):
    stock_service = get_stock_service()
    stock_service.get_all_stocks_with_scores.return_value = [
        {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'sector': 'Technology', 'price': 170.0, 'market_cap': 2.8e12, 'undervaluation_score': 75.5, 'data_quality': 'high', 'has_profile': 1}
    ]
    stock_service.get_stock_summary_stats.return_value = {'total_stocks': 1, 'stocks_with_profiles': 1, 'unique_sectors': 1, 'sectors': ['Technology']}
    
    response = client.get('/')
    assert response.status_code == 200
    assert b"Apple Inc." in response.data
    assert b"Technology" in response.data

def test_stock_detail_route(client):
    stock_service = get_stock_service()
    fmp_client = get_fmp_client()

    stock_service.get_stock_basic_info.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'}
    stock_service.get_stock_company_profile.return_value = {'companyname': 'Apple Inc.', 'price': 170.0}
    stock_service.get_stock_undervaluation_score.return_value = {'undervaluation_score': 75.5}
    stock_service.get_stock_historical_prices.return_value = [{'date': '2023-01-01', 'close': 170.0}]
    fmp_client.api_key = "test_fmp_key"
    fmp_client.get_fundamentals_summary.return_value = {'pe_ratio': 30.0}
    fmp_client.get_price_targets.return_value = [{'priceTarget': 180.0}]

    response = client.get('/stock/AAPL')
    assert response.status_code == 200
    assert b"Apple Inc." in response.data
    assert b"Undervaluation Score: 75.5" in response.data
    assert b"PE Ratio: 30.0" in response.data

def test_stock_detail_not_found(client):
    stock_service = get_stock_service()
    stock_service.get_stock_basic_info.return_value = None

    response = client.get('/stock/NONEXISTENT')
    assert response.status_code == 200 # Renders error.html with 200 status
    assert b"Stock NONEXISTENT not found" in response.data

def test_sector_detail_route(client):
    stock_service = get_stock_service()
    stock_service.get_stocks_by_sector.return_value = [
        {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'sector': 'Technology', 'undervaluation_score': 75.5},
        {'symbol': 'MSFT', 'company_name': 'Microsoft Corp.', 'sector': 'Technology', 'undervaluation_score': 60.2}
    ]

    response = client.get('/sector/Technology')
    assert response.status_code == 200
    assert b"Sector: Technology" in response.data
    assert b"Apple Inc." in response.data
    assert b"Average Undervaluation Score: 67.85" in response.data # (75.5+60.2)/2

def test_sectors_overview_route(client):
    stock_service = get_stock_service()
    stock_service.get_sector_analysis.return_value = [
        {'sector': 'Technology', 'total_stocks': 2, 'stocks_with_scores': 2, 'avg_undervaluation_score': 67.85},
        {'sector': 'Financials', 'total_stocks': 1, 'stocks_with_scores': 1, 'avg_undervaluation_score': 50.0}
    ]

    response = client.get('/sectors')
    assert response.status_code == 200
    assert b"Technology" in response.data
    assert b"Financials" in response.data

def test_analysis_page_route(client):
    analyzer = get_undervaluation_analyzer()
    analyzer.get_cache_stats.return_value = {'total_entries': 10, 'valid_entries': 5, 'expired_entries': 5}
    analyzer.analyze_undervaluation.return_value = {
        'total_stocks': 100,
        'analyzed_stocks': 80,
        'highly_undervalued': 10,
        'avg_score': 65.0
    }

    response = client.get('/analysis')
    assert response.status_code == 200
    assert b"Undervaluation Analysis" in response.data
    assert b"Total Stocks: 100" in response.data
    assert b"Highly Undervalued: 10" in response.data

# --- Test API Routes (app.py) ---

def test_api_stocks_route(client):
    stock_service = get_stock_service()
    stock_service.get_all_stocks_with_scores.return_value = [
        {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'sector': 'Technology', 'price': 170.0, 'market_cap': 2.8e12, 'undervaluation_score': 75.5, 'data_quality': 'high'}
    ]

    response = client.get('/api/stocks')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['symbol'] == 'AAPL'
    assert data[0]['undervaluation_score'] == 75.5

def test_api_stock_detail_route(client):
    stock_service = get_stock_service()
    stock_service.get_stock_basic_info.return_value = {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'}
    stock_service.get_stock_company_profile.return_value = {'companyname': 'Apple Inc.', 'price': 170.0}
    stock_service.get_stock_undervaluation_score.return_value = {'undervaluation_score': 75.5}
    stock_service.get_stock_historical_prices.return_value = [{'date': '2023-01-01', 'close': 170.0}]

    response = client.get('/api/stock/AAPL')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['basic_info']['symbol'] == 'AAPL'
    assert data['undervaluation']['undervaluation_score'] == 75.5

def test_api_sectors_route(client):
    stock_service = get_stock_service()
    stock_service.get_sector_analysis.return_value = [
        {'sector': 'Technology', 'total_stocks': 2, 'avg_undervaluation_score': 67.85}
    ]

    response = client.get('/api/sectors')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['sector'] == 'Technology'

def test_api_run_analysis_route(client):
    analyzer = get_undervaluation_analyzer()
    analyzer.analyze_undervaluation.return_value = {'total_stocks': 100, 'analyzed_stocks': 100}
    analyzer.get_cache_stats.return_value = {'total_entries': 10, 'valid_entries': 10}

    response = client.post('/api/analysis/run', json={'force_refresh': True})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['summary']['total_stocks'] == 100

# --- Authentication Routes ---

def test_register_get(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b"Register" in response.data

def test_register_post_success(client):
    auth_mgr = get_auth_manager()
    auth_mgr.register_user.return_value = {'success': True, 'user_id': 1}

    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration successful! Please log in." in response.data
    assert b"Login" in response.data # Redirects to login page

def test_register_post_password_mismatch(client):
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123',
        'confirm_password': 'password_mismatch'
    })
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data

def test_register_post_failure(client):
    auth_mgr = get_auth_manager()
    auth_mgr.register_user.return_value = {'success': False, 'error': 'Username already exists'}

    response = client.post('/register', data={
        'username': 'existinguser',
        'email': 'existing@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert response.status_code == 200
    assert b"Username already exists" in response.data

def test_login_get(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Login" in response.data

def test_login_post_success(client):
    auth_mgr = get_auth_manager()
    auth_mgr.authenticate_user.return_value = {
        'success': True,
        'user_id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'session_token': 'mock_session_token'
    }

    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, testuser!" in response.data
    assert b"S&P 500 Stocks" in response.data # Redirects to index

    with client.session_transaction() as sess:
        assert sess['user_id'] == 1
        assert sess['username'] == 'testuser'

def test_login_post_failure(client):
    auth_mgr = get_auth_manager()
    auth_mgr.authenticate_user.return_value = {'success': False, 'error': 'Invalid credentials'}

    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    })
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data

def test_logout_route(logged_in_client):
    auth_mgr = get_auth_manager()
    auth_mgr.logout_user.return_value = True

    response = logged_in_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out successfully." in response.data
    assert b"S&P 500 Stocks" in response.data # Redirects to index

    with logged_in_client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_profile_route_logged_in(logged_in_client):
    auth_mgr = get_auth_manager()
    # Mock the sqlite3.connect and cursor for profile route
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [
        ("2023-01-01T10:00:00", "2023-07-01T15:00:00"), # user_data
        (5,) # watchlist_count
    ]
    with patch('app.sqlite3.connect', return_value=mock_conn):
        response = logged_in_client.get('/profile')
        assert response.status_code == 200
        assert b"User Profile" in response.data
        assert b"Member Since: 2023-01-01" in response.data
        assert b"Last Login: 2023-07-01" in response.data
        assert b"Watchlist Items: 5" in response.data

def test_profile_route_not_logged_in(client):
    response = client.get('/profile', follow_redirects=True)
    assert response.status_code == 200
    assert b"Please log in to access this page." in response.data
    assert b"Login" in response.data

def test_change_password_post_success(logged_in_client):
    auth_mgr = get_auth_manager()
    auth_mgr.verify_password.return_value = True
    auth_mgr.generate_password_hash.return_value = ("new_hash", "new_salt")

    # Mock sqlite3 operations for change_password
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = ("old_hash", "old_salt")
    with patch('app.sqlite3.connect', return_value=mock_conn):
        response = logged_in_client.post('/change_password', data={
            'current_password': 'oldpassword',
            'new_password': 'newpassword123',
            'confirm_new_password': 'newpassword123'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Password changed successfully" in response.data
        mock_cursor.execute.assert_any_call('UPDATE users SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP\n            WHERE id = ?',
            ('new_hash', 'new_salt', 1))

def test_change_password_post_mismatch(logged_in_client):
    response = logged_in_client.post('/change_password', data={
        'current_password': 'oldpassword',
        'new_password': 'newpassword123',
        'confirm_new_password': 'mismatch'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"New passwords do not match" in response.data

def test_watchlist_route(logged_in_client):
    # Mock sqlite3 operations for watchlist
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        ('AAPL', 'Great stock', '2023-01-01T10:00:00', 'Apple Inc.', 170.0, 'Technology', 75.5, 'Apple Inc.'),
        ('MSFT', 'Software giant', '2023-01-02T11:00:00', 'Microsoft Corp.', 400.0, 'Technology', 60.2, 'Microsoft Corp.')
    ]
    with patch('app.sqlite3.connect', return_value=mock_conn):
        response = logged_in_client.get('/watchlist')
        assert response.status_code == 200
        assert b"My Watchlist" in response.data
        assert b"Apple Inc." in response.data
        assert b"Microsoft Corp." in response.data
        assert b"Great stock" in response.data

def test_add_to_watchlist_post_success(logged_in_client):
    stock_service = get_stock_service()
    stock_service.get_stock_basic_info.return_value = {'symbol': 'GOOG', 'name': 'Alphabet Inc.'}

    # Mock sqlite3 operations for add_to_watchlist
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch('app.sqlite3.connect', return_value=mock_conn):
        response = logged_in_client.post('/add_to_watchlist', data={
            'symbol': 'GOOG',
            'notes': 'Good long-term hold'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"GOOG added to your watchlist" in response.data
        mock_cursor.execute.assert_called_with(
            '\n            INSERT OR REPLACE INTO user_watchlists (user_id, symbol, notes)\n            VALUES (?, ?, ?)\n        ', (1, 'GOOG', 'Good long-term hold'))

def test_remove_from_watchlist_post_success(logged_in_client):
    # Mock sqlite3 operations for remove_from_watchlist
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch('app.sqlite3.connect', return_value=mock_conn):
        response = logged_in_client.post('/remove_from_watchlist', json={'symbol': 'AAPL'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        mock_cursor.execute.assert_called_with(
            '\n            DELETE FROM user_watchlists WHERE user_id = ? AND symbol = ?\n        ', (1, 'AAPL'))

def test_update_watchlist_notes_post_success(logged_in_client):
    # Mock sqlite3 operations for update_watchlist_notes
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch('app.sqlite3.connect', return_value=mock_conn):
        response = logged_in_client.post('/update_watchlist_notes', data={
            'symbol': 'AAPL',
            'notes': 'Updated notes for Apple'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Notes updated for AAPL" in response.data
        mock_cursor.execute.assert_called_with(
            '\n            UPDATE user_watchlists SET notes = ? WHERE user_id = ? AND symbol = ?\n        ', ('Updated notes for Apple', 1, 'AAPL'))

# --- Portfolio Routes ---

def test_portfolio_route(logged_in_client):
    portfolio_mgr = get_portfolio_manager()
    portfolio_mgr.get_user_portfolio.return_value = {
        'holdings': [
            {'symbol': 'AAPL', 'shares': 10, 'current_value': 1700, 'gain_loss': 200}
        ],
        'summary': {'total_holdings': 1, 'total_value': 1700, 'total_cost': 1500, 'total_gain_loss': 200, 'total_gain_loss_pct': 13.33}
    }
    portfolio_mgr.get_user_transactions.return_value = [
        {'symbol': 'AAPL', 'transaction_type': 'BUY', 'shares': 10, 'price_per_share': 150, 'total_amount': 1500, 'transaction_date': date(2023,1,1)}
    ]

    response = logged_in_client.get('/portfolio')
    assert response.status_code == 200
    assert b"My Portfolio" in response.data
    assert b"AAPL" in response.data
    assert b"Total Value: $1,700.00" in response.data

def test_add_portfolio_transaction_post_success(logged_in_client):
    portfolio_mgr = get_portfolio_manager()
    stock_service = get_stock_service()
    stock_service.get_stock_basic_info.return_value = {'symbol': 'GOOG', 'name': 'Alphabet Inc.'}
    portfolio_mgr.add_transaction.return_value = {'success': True, 'transaction_id': 1}

    response = logged_in_client.post('/add_portfolio_transaction', data={
        'transaction_type': 'BUY',
        'symbol': 'GOOG',
        'shares': 5.0,
        'price_per_share': 100.0,
        'transaction_date': '2023-01-01',
        'fees': 2.0,
        'notes': 'First buy of GOOG'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"BUY transaction for GOOG added successfully" in response.data
    portfolio_mgr.add_transaction.assert_called_once()

def test_portfolio_transactions_route(logged_in_client):
    portfolio_mgr = get_portfolio_manager()
    portfolio_mgr.get_user_transactions.return_value = [
        {'id': 1, 'symbol': 'AAPL', 'transaction_type': 'BUY', 'shares': 10, 'price_per_share': 150, 'total_amount': 1500, 'transaction_date': date(2023,1,1)}
    ]

    response = logged_in_client.get('/portfolio/transactions')
    assert response.status_code == 200
    assert b"Transaction History" in response.data
    assert b"AAPL" in response.data

def test_delete_portfolio_transaction_post_success(logged_in_client):
    portfolio_mgr = get_portfolio_manager()
    portfolio_mgr.delete_transaction.return_value = {'success': True}

    response = logged_in_client.post('/delete_portfolio_transaction', json={'transaction_id': 123})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    portfolio_mgr.delete_transaction.assert_called_once_with(1, 123)

def test_export_transactions_csv(logged_in_client):
    portfolio_mgr = get_portfolio_manager()
    portfolio_mgr.get_user_transactions.return_value = [
        {'id': 1, 'symbol': 'AAPL', 'transaction_type': 'BUY', 'shares': 10, 'price_per_share': 150, 'total_amount': 1500, 'transaction_date': date(2023,1,1), 'fees': 5.0, 'notes': 'test'}
    ]

    response = logged_in_client.get('/export_transactions?format=csv')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert b'Date,Type,Symbol,Shares,Price per Share,Fees,Total Amount,Notes\r\n' in response.data
    assert b'2023-01-01,BUY,AAPL,10.0,150.0,5.0,1500.0,test\r\n' in response.data

def test_export_transactions_pdf_not_implemented(logged_in_client):
    response = logged_in_client.get('/export_transactions?format=pdf', follow_redirects=True)
    assert response.status_code == 200
    assert b"PDF export not yet implemented" in response.data

# --- Error Handlers ---

def test_404_error_handler(client):
    response = client.get('/nonexistent_page')
    assert response.status_code == 404
    assert b"Page not found" in response.data

def test_500_error_handler(client):
    # Simulate an internal server error by making a service call fail
    stock_service = get_stock_service()
    stock_service.get_all_stocks_with_scores.side_effect = Exception("Simulated DB error")

    response = client.get('/') # Trigger the index route which calls get_all_stocks_with_scores
    assert response.status_code == 500
    assert b"Internal server error" in response.data