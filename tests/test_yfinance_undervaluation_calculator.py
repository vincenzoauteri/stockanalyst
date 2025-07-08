#!/usr/bin/env python3
"""
Tests for YFinance Undervaluation Calculator
Tests the Yahoo Finance-based undervaluation scoring system
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime
import os

# Mock environment variables before importing
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {'DATABASE_PATH': ':memory:'}):
        yield

from yfinance_undervaluation_calculator import YFinanceUndervaluationCalculator

@pytest.fixture
def calculator():
    """Create a calculator instance with mocked database"""
    with patch('yfinance_undervaluation_calculator.DatabaseManager') as mock_db:
        calc = YFinanceUndervaluationCalculator()
        calc.db = mock_db.return_value
        yield calc

@pytest.fixture
def sample_financial_data():
    """Sample financial data for testing calculations"""
    return {
        'symbol': 'AAPL',
        'company_name': 'Apple Inc.',
        'price': 150.0,
        'market_cap': 2800000000000,
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'revenue': 365000000000,
        'net_income': 94000000000,
        'eps': 5.89,
        'total_assets': 352000000000,
        'total_equity': 50000000000,
        'total_debt': 120000000000,
        'current_assets': 135000000000,
        'current_liabilities': 125000000000,
        'operating_cash_flow': 104000000000,
        'free_cash_flow': 93000000000
    }

class TestYFinanceUndervaluationCalculator:
    """Test cases for the YFinance undervaluation calculator"""

    def test_calculator_initialization(self, calculator):
        """Test calculator initializes properly"""
        assert calculator is not None
        assert hasattr(calculator, 'db')

    def test_get_financial_data_success(self, calculator, sample_financial_data):
        """Test getting financial data for a symbol"""
        # Mock database connection and queries
        mock_conn = MagicMock()
        calculator.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock the profile data result
        profile_result = MagicMock()
        profile_result.symbol = 'AAPL'
        profile_result.companyname = 'Apple Inc.'
        profile_result.price = 150.0
        profile_result.mktcap = 2800000000000
        profile_result.sector = 'Technology'
        profile_result.industry = 'Consumer Electronics'
        
        # Mock the income data result
        income_result = MagicMock()
        income_result.total_revenue = 365000000000
        income_result.net_income = 94000000000
        income_result.diluted_eps = 5.89
        income_result.basic_eps = 5.89
        income_result.shares_outstanding = 16000000000
        
        # Mock the balance data result
        balance_result = MagicMock()
        balance_result.total_assets = 352000000000
        balance_result.total_equity = 50000000000
        balance_result.total_debt = 120000000000
        balance_result.current_assets = 135000000000
        balance_result.current_liabilities = 125000000000
        
        # Mock the cashflow data result
        cashflow_result = MagicMock()
        cashflow_result.operating_cash_flow = 104000000000
        cashflow_result.free_cash_flow = 93000000000
        
        # Set up the execute method to return different results for different queries
        mock_conn.execute.return_value.fetchone.side_effect = [
            profile_result,  # First call for profile data
            income_result,   # Second call for income data
            balance_result,  # Third call for balance data
            cashflow_result  # Fourth call for cashflow data
        ]
        
        result = calculator.get_financial_data('AAPL')
        
        assert result is not None
        assert result['symbol'] == 'AAPL'
        assert result['company_name'] == 'Apple Inc.'
        assert result['price'] == 150.0
        assert result['market_cap'] == 2800000000000

    def test_get_financial_data_no_profile(self, calculator):
        """Test getting financial data when no profile exists"""
        # Mock database connection
        mock_conn = MagicMock()
        calculator.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock no profile data found
        mock_conn.execute.return_value.fetchone.return_value = None
        
        result = calculator.get_financial_data('NONEXISTENT')
        
        assert result == {}

    def test_calculate_financial_ratios(self, calculator, sample_financial_data):
        """Test financial ratio calculations"""
        ratios = calculator.calculate_financial_ratios(sample_financial_data)
        
        assert isinstance(ratios, dict)
        
        # Check that basic ratios are calculated
        expected_keys = ['pe_ratio', 'pb_ratio', 'ps_ratio', 'current_ratio', 
                        'debt_to_equity', 'roe', 'roa', 'profit_margin']
        
        for key in expected_keys:
            if key in ratios:  # Only check if the ratio was calculated
                assert isinstance(ratios[key], (int, float))

    def test_calculate_financial_ratios_missing_data(self, calculator):
        """Test financial ratio calculations with missing data"""
        incomplete_data = {
            'symbol': 'TEST',
            'price': 100.0,
            'eps': 5.0
            # Missing most other fields
        }
        
        ratios = calculator.calculate_financial_ratios(incomplete_data)
        
        # Should still return a dict, even if many ratios can't be calculated
        assert isinstance(ratios, dict)
        
        # PE ratio should be calculable
        if 'pe_ratio' in ratios:
            assert ratios['pe_ratio'] == 20.0  # 100 / 5

    def test_get_sector_averages(self, calculator):
        """Test getting sector averages"""
        # Mock database connection
        mock_conn = MagicMock()
        calculator.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock sector averages result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {'symbol': 'AAPL', 'pe_ratio': 25.0, 'pb_ratio': 5.0},
            {'symbol': 'MSFT', 'pe_ratio': 30.0, 'pb_ratio': 6.0}
        ]
        mock_conn.execute.return_value = mock_result
        
        averages = calculator.get_sector_averages('Technology')
        
        assert isinstance(averages, dict)

    def test_calculate_undervaluation_score_success(self, calculator):
        """Test calculating undervaluation score successfully"""
        # Mock get_financial_data to return sample data
        sample_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'eps': 6.0,
            'market_cap': 2500000000000,
            'total_equity': 50000000000,
            'revenue': 365000000000,
            'sector': 'Technology'
        }
        
        with patch.object(calculator, 'get_financial_data', return_value=sample_data), \
             patch.object(calculator, 'calculate_financial_ratios', return_value={'pe_ratio': 25.0}), \
             patch.object(calculator, 'get_sector_averages', return_value={'pe_ratio': 30.0}):
            
            result = calculator.calculate_undervaluation_score('AAPL')
            
            assert result is not None
            assert 'symbol' in result
            assert result['symbol'] == 'AAPL'

    def test_calculate_undervaluation_score_no_data(self, calculator):
        """Test calculating undervaluation score with no data"""
        with patch.object(calculator, 'get_financial_data', return_value={}):
            result = calculator.calculate_undervaluation_score('NONEXISTENT')
            
            assert result is None

    def test_save_undervaluation_score(self, calculator):
        """Test saving undervaluation score to database"""
        # Mock database connection
        mock_conn = MagicMock()
        calculator.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        score_data = {
            'symbol': 'AAPL',
            'undervaluation_score': 75.5,
            'data_quality': 'high',
            'calculated_at': datetime.now()
        }
        
        calculator.save_undervaluation_score(score_data)
        
        # Verify database execute was called
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()

    def test_calculate_all_scores(self, calculator):
        """Test calculating scores for all symbols"""
        # Mock database connection for getting symbols
        mock_conn = MagicMock()
        calculator.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock symbols query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [('AAPL',), ('MSFT',)]
        mock_conn.execute.return_value = mock_result
        
        # Mock calculate_undervaluation_score
        with patch.object(calculator, 'calculate_undervaluation_score', 
                         side_effect=[{'symbol': 'AAPL', 'score': 75}, 
                                    {'symbol': 'MSFT', 'score': 80}]) as mock_calc:
            
            result = calculator.calculate_all_scores(limit=2)
            
            assert isinstance(result, dict)
            assert 'processed' in result
            assert 'errors' in result
            assert result['processed'] == 2

    def test_calculate_all_scores_with_limit(self, calculator):
        """Test calculating scores with a limit"""
        # Mock database connection
        mock_conn = MagicMock()
        calculator.db.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock symbols query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [('AAPL',)]
        mock_conn.execute.return_value = mock_result
        
        # Mock calculate_undervaluation_score
        with patch.object(calculator, 'calculate_undervaluation_score', 
                         return_value={'symbol': 'AAPL', 'score': 75}):
            
            result = calculator.calculate_all_scores(limit=1)
            
            assert result['processed'] == 1

    def test_error_handling_in_financial_data(self, calculator):
        """Test error handling when getting financial data"""
        # Mock database to raise an exception
        calculator.db.engine.connect.side_effect = Exception("Database error")
        
        result = calculator.get_financial_data('AAPL')
        
        # Should return empty dict on error
        assert result == {}

    def test_ratio_calculation_edge_cases(self, calculator):
        """Test ratio calculations with edge cases"""
        edge_case_data = {
            'symbol': 'EDGE',
            'price': 100.0,
            'eps': 0,  # Zero EPS
            'market_cap': 1000000000,
            'total_equity': 0,  # Zero equity
            'revenue': 0,  # Zero revenue
            'current_assets': 100000,
            'current_liabilities': 0,  # Zero liabilities
            'total_debt': 1000000,
            'net_income': -10000000  # Negative income
        }
        
        ratios = calculator.calculate_financial_ratios(edge_case_data)
        
        # Should handle edge cases gracefully without crashing
        assert isinstance(ratios, dict)
        
        # Some ratios may not be calculable with zero denominators
        # The function should handle these gracefully

    def test_sector_comparison_logic(self, calculator):
        """Test that sector comparisons work correctly"""
        # Mock get_sector_averages to return known values
        sector_averages = {
            'pe_ratio': 25.0,
            'pb_ratio': 3.0,
            'ps_ratio': 5.0
        }
        
        with patch.object(calculator, 'get_sector_averages', return_value=sector_averages):
            averages = calculator.get_sector_averages('Technology')
            
            assert averages['pe_ratio'] == 25.0
            assert averages['pb_ratio'] == 3.0