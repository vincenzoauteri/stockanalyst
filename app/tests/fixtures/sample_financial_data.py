"""
Sample Financial Data Test Fixtures
Provides realistic test data for financial testing
"""

from datetime import datetime, date

SAMPLE_HISTORICAL_PRICES = [
    {'symbol': 'AAPL', 'date': date(2024, 1, 1), 'open': 148.50, 'high': 152.30, 'low': 147.80, 'close': 150.25, 'volume': 45000000},
    {'symbol': 'AAPL', 'date': date(2024, 1, 2), 'open': 150.25, 'high': 151.75, 'low': 149.50, 'close': 151.20, 'volume': 42000000},
    {'symbol': 'MSFT', 'date': date(2024, 1, 1), 'open': 328.00, 'high': 333.50, 'low': 327.20, 'close': 330.75, 'volume': 28000000},
    {'symbol': 'MSFT', 'date': date(2024, 1, 2), 'open': 330.75, 'high': 332.40, 'low': 329.80, 'close': 331.95, 'volume': 26000000}
]

SAMPLE_CORPORATE_ACTIONS = [
    {'symbol': 'AAPL', 'action_type': 'dividend', 'action_date': date(2024, 2, 15), 'amount': 0.24, 'currency': 'USD'},
    {'symbol': 'MSFT', 'action_type': 'dividend', 'action_date': date(2024, 2, 20), 'amount': 0.75, 'currency': 'USD'},
    {'symbol': 'GOOGL', 'action_type': 'split', 'action_date': date(2024, 3, 1), 'split_ratio': '20:1'}
]

SAMPLE_INCOME_STATEMENTS = [
    {
        'symbol': 'AAPL',
        'period': 'annual',
        'calendar_year': 2023,
        'revenue': 383285000000,
        'cost_of_revenue': 214137000000,
        'gross_profit': 169148000000,
        'operating_expenses': 55013000000,
        'operating_income': 114135000000,
        'net_income': 96995000000
    },
    {
        'symbol': 'MSFT', 
        'period': 'annual',
        'calendar_year': 2023,
        'revenue': 211915000000,
        'cost_of_revenue': 65525000000,
        'gross_profit': 146390000000,
        'operating_expenses': 70051000000,
        'operating_income': 76339000000,
        'net_income': 72361000000
    }
]

SAMPLE_BALANCE_SHEETS = [
    {
        'symbol': 'AAPL',
        'period': 'annual', 
        'calendar_year': 2023,
        'total_assets': 352755000000,
        'total_liabilities': 290437000000,
        'total_equity': 62318000000,
        'cash_and_equivalents': 29965000000,
        'total_debt': 123930000000
    },
    {
        'symbol': 'MSFT',
        'period': 'annual',
        'calendar_year': 2023, 
        'total_assets': 411976000000,
        'total_liabilities': 205753000000,
        'total_equity': 206223000000,
        'cash_and_equivalents': 34704000000,
        'total_debt': 97714000000
    }
]

SAMPLE_CASH_FLOW_STATEMENTS = [
    {
        'symbol': 'AAPL',
        'period': 'annual',
        'calendar_year': 2023,
        'operating_cash_flow': 110543000000,
        'investing_cash_flow': -10959000000,
        'financing_cash_flow': -108488000000,
        'free_cash_flow': 99584000000
    },
    {
        'symbol': 'MSFT',
        'period': 'annual', 
        'calendar_year': 2023,
        'operating_cash_flow': 87582000000,
        'investing_cash_flow': -28388000000,
        'financing_cash_flow': -52773000000,
        'free_cash_flow': 65149000000
    }
]

SAMPLE_ANALYST_RECOMMENDATIONS = [
    {'symbol': 'AAPL', 'strong_buy': 15, 'buy': 25, 'hold': 8, 'sell': 2, 'strong_sell': 0},
    {'symbol': 'MSFT', 'strong_buy': 18, 'buy': 22, 'hold': 6, 'sell': 1, 'strong_sell': 0},
    {'symbol': 'GOOGL', 'strong_buy': 20, 'buy': 18, 'hold': 4, 'sell': 1, 'strong_sell': 0}
]