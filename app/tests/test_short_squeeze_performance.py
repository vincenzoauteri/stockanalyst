#!/usr/bin/env python3
"""
Performance Tests for Short Squeeze Analysis
Tests system performance with realistic data volumes and loads
"""

import pytest
import time
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
import threading
import concurrent.futures
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
def sp500_symbols():
    """Sample of S&P 500 symbols for performance testing"""
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'UNH', 'JNJ',
        'V', 'XOM', 'PG', 'JPM', 'HD', 'CVX', 'MA', 'ABBV', 'PFE', 'AVGO',
        'KO', 'COST', 'PEP', 'TMO', 'WMT', 'BAC', 'CRM', 'ABT', 'LLY', 'ADBE',
        'ACN', 'MRK', 'CSCO', 'TXN', 'DIS', 'DHR', 'VZ', 'NKE', 'NFLX', 'COP',
        'INTC', 'CMCSA', 'AMD', 'WFC', 'UPS', 'LOW', 'AMGN', 'QCOM', 'HON', 'NEE',
        'T', 'IBM', 'MS', 'CAT', 'RTX', 'SPGI', 'BLK', 'ELV', 'MDT', 'AXP',
        'SCHW', 'DE', 'BKNG', 'AMAT', 'SYK', 'ADP', 'TJX', 'LMT', 'GILD', 'ADI',
        'CVS', 'AMT', 'C', 'SBUX', 'PYPL', 'MDLZ', 'ISRG', 'ZTS', 'MMC', 'CB',
        'NOW', 'MO', 'EOG', 'TGT', 'EQIX', 'BMY', 'SLB', 'REGN', 'CI', 'SO',
        'BDX', 'BA', 'ITW', 'PLD', 'APD', 'DUK', 'CSX', 'CL', 'WM', 'EMR',
        'FDX', 'NSC', 'GE', 'SHW', 'MMM', 'ATVI', 'GM', 'FISV', 'TFC', 'USB'
    ]

def generate_mock_short_data(symbol, index=0):
    """Generate realistic mock short interest data"""
    base_values = {
        'short_interest': 5000000 + (index * 1000000),
        'float_shares': 50000000 + (index * 10000000),
        'short_ratio': 2.0 + (index * 0.5),
        'short_percent_of_float': 10.0 + (index * 2.0),
        'average_daily_volume': 1000000 + (index * 500000)
    }
    
    # Add some variation
    import random
    variation = random.uniform(0.8, 1.2)
    
    return {
        'symbol': symbol,
        'report_date': date.today() - timedelta(days=random.randint(1, 14)),
        'short_interest': int(base_values['short_interest'] * variation),
        'float_shares': int(base_values['float_shares'] * variation),
        'short_ratio': round(base_values['short_ratio'] * variation, 2),
        'short_percent_of_float': round(base_values['short_percent_of_float'] * variation, 2),
        'average_daily_volume': int(base_values['average_daily_volume'] * variation)
    }

