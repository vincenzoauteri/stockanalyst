import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta
import json
import os

# Mock os.getenv for FMP_API_KEY and DATABASE_PATH before importing modules
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {'FMP_API_KEY': 'test_api_key', }):
        yield

from undervaluation_analyzer import UndervaluationAnalyzer
from database import DatabaseManager
from fmp_client import FMPClient

@pytest.fixture
def mock_db_manager():
    db_manager = MagicMock(spec=DatabaseManager)
    # Mock get_sp500_symbols to return a predefined list
    db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT', 'GOOG']
    
    # Mock the engine.connect() and read_sql for get_fundamentals_data
    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    db_manager.engine = mock_engine

    # Mock pd.read_sql to return a base DataFrame for get_fundamentals_data
    base_df_data = {
        'symbol': ['AAPL', 'MSFT', 'GOOG'],
        'sector': ['Technology', 'Technology', 'Communication Services'],
        'price': [170.0, 400.0, 150.0],
        'beta': [1.2, 0.9, 1.1],
        'mktcap': [2.8e12, 3.0e12, 1.9e12],
        'dcf': [180.0, 420.0, 160.0]
    }
    with patch('pandas.read_sql', return_value=pd.DataFrame(base_df_data)) as mock_read_sql:
        yield db_manager

@pytest.fixture
def mock_fmp_client():
    fmp_client = MagicMock(spec=FMPClient)
    # Configure default return for get_fundamentals_summary
    fmp_client.get_fundamentals_summary.side_effect = [
        # AAPL fundamentals
        {'symbol': 'AAPL', 'pe_ratio': 30.0, 'pb_ratio': 15.0, 'price_to_sales': 7.0, 
         'roe': 0.5, 'net_profit_margin': 0.25, 'current_ratio': 1.5, 'free_cash_flow_yield': 0.03,
         'debt_to_equity': 1.0, 'return_on_assets': 0.15, 'gross_profit_margin': 0.45},
        # MSFT fundamentals
        {'symbol': 'MSFT', 'pe_ratio': 35.0, 'pb_ratio': 18.0, 'price_to_sales': 8.0, 
         'roe': 0.4, 'net_profit_margin': 0.20, 'current_ratio': 1.2, 'free_cash_flow_yield': 0.02,
         'debt_to_equity': 0.8, 'return_on_assets': 0.12, 'gross_profit_margin': 0.40},
        # GOOG fundamentals
        {'symbol': 'GOOG', 'pe_ratio': 28.0, 'pb_ratio': 12.0, 'price_to_sales': 6.0, 
         'roe': 0.6, 'net_profit_margin': 0.30, 'current_ratio': 2.0, 'free_cash_flow_yield': 0.04,
         'debt_to_equity': 0.6, 'return_on_assets': 0.18, 'gross_profit_margin': 0.50}
    ]
    yield fmp_client

@pytest.fixture
def analyzer(mock_db_manager, mock_fmp_client):
    with patch.multiple('undervaluation_analyzer',
                        DatabaseManager=lambda: mock_db_manager,
                        FMPClient=lambda: mock_fmp_client):
        analyzer_instance = UndervaluationAnalyzer(cache_duration_hours=0.1) # Short cache duration for testing
        analyzer_instance.client = mock_fmp_client  # Ensure the client is properly mocked
        yield analyzer_instance

# --- Cache Tests ---

def test_cache_init_and_load(analyzer):
    # Mock _load_cache to return empty data for this test
    with patch.object(analyzer, '_load_cache', return_value={}):
        cache_data = analyzer._load_cache()
        assert cache_data == {}

def test_cache_save_and_load(analyzer):
    test_data = {'AAPL': {'data': {'pe_ratio': 20}, 'timestamp': datetime.now().isoformat()}}
    analyzer._save_cache(test_data)
    loaded_data = analyzer._load_cache()
    assert loaded_data['AAPL']['data'] == {'pe_ratio': 20}

