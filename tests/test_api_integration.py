#!/usr/bin/env python3
"""
API Integration Tests - Comprehensive Testing
Tests actual API functionality with mocked services
"""

import os
import sys
import json
import requests
from datetime import date, datetime
from unittest.mock import patch, MagicMock

# Set environment variables before importing
os.environ.update({
    'SECRET_KEY': 'test-secret-key',
    'DATABASE_PATH': ':memory:',
    'FMP_API_KEY': 'test_fmp_key'
})

# Add the app directory to the path
sys.path.insert(0, '/app')

def test_api_stocks_endpoint():
    """Test /api/v2/stocks endpoint functionality"""
    from app import app
    
    with app.test_client() as client:
        with patch('services.get_stock_service') as mock_get_service:
            # Mock the stock service
            mock_service = MagicMock()
            mock_service.get_all_stocks_with_scores.return_value = [
                {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'company_name': 'Apple Inc.',
                    'sector': 'Technology',
                    'price': 170.0,
                    'mktcap': 2.8e12,
                    'undervaluation_score': 75.5
                },
                {
                    'symbol': 'MSFT',
                    'name': 'Microsoft Corp.',
                    'company_name': 'Microsoft Corp.',
                    'sector': 'Technology',
                    'price': 400.0,
                    'mktcap': 3.0e12,
                    'undervaluation_score': 60.2
                }
            ]
            mock_get_service.return_value = mock_service
            
            # Test basic endpoint
            response = client.get('/api/v2/stocks')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] == True
            assert len(data['data']) == 2
            assert data['data'][0]['symbol'] == 'AAPL'
            
            # Test with filters
            response = client.get('/api/v2/stocks?sector=Technology&min_score=60')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] == True
            assert len(data['data']) == 2
            
            print("✅ API stocks endpoint test passed")

def test_api_stock_detail_endpoint():
    """Test /api/v2/stocks/<symbol> endpoint functionality"""
    from app import app
    
    with app.test_client() as client:
        with patch('services.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_stock_basic_info.return_value = {
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'sector': 'Technology'
            }
            mock_service.get_stock_company_profile.return_value = {
                'companyname': 'Apple Inc.',
                'price': 170.0,
                'beta': 1.2,
                'mktcap': 2.8e12,
                'description': 'A tech company.'
            }
            mock_service.get_stock_undervaluation_score.return_value = {
                'undervaluation_score': 75.5
            }
            mock_get_service.return_value = mock_service
            
            response = client.get('/api/v2/stocks/AAPL')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['data']['symbol'] == 'AAPL'
            assert data['data']['undervaluation_score'] == 75.5
            
            print("✅ API stock detail endpoint test passed")

def test_api_financial_statements_endpoint():
    """Test /api/v2/stocks/<symbol>/financial-statements endpoint"""
    from app import app
    
    with app.test_client() as client:
        with patch('services.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_income_statements.return_value = [
                {'period': 'Q4 2023', 'revenue': 1000000000, 'net_income': 200000000}
            ]
            mock_service.get_balance_sheets.return_value = [
                {'period': 'Q4 2023', 'total_assets': 5000000000, 'total_equity': 2000000000}
            ]
            mock_service.get_cash_flow_statements.return_value = [
                {'period': 'Q4 2023', 'operating_cash_flow': 300000000}
            ]
            mock_get_service.return_value = mock_service
            
            response = client.get('/api/v2/stocks/AAPL/financial-statements')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['data']['symbol'] == 'AAPL'
            assert len(data['data']['income_statements']) == 1
            assert len(data['data']['balance_sheets']) == 1
            assert len(data['data']['cash_flow_statements']) == 1
            
            print("✅ API financial statements endpoint test passed")

def test_api_corporate_actions_endpoint():
    """Test /api/v2/stocks/<symbol>/corporate-actions endpoint"""
    from app import app
    
    with app.test_client() as client:
        with patch('services.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_corporate_actions.return_value = [
                {
                    'action_type': 'dividend',
                    'amount': 0.50,
                    'ex_date': date(2023, 3, 15)
                },
                {
                    'action_type': 'split',
                    'split_ratio': '2:1',
                    'ex_date': date(2023, 6, 10)
                }
            ]
            mock_get_service.return_value = mock_service
            
            response = client.get('/api/v2/stocks/AAPL/corporate-actions')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['symbol'] == 'AAPL'
            assert len(data['corporate_actions']) == 2
            assert data['corporate_actions'][0]['action_type'] == 'dividend'
            
            print("✅ API corporate actions endpoint test passed")

def test_api_health_endpoint():
    """Test /api/v2/health endpoint functionality"""
    from app import app
    
    with app.test_client() as client:
        with patch('services.get_stock_service') as mock_get_service, \
             patch('services.get_fmp_client') as mock_get_client:
            
            mock_service = MagicMock()
            mock_service.get_all_stocks_with_scores.return_value = [{}, {}]  # 2 stocks
            mock_get_service.return_value = mock_service
            
            mock_client = MagicMock()
            mock_client.get_remaining_requests.return_value = 200
            mock_get_client.return_value = mock_client
            
            response = client.get('/api/v2/health')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] == True
            assert data['status'] == 'healthy'
            assert data['database']['connected'] == True
            assert data['database']['stock_count'] == 2
            
            print("✅ API health endpoint test passed")

def test_api_auth_status_endpoint():
    """Test /api/v2/auth/status endpoint functionality"""
    from app import app
    
    with app.test_client() as client:
        # Test not logged in
        response = client.get('/api/v2/auth/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['authenticated'] == False
        
        # Test logged in (simulate session)
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['email'] = 'test@example.com'
        
        response = client.get('/api/v2/auth/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['authenticated'] == True
        assert data['user']['username'] == 'testuser'
        
        print("✅ API auth status endpoint test passed")

def test_api_error_handling():
    """Test API error handling scenarios"""
    from app import app
    
    with app.test_client() as client:
        # Test service error
        with patch('services.get_stock_service') as mock_get_service:
            mock_get_service.side_effect = Exception("Service error")
            
            response = client.get('/api/v2/stocks')
            assert response.status_code == 500
            
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'error' in data
            
        # Test not found
        with patch('services.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_stock_basic_info.return_value = None
            mock_get_service.return_value = mock_service
            
            response = client.get('/api/v2/stocks/NONEXISTENT')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'Stock not found' in data['error']
            
        print("✅ API error handling test passed")

def test_api_invalid_parameters():
    """Test API with invalid parameters"""
    from app import app
    
    with app.test_client() as client:
        with patch('services.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            
            # Test invalid parameters
            response = client.get('/api/v2/stocks?min_score=invalid')
            assert response.status_code == 400
            
            data = json.loads(response.data)
            assert data['success'] == False
            assert 'Invalid query parameters' in data['error']
            
            print("✅ API invalid parameters test passed")

def run_all_tests():
    """Run all integration tests"""
    print("🧪 Running API Integration Tests")
    print("=" * 50)
    
    test_functions = [
        test_api_stocks_endpoint,
        test_api_stock_detail_endpoint,
        test_api_financial_statements_endpoint,
        test_api_corporate_actions_endpoint,
        test_api_health_endpoint,
        test_api_auth_status_endpoint,
        test_api_error_handling,
        test_api_invalid_parameters
    ]
    
    passed = 0
    total = len(test_functions)
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 50)
    print(f"✅ {passed}/{total} integration tests passed")
    
    if passed == total:
        print("🎉 All API integration tests passed!")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)