@pytest.mark.performance
class TestBatchCalculationPerformance:
    """Test performance of batch score calculations"""
    
    def test_batch_calculation_timing(self, sp500_symbols):
        """Test batch calculation performance with S&P 500 symbols"""
        with patch('database.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Create mock data for all symbols
            mock_data = {}
            for i, symbol in enumerate(sp500_symbols):
                mock_data[symbol] = generate_mock_short_data(symbol, i)
            
            def mock_execute_side_effect(*args, **kwargs):
                mock_result = MagicMock()
                if 'short_interest_data' in str(args[0]):
                    symbol = kwargs.get('symbol', sp500_symbols[0])
                    if symbol in mock_data:
                        mock_row = MagicMock()
                        for key, value in mock_data[symbol].items():
                            setattr(mock_row, key, value)
                        mock_result.fetchone.return_value = mock_row
                    else:
                        mock_result.fetchone.return_value = None
                else:
                    # Historical prices - return empty for speed
                    mock_result.fetchall.return_value = []
                return mock_result
            
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = mock_execute_side_effect
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Time the batch calculation
            analyzer = ShortSqueezeAnalyzer()
            start_time = time.time()
            
            results = analyzer.calculate_batch_scores(sp500_symbols)
            
            end_time = time.time()
            calculation_time = end_time - start_time
            
            # Performance assertions
            assert calculation_time < 120.0, f"Batch calculation took {calculation_time:.2f}s, should be under 2 minutes"
            assert len(results) == len(sp500_symbols), "Should process all symbols"
            
            # Calculate throughput
            throughput = len(sp500_symbols) / calculation_time
            assert throughput > 0.8, f"Throughput {throughput:.2f} symbols/sec is too low"
            
            print(f"\nBatch Performance Results:")
            print(f"  Symbols processed: {len(sp500_symbols)}")
            print(f"  Total time: {calculation_time:.2f} seconds")
            print(f"  Throughput: {throughput:.2f} symbols/second")
            print(f"  Average per symbol: {calculation_time/len(sp500_symbols)*1000:.1f} ms")
    
    def test_batch_storage_performance(self, sp500_symbols):
        """Test performance of batch score storage"""
        with patch('database.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            mock_db.insert_short_squeeze_score.return_value = True
            
            # Generate realistic score results
            results = []
            for i, symbol in enumerate(sp500_symbols):
                results.append({
                    'symbol': symbol,
                    'squeeze_score': 30.0 + (i % 70),  # Spread scores 30-100
                    'si_score': 20.0 + (i % 80),
                    'dtc_score': 10.0 + (i % 90),
                    'float_score': 40.0 + (i % 60),
                    'momentum_score': 25.0 + (i % 75),
                    'data_quality': ['high', 'medium', 'low'][i % 3]
                })
            
            # Time the batch storage
            analyzer = ShortSqueezeAnalyzer()
            start_time = time.time()
            
            stored_count = analyzer.store_squeeze_scores(results)
            
            end_time = time.time()
            storage_time = end_time - start_time
            
            # Performance assertions
            assert storage_time < 30.0, f"Batch storage took {storage_time:.2f}s, should be under 30 seconds"
            assert stored_count == len(sp500_symbols), "Should store all valid scores"
            
            # Calculate storage throughput
            throughput = len(sp500_symbols) / storage_time
            assert throughput > 3.0, f"Storage throughput {throughput:.2f} scores/sec is too low"
            
            print(f"\nBatch Storage Performance Results:")
            print(f"  Scores stored: {stored_count}")
            print(f"  Total time: {storage_time:.2f} seconds")
            print(f"  Throughput: {throughput:.2f} scores/second")

@pytest.mark.performance
class TestAPIPerformanceUnderLoad:
    """Test API performance under concurrent load"""
    
    def test_concurrent_api_requests(self, client, sp500_symbols):
        """Test API performance with concurrent requests"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            
            # Mock service responses
            def mock_get_squeeze_score(symbol):
                return {
                    'symbol': symbol,
                    'squeeze_score': 75.0,
                    'data_quality': 'high',
                    'calculated_at': datetime.now().isoformat()
                }
            
            mock_service.get_short_squeeze_score = mock_get_squeeze_score
            mock_get_service.return_value = mock_service
            
            # Function to make API request with thread-safe client
            def make_request(symbol):
                with app.test_client() as thread_client:
                    start_time = time.time()
                    response = thread_client.get(f'/api/v2/stocks/{symbol}/squeeze-score')
                    end_time = time.time()
                    return {
                        'symbol': symbol,
                        'status_code': response.status_code,
                        'response_time': end_time - start_time,
                        'success': response.status_code == 200
                    }
            
            # Test concurrent requests
            test_symbols = sp500_symbols[:20]  # Test with 20 symbols
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, symbol) for symbol in test_symbols]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # Performance assertions
            assert all(r['success'] for r in results), "All requests should succeed"
            assert total_time < 10.0, f"Concurrent requests took {total_time:.2f}s, should be under 10 seconds"
            
            # Check individual response times
            response_times = [r['response_time'] for r in results]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            assert avg_response_time < 0.5, f"Average response time {avg_response_time:.3f}s is too slow"
            assert max_response_time < 1.0, f"Max response time {max_response_time:.3f}s is too slow"
            
            print(f"\nConcurrent API Performance Results:")
            print(f"  Total requests: {len(test_symbols)}")
            print(f"  Total time: {total_time:.2f} seconds")
            print(f"  Average response time: {avg_response_time:.3f} seconds")
            print(f"  Max response time: {max_response_time:.3f} seconds")
            print(f"  Requests per second: {len(test_symbols)/total_time:.2f}")
    
    def test_rankings_api_performance(self, client):
        """Test performance of rankings API with large result sets"""
        with patch('api_routes.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            
            # Generate large mock dataset
            large_rankings = []
            for i in range(500):  # Simulate all S&P 500 stocks
                large_rankings.append({
                    'symbol': f'SYM{i:03d}',
                    'company_name': f'Test Company {i}',
                    'squeeze_score': 100 - (i * 0.2),  # Decreasing scores
                    'si_score': 90 - (i * 0.18),
                    'dtc_score': 80 - (i * 0.16),
                    'data_quality': ['high', 'medium', 'low'][i % 3],
                    'calculated_at': datetime.now().isoformat()
                })
            
            # Mock service that respects limit parameter
            def mock_get_rankings(limit=50, **kwargs):
                return large_rankings[:limit]
            
            mock_service.get_short_squeeze_rankings.side_effect = mock_get_rankings
            mock_get_service.return_value = mock_service
            
            # Test different limit sizes
            for limit in [50, 100, 200, 500]:
                start_time = time.time()
                response = client.get(f'/api/v2/squeeze/rankings?limit={limit}')
                end_time = time.time()
                
                response_time = end_time - start_time
                
                # Performance assertions
                assert response.status_code == 200, f"Request failed for limit {limit}"
                assert response_time < 2.0, f"Response time {response_time:.3f}s too slow for limit {limit}"
                
                data = json.loads(response.data)
                assert data['success'] is True
                assert len(data['data']) <= limit
                
                print(f"  Limit {limit}: {response_time:.3f}s")

@pytest.mark.performance  
class TestDatabaseQueryPerformance:
    """Test database query performance"""
    
    def test_data_access_layer_performance(self, sp500_symbols):
        """Test data access layer query performance"""
        with patch('data_access_layer.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Mock fast database responses
            mock_conn = MagicMock()
            mock_row = MagicMock()
            mock_row.symbol = 'AAPL'
            mock_row.squeeze_score = 75.0
            mock_row.data_quality = 'high'
            mock_row.calculated_at = datetime.now()
            
            # Simulate realistic query times
            def mock_execute_with_timing(*args, **kwargs):
                time.sleep(0.001)  # Simulate 1ms database query
                mock_result = MagicMock()
                mock_result.fetchone.return_value = mock_row
                mock_result.fetchall.return_value = [mock_row] * 100
                return mock_result
            
            mock_conn.execute.side_effect = mock_execute_with_timing
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            service = StockDataService()
            
            # Test individual queries
            test_symbols = sp500_symbols[:50]
            start_time = time.time()
            
            for symbol in test_symbols:
                score = service.get_short_squeeze_score(symbol)
                assert score is not None
            
            total_time = time.time() - start_time
            avg_query_time = total_time / len(test_symbols)
            
            # Performance assertions
            assert avg_query_time < 0.1, f"Average query time {avg_query_time:.3f}s is too slow"
            assert total_time < 5.0, f"Total query time {total_time:.2f}s is too slow"
            
            print(f"\nDatabase Query Performance Results:")
            print(f"  Queries executed: {len(test_symbols)}")
            print(f"  Total time: {total_time:.3f} seconds")
            print(f"  Average per query: {avg_query_time:.3f} seconds")
    
    def test_rankings_query_performance(self):
        """Test performance of complex rankings queries"""
        with patch('data_access_layer.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Generate large mock result set
            mock_rows = []
            for i in range(500):
                mock_row = MagicMock()
                mock_row.symbol = f'SYM{i:03d}'
                mock_row.squeeze_score = 100 - (i * 0.2)
                mock_row.data_quality = 'high'
                mock_row.calculated_at = datetime.now()
                mock_rows.append(mock_row)
            
            # Mock database query
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchall.return_value = mock_rows
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            service = StockDataService()
            
            # Test rankings query performance
            start_time = time.time()
            rankings = service.get_short_squeeze_rankings(limit=500)
            end_time = time.time()
            
            query_time = end_time - start_time
            
            # Performance assertions
            assert query_time < 1.0, f"Rankings query took {query_time:.3f}s, should be under 1 second"
            assert len(rankings) <= 500, "Should return correct number of results"
            
            print(f"\nRankings Query Performance:")
            print(f"  Query time: {query_time:.3f} seconds")
            print(f"  Results returned: {len(rankings)}")

@pytest.mark.performance
class TestFrontendPerformance:
    """Test frontend rendering performance"""
    
    def test_squeeze_page_load_time(self, client):
        """Test short squeeze page load performance"""
        with patch('app.get_stock_service') as mock_get_service:
            mock_service = MagicMock()
            
            # Generate realistic frontend data
            rankings = []
            for i in range(100):  # Simulate 100 results
                rankings.append({
                    'symbol': f'SYM{i:03d}',
                    'company_name': f'Test Company {i}',
                    'squeeze_score': 100 - i,
                    'short_percent_of_float': 15.0 + (i % 20),
                    'data_quality': ['high', 'medium', 'low'][i % 3],
                    'calculated_at': '2025-07-13T10:00:00'
                })
            
            mock_service.get_short_squeeze_rankings.return_value = rankings
            mock_service.get_short_squeeze_summary_stats.return_value = {
                'total_scores': 500,
                'high_risk_count': 25,
                'avg_squeeze_score': 45.8,
                'max_short_percent': 35.5
            }
            
            mock_get_service.return_value = mock_service
            
            # Test page load time
            start_time = time.time()
            response = client.get('/squeeze')
            end_time = time.time()
            
            load_time = end_time - start_time
            
            # Performance assertions
            assert response.status_code == 200, "Page should load successfully"
            assert load_time < 3.0, f"Page load time {load_time:.3f}s is too slow"
            
            # Verify content is present
            html_content = response.data.decode('utf-8')
            assert 'Short Squeeze Analysis' in html_content
            assert 'SYM001' in html_content  # Should contain test data
            
            print(f"\nFrontend Performance Results:")
            print(f"  Page load time: {load_time:.3f} seconds")
            print(f"  Response size: {len(response.data)} bytes")

@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage during large operations"""
    
    def test_batch_calculation_memory_usage(self, sp500_symbols):
        """Test memory usage during batch calculations"""
        import psutil
        import os
        
        with patch('database.DatabaseManager') as mock_db_manager:
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            # Mock minimal data to avoid memory bloat
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
            
            # Measure memory before
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run batch calculation
            analyzer = ShortSqueezeAnalyzer()
            results = analyzer.calculate_batch_scores(sp500_symbols)
            
            # Measure memory after
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = memory_after - memory_before
            
            # Memory assertions
            assert memory_increase < 100, f"Memory increase {memory_increase:.1f}MB is too high"
            
            print(f"\nMemory Usage Results:")
            print(f"  Memory before: {memory_before:.1f} MB")
            print(f"  Memory after: {memory_after:.1f} MB")
            print(f"  Memory increase: {memory_increase:.1f} MB")

if __name__ == '__main__':
    # Run performance tests with verbose output
    pytest.main([__file__, '-v', '-s', '-m', 'performance'])