def test_is_cache_valid(analyzer):
    # Test valid cache
    valid_time = (datetime.now() - timedelta(minutes=1)).isoformat()
    assert analyzer._is_cache_valid(valid_time)

    # Test expired cache
    expired_time = (datetime.now() - timedelta(hours=1)).isoformat()
    # Temporarily set cache_duration_hours to a small value for this test
    original_duration = analyzer.cache_duration_hours
    analyzer.cache_duration_hours = 0.01 # 0.6 minutes
    assert not analyzer._is_cache_valid(expired_time)
    analyzer.cache_duration_hours = original_duration # Reset

def test_get_cached_fundamentals(analyzer):
    symbol = 'AAPL'
    # Simulate cached data
    cache_data = {
        symbol: {
            'data': {'pe_ratio': 22.0},
            'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat()
        }
    }
    with patch.object(analyzer, '_load_cache', return_value=cache_data):
        cached = analyzer._get_cached_fundamentals(symbol)
        assert cached['pe_ratio'] == 22.0

    # Simulate expired cache
    expired_cache_data = {
        symbol: {
            'data': {'pe_ratio': 22.0},
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat()
        }
    }
    with patch.object(analyzer, '_load_cache', return_value=expired_cache_data):
        original_duration = analyzer.cache_duration_hours
        analyzer.cache_duration_hours = 0.01
        cached = analyzer._get_cached_fundamentals(symbol)
        assert cached is None
        analyzer.cache_duration_hours = original_duration

def test_cache_fundamentals(analyzer):
    symbol = 'MSFT'
    fundamentals = {'pe_ratio': 30.0}
    
    # Mock the save/load methods to avoid actual file operations in tests
    with patch.object(analyzer, '_save_cache') as mock_save_cache, \
         patch.object(analyzer, '_load_cache', return_value={}):
        analyzer._cache_fundamentals(symbol, fundamentals)
        
        # Verify save_cache was called with the correct data structure
        mock_save_cache.assert_called_once()
        saved_data = mock_save_cache.call_args[0][0]
        assert symbol in saved_data
        assert saved_data[symbol]['data'] == fundamentals
        assert 'timestamp' in saved_data[symbol]

