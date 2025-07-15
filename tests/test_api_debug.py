#!/usr/bin/env python3
"""
Debug API Tests - PostgreSQL-only environment
"""

import os
import sys
import json
from unittest.mock import patch

def debug_api_stocks_endpoint():
    """Debug the stocks endpoint"""
    # Set environment variables for PostgreSQL testing
    test_env = {
        'POSTGRES_HOST': 'postgres',
        'POSTGRES_DB': 'stockanalyst',
        'SECRET_KEY': 'test-secret-key',
        'FMP_API_KEY': 'test_fmp_key',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        from app import app
        
        with app.test_client() as client:
            response = client.get('/api/v2/stocks')
            print(f"Status: {response.status_code}")
            print(f"Data: {response.data.decode()}")
            
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"Success: {data.get('success')}")
                print(f"Data length: {len(data.get('data', []))}")
                if data.get('data'):
                    print(f"First item: {data['data'][0]}")

def debug_api_stock_detail_endpoint():
    """Debug the stock detail endpoint"""
    test_env = {
        'POSTGRES_HOST': 'postgres',
        'POSTGRES_DB': 'stockanalyst',
        'SECRET_KEY': 'test-secret-key',
        'FMP_API_KEY': 'test_fmp_key',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        from app import app
        
        with app.test_client() as client:
            response = client.get('/api/v2/stocks/AAPL')
            print(f"Status: {response.status_code}")
            print(f"Data: {response.data.decode()}")

def debug_api_health_endpoint():
    """Debug the health endpoint"""
    test_env = {
        'POSTGRES_HOST': 'postgres',
        'POSTGRES_DB': 'stockanalyst',
        'SECRET_KEY': 'test-secret-key',
        'FMP_API_KEY': 'test_fmp_key',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        from app import app
        
        with app.test_client() as client:
            response = client.get('/api/v2/health')
            print(f"Status: {response.status_code}")
            print(f"Data: {response.data.decode()}")

if __name__ == "__main__":
    print("🔍 Debugging API Endpoints (PostgreSQL)")
    print("=" * 50)
    
    print("\n📊 Testing /api/v2/stocks")
    debug_api_stocks_endpoint()
    
    print("\n📈 Testing /api/v2/stocks/AAPL")
    debug_api_stock_detail_endpoint()
    
    print("\n🏥 Testing /api/v2/health")
    debug_api_health_endpoint()