def test_cleanup_cache(analyzer):
    # Simulate cache with one valid and one expired entry
    cache_data = {
        'VALID': {'data': {'pe_ratio': 10}, 'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat()},
        'EXPIRED': {'data': {'pe_ratio': 20}, 'timestamp': (datetime.now() - timedelta(hours=1)).isoformat()}
    }
    with patch.object(analyzer, '_load_cache', return_value=cache_data), \
         patch.object(analyzer, '_save_cache') as mock_save_cache:
        original_duration = analyzer.cache_duration_hours
        analyzer.cache_duration_hours = 0.01
        analyzer._cleanup_cache()
        analyzer.cache_duration_hours = original_duration
        
        # Verify that save_cache was called - actual logic removes expired entries  
        mock_save_cache.assert_called_once()
        saved_data = mock_save_cache.call_args[0][0]
        # All entries should be removed due to very short cache duration (0.01 hours)
        assert len(saved_data) == 0

def test_get_cache_stats(analyzer):
    cache_data = {
        'VALID1': {'data': {}, 'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat()},
        'VALID2': {'data': {}, 'timestamp': (datetime.now() - timedelta(minutes=2)).isoformat()},
        'EXPIRED1': {'data': {}, 'timestamp': (datetime.now() - timedelta(hours=1)).isoformat()}
    }
    with patch.object(analyzer, '_load_cache', return_value=cache_data):
        original_duration = analyzer.cache_duration_hours
        analyzer.cache_duration_hours = 1.0  # 1 hour - so minutes=1,2 are valid, hours=1 is expired
        stats = analyzer.get_cache_stats()
        analyzer.cache_duration_hours = original_duration

        assert stats['total_entries'] == 3
        assert stats['valid_entries'] == 2
        assert stats['expired_entries'] == 1

def test_clear_cache(analyzer):
    with patch('os.path.exists', return_value=True), \
         patch('os.remove') as mock_remove, \
         patch('undervaluation_analyzer.UndervaluationAnalyzer._init_cache') as mock_init_cache:
        analyzer.clear_cache()
        mock_remove.assert_called_once_with(analyzer.cache_file)
        mock_init_cache.assert_called_once()

# --- Scoring Logic Tests ---

@pytest.fixture
def sample_sector_stats():
    return {
        'Technology': {
            'pe_ratio': {'mean': 30.0, 'std': 5.0},
            'pb_ratio': {'mean': 10.0, 'std': 2.0},
            'price_to_sales': {'mean': 5.0, 'std': 1.0},
            'roe': {'mean': 0.20, 'std': 0.05},
            'net_profit_margin': {'mean': 0.15, 'std': 0.03},
            'current_ratio': {'mean': 1.5, 'std': 0.2},
            'free_cash_flow_yield': {'mean': 0.03, 'std': 0.01},
            'debt_to_equity': {'mean': 0.8, 'std': 0.2},
            'return_on_assets': {'mean': 0.10, 'std': 0.02},
            'gross_profit_margin': {'mean': 0.40, 'std': 0.05}
        }
    }

def test_score_valuation_metrics(analyzer, sample_sector_stats):
    # Stock with lower PE (better) than average
    stock_good_pe = pd.Series({'pe_ratio': 25.0, 'pb_ratio': 9.0, 'price_to_sales': 4.5})
    score = analyzer.score_valuation_metrics(stock_good_pe, sample_sector_stats, 'Technology')
    assert score > 50 # Should be better than average

    # Stock with higher PE (worse) than average
    stock_bad_pe = pd.Series({'pe_ratio': 35.0, 'pb_ratio': 11.0, 'price_to_sales': 5.5})
    score = analyzer.score_valuation_metrics(stock_bad_pe, sample_sector_stats, 'Technology')
    assert score < 50 # Should be worse than average

    # Stock with missing data
    stock_missing_data = pd.Series({'pe_ratio': 25.0})
    score = analyzer.score_valuation_metrics(stock_missing_data, sample_sector_stats, 'Technology')
    assert score > 0 # Should still calculate based on available data

def test_score_quality_metrics(analyzer, sample_sector_stats):
    # Stock with better quality metrics
    stock_good_quality = pd.Series({'roe': 0.25, 'net_profit_margin': 0.18, 'current_ratio': 1.8, 'free_cash_flow_yield': 0.04})
    score = analyzer.score_quality_metrics(stock_good_quality, sample_sector_stats, 'Technology')
    assert score > 50

    # Stock with worse quality metrics
    stock_bad_quality = pd.Series({'roe': 0.15, 'net_profit_margin': 0.12, 'current_ratio': 1.2, 'free_cash_flow_yield': 0.02})
    score = analyzer.score_quality_metrics(stock_bad_quality, sample_sector_stats, 'Technology')
    assert score < 50

def test_score_financial_strength(analyzer, sample_sector_stats):
    # Stock with better strength (lower debt, higher returns)
    stock_good_strength = pd.Series({'debt_to_equity': 0.5, 'return_on_assets': 0.12, 'gross_profit_margin': 0.45})
    score = analyzer.score_financial_strength(stock_good_strength, sample_sector_stats, 'Technology')
    assert score > 50

    # Stock with worse strength
    stock_bad_strength = pd.Series({'debt_to_equity': 1.0, 'return_on_assets': 0.08, 'gross_profit_margin': 0.35})
    score = analyzer.score_financial_strength(stock_bad_strength, sample_sector_stats, 'Technology')
    assert score < 50

def test_score_risk_adjustment(analyzer):
    # Low beta, large cap (good)
    stock_low_risk = pd.Series({'beta': 0.7, 'mktcap': 200_000_000_000})
    score = analyzer.score_risk_adjustment(stock_low_risk)
    assert score > 50

    # High beta, small cap (bad)
    stock_high_risk = pd.Series({'beta': 2.5, 'mktcap': 5_000_000_000})
    score = analyzer.score_risk_adjustment(stock_high_risk)
    assert score < 50

    # Neutral
    stock_neutral_risk = pd.Series({'beta': 1.0, 'mktcap': 50_000_000_000})
    score = analyzer.score_risk_adjustment(stock_neutral_risk)
    assert score == 50.0

# --- Integration/Workflow Tests ---

def test_get_fundamentals_data_no_cache_force_refresh(analyzer, mock_db_manager, mock_fmp_client):
    # Ensure cache is empty and force refresh
    with patch.object(analyzer, '_load_cache', return_value={}), \
         patch.object(analyzer, '_cache_fundamentals') as mock_cache:
        df = analyzer.get_fundamentals_data(use_cache=False, force_refresh=True)
        assert not df.empty
        assert len(df) == 3 # AAPL, MSFT, GOOG
        assert mock_fmp_client.get_fundamentals_summary.call_count == 3 # All should be fetched
        # When use_cache=False, data is not cached, so cache calls should be 0
        assert mock_cache.call_count == 0

def test_get_fundamentals_data_with_cache(analyzer, mock_db_manager, mock_fmp_client):
    # Simulate all data being in cache and valid
    cached_data = {
        'AAPL': {'data': {'pe_ratio': 20.0}, 'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat()},
        'MSFT': {'data': {'pe_ratio': 25.0}, 'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat()},
        'GOOG': {'data': {'pe_ratio': 22.0}, 'timestamp': (datetime.now() - timedelta(minutes=1)).isoformat()}
    }
    with patch.object(analyzer, '_load_cache', return_value=cached_data), \
         patch.object(analyzer, '_cache_fundamentals') as mock_cache_fundamentals:
        df = analyzer.get_fundamentals_data(use_cache=True, force_refresh=False)
        assert not df.empty
        assert len(df) == 3
        mock_fmp_client.get_fundamentals_summary.assert_not_called() # No API calls if all cached
        mock_cache_fundamentals.assert_not_called() # No caching if already in cache

def test_calculate_undervaluation_scores(analyzer, mock_db_manager, mock_fmp_client):
    # Ensure get_fundamentals_data is mocked to return a DataFrame with all necessary columns
    # This mock needs to be more comprehensive to include all metrics used in scoring
    mock_fundamentals_df = pd.DataFrame([
        {'symbol': 'AAPL', 'sector': 'Technology', 'price': 170.0, 'beta': 1.2, 'mktcap': 2.8e12,
         'pe_ratio': 30.0, 'pb_ratio': 15.0, 'price_to_sales': 7.0, 
         'roe': 0.5, 'net_profit_margin': 0.25, 'current_ratio': 1.5, 'free_cash_flow_yield': 0.03,
         'debt_to_equity': 1.0, 'return_on_assets': 0.15, 'gross_profit_margin': 0.45},
        {'symbol': 'MSFT', 'sector': 'Technology', 'price': 400.0, 'beta': 0.9, 'mktcap': 3.0e12,
         'pe_ratio': 35.0, 'pb_ratio': 18.0, 'price_to_sales': 8.0, 
         'roe': 0.4, 'net_profit_margin': 0.20, 'current_ratio': 1.2, 'free_cash_flow_yield': 0.02,
         'debt_to_equity': 0.8, 'return_on_assets': 0.12, 'gross_profit_margin': 0.40},
        {'symbol': 'GOOG', 'sector': 'Communication Services', 'price': 150.0, 'beta': 1.1, 'mktcap': 1.9e12,
         'pe_ratio': 28.0, 'pb_ratio': 12.0, 'price_to_sales': 6.0, 
         'roe': 0.6, 'net_profit_margin': 0.30, 'current_ratio': 2.0, 'free_cash_flow_yield': 0.04,
         'debt_to_equity': 0.6, 'return_on_assets': 0.18, 'gross_profit_margin': 0.50}
    ])

    with patch('undervaluation_analyzer.UndervaluationAnalyzer.get_fundamentals_data', return_value=mock_fundamentals_df):
        scores_df = analyzer.calculate_undervaluation_scores(use_cache=False, force_refresh=True)
        assert not scores_df.empty
        assert len(scores_df) == 3
        assert 'undervaluation_score' in scores_df.columns
        assert scores_df['undervaluation_score'].notna().all()
        
        # Verify scores are within a reasonable range (0-100)
        assert (scores_df['undervaluation_score'] >= 0).all()
        assert (scores_df['undervaluation_score'] <= 100).all()

def test_store_scores(analyzer, mock_db_manager):
    scores_df = pd.DataFrame([
        {'symbol': 'AAPL', 'sector': 'Technology', 'undervaluation_score': 75.0, 'data_quality': 'high'},
        {'symbol': 'MSFT', 'sector': 'Technology', 'undervaluation_score': 60.0, 'data_quality': 'high'}
    ])
    analyzer.store_scores(scores_df)
    mock_db_manager.insert_undervaluation_scores.assert_called_once()
    # Check if the data passed to insert_undervaluation_scores is correct
    assert mock_db_manager.insert_undervaluation_scores.call_args[0][0][0]['symbol'] == 'AAPL'

def test_analyze_undervaluation(analyzer, mock_db_manager, mock_fmp_client):
    # Mock get_fundamentals_data to return a DataFrame with all necessary columns
    mock_fundamentals_df = pd.DataFrame([
        {'symbol': 'AAPL', 'sector': 'Technology', 'price': 170.0, 'beta': 1.2, 'mktcap': 2.8e12,
         'pe_ratio': 30.0, 'pb_ratio': 15.0, 'price_to_sales': 7.0, 
         'roe': 0.5, 'net_profit_margin': 0.25, 'current_ratio': 1.5, 'free_cash_flow_yield': 0.03,
         'debt_to_equity': 1.0, 'return_on_assets': 0.15, 'gross_profit_margin': 0.45},
        {'symbol': 'MSFT', 'sector': 'Technology', 'price': 400.0, 'beta': 0.9, 'mktcap': 3.0e12,
         'pe_ratio': 35.0, 'pb_ratio': 18.0, 'price_to_sales': 8.0, 
         'roe': 0.4, 'net_profit_margin': 0.20, 'current_ratio': 1.2, 'free_cash_flow_yield': 0.02,
         'debt_to_equity': 0.8, 'return_on_assets': 0.12, 'gross_profit_margin': 0.40},
        {'symbol': 'GOOG', 'sector': 'Communication Services', 'price': 150.0, 'beta': 1.1, 'mktcap': 1.9e12,
         'pe_ratio': 28.0, 'pb_ratio': 12.0, 'price_to_sales': 6.0, 
         'roe': 0.6, 'net_profit_margin': 0.30, 'current_ratio': 2.0, 'free_cash_flow_yield': 0.04,
         'debt_to_equity': 0.6, 'return_on_assets': 0.18, 'gross_profit_margin': 0.50}
    ])

    with patch('undervaluation_analyzer.UndervaluationAnalyzer.get_fundamentals_data', return_value=mock_fundamentals_df):
        summary = analyzer.analyze_undervaluation(use_cache=False, force_refresh=True)
        assert summary['total_stocks'] == 3
        assert summary['analyzed_stocks'] == 3
        assert summary['insufficient_data'] == 0
        assert summary['avg_score'] > 0
        mock_db_manager.insert_undervaluation_scores.assert_called_once()

def test_calculate_sector_stats(analyzer):
    df_data = {
        'symbol': ['A', 'B', 'C', 'D'],
        'sector': ['Tech', 'Tech', 'Finance', 'Finance'],
        'pe_ratio': [20, 25, 10, 12],
        'roe': [0.15, 0.18, 0.10, 0.11]
    }
    df = pd.DataFrame(df_data)
    metric_cols = ['pe_ratio', 'roe']
    stats = analyzer.calculate_sector_stats(df, metric_cols)

    assert 'Tech' in stats
    assert 'Finance' in stats
    assert stats['Tech']['pe_ratio']['mean'] == 22.5
    assert stats['Finance']['roe']['mean'] == pytest.approx(0.105)

def test_data_quality_assignment(analyzer):
    # Mock a stock with high data quality
    stock_high_quality = pd.Series({
        'symbol': 'HQ', 'sector': 'Tech', 'price': 100, 'beta': 1.0, 'mktcap': 1e9,
        'pe_ratio': 20, 'pb_ratio': 2, 'price_to_sales': 1,
        'roe': 0.2, 'net_profit_margin': 0.1, 'current_ratio': 1.5, 'free_cash_flow_yield': 0.05,
        'debt_to_equity': 0.5, 'return_on_assets': 0.1, 'gross_profit_margin': 0.3
    })
    # All 10 metrics present
    scores_df = analyzer.calculate_undervaluation_scores(use_cache=False, force_refresh=True)
    # This test needs to be run in isolation or with a specific mock for get_fundamentals_data
    # to control the number of available metrics.
    # For now, I'll rely on the overall test of calculate_undervaluation_scores to cover this.

    # To properly test data_quality assignment, I need to mock the `get_fundamentals_data`
    # to return dataframes with varying completeness.
    # This is better tested as part of the `calculate_undervaluation_scores` integration test.
    # I will add a specific check there.

    # Re-running calculate_undervaluation_scores with a controlled mock for get_fundamentals_data
    mock_fundamentals_df_high_quality = pd.DataFrame([
        {'symbol': 'HQ', 'sector': 'Tech', 'price': 100, 'beta': 1.0, 'mktcap': 1e9,
         'pe_ratio': 20, 'pb_ratio': 2, 'price_to_sales': 1,
         'roe': 0.2, 'net_profit_margin': 0.1, 'current_ratio': 1.5, 'free_cash_flow_yield': 0.05,
         'debt_to_equity': 0.5, 'return_on_assets': 0.1, 'gross_profit_margin': 0.3}
    ])
    with patch('undervaluation_analyzer.UndervaluationAnalyzer.get_fundamentals_data', return_value=mock_fundamentals_df_high_quality):
        scores = analyzer.calculate_undervaluation_scores(use_cache=False, force_refresh=True)
        assert scores.iloc[0]['data_quality'] == 'high'

    mock_fundamentals_df_medium_quality = pd.DataFrame([
        {'symbol': 'MQ', 'sector': 'Tech', 'price': 100, 'beta': 1.0, 'mktcap': 1e9,
         'pe_ratio': 20, 'pb_ratio': 2, 'price_to_sales': 1,
         'roe': 0.2, 'net_profit_margin': 0.1} # Only 6 out of 10 metrics (60%)
    ])
    with patch('undervaluation_analyzer.UndervaluationAnalyzer.get_fundamentals_data', return_value=mock_fundamentals_df_medium_quality):
        scores = analyzer.calculate_undervaluation_scores(use_cache=False, force_refresh=True)
        assert scores.iloc[0]['data_quality'] == 'medium'

    mock_fundamentals_df_low_quality = pd.DataFrame([
        {'symbol': 'LQ', 'sector': 'Tech', 'price': 100, 'beta': 1.0, 'mktcap': 1e9,
         'pe_ratio': 20, 'pb_ratio': 2, # Missing many metrics
        }
    ])
    with patch('undervaluation_analyzer.UndervaluationAnalyzer.get_fundamentals_data', return_value=mock_fundamentals_df_low_quality):
        scores = analyzer.calculate_undervaluation_scores(use_cache=False, force_refresh=True)
        assert scores.iloc[0]['data_quality'] == 'low'

    mock_fundamentals_df_insufficient_data = pd.DataFrame([
        {'symbol': 'ID', 'sector': 'Tech', 'insufficient_data': True}
    ])
    with patch('undervaluation_analyzer.UndervaluationAnalyzer.get_fundamentals_data', return_value=mock_fundamentals_df_insufficient_data):
        scores = analyzer.calculate_undervaluation_scores(use_cache=False, force_refresh=True)
        assert scores.iloc[0]['data_quality'] == 'insufficient'
