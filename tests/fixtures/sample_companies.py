"""
Sample S&P 500 Companies Test Fixtures
Provides realistic test data for company testing
"""

SAMPLE_SP500_COMPANIES = [
    {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Information Technology'},
    {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Information Technology'}, 
    {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Communication Services'},
    {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary'},
    {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Information Technology'},
    {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Communication Services'},
    {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Discretionary'},
    {'symbol': 'AVGO', 'name': 'Broadcom Inc.', 'sector': 'Information Technology'},
    {'symbol': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Staples'},
    {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financials'},
    {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Health Care'},
    {'symbol': 'V', 'name': 'Visa Inc.', 'sector': 'Financials'},
    {'symbol': 'PG', 'name': 'Procter & Gamble Co.', 'sector': 'Consumer Staples'},
    {'symbol': 'UNH', 'name': 'UnitedHealth Group Inc.', 'sector': 'Health Care'},
    {'symbol': 'HD', 'name': 'Home Depot Inc.', 'sector': 'Consumer Discretionary'},
    {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Communication Services'},
    {'symbol': 'BAC', 'name': 'Bank of America Corp.', 'sector': 'Financials'},
    {'symbol': 'ABBV', 'name': 'AbbVie Inc.', 'sector': 'Health Care'},
    {'symbol': 'ORCL', 'name': 'Oracle Corporation', 'sector': 'Information Technology'},
    {'symbol': 'KO', 'name': 'Coca-Cola Co.', 'sector': 'Consumer Staples'}
]

SAMPLE_COMPANY_PROFILES = [
    {'symbol': 'AAPL', 'companyname': 'Apple Inc.', 'price': 150.25, 'mktcap': 2500000, 'industry': 'Technology'},
    {'symbol': 'MSFT', 'companyname': 'Microsoft Corporation', 'price': 330.75, 'mktcap': 2400000, 'industry': 'Technology'},
    {'symbol': 'GOOGL', 'companyname': 'Alphabet Inc.', 'price': 2650.50, 'mktcap': 1700000, 'industry': 'Technology'},
    {'symbol': 'AMZN', 'companyname': 'Amazon.com Inc.', 'price': 3100.25, 'mktcap': 1600000, 'industry': 'E-commerce'},
    {'symbol': 'NVDA', 'companyname': 'NVIDIA Corporation', 'price': 450.80, 'mktcap': 1100000, 'industry': 'Semiconductors'},
    {'symbol': 'META', 'companyname': 'Meta Platforms Inc.', 'price': 280.45, 'mktcap': 750000, 'industry': 'Social Media'},
    {'symbol': 'TSLA', 'companyname': 'Tesla Inc.', 'price': 220.15, 'mktcap': 700000, 'industry': 'Automotive'},
    {'symbol': 'WMT', 'companyname': 'Walmart Inc.', 'price': 155.80, 'mktcap': 425000, 'industry': 'Retail'},
    {'symbol': 'JPM', 'companyname': 'JPMorgan Chase & Co.', 'price': 145.60, 'mktcap': 430000, 'industry': 'Banking'},
    {'symbol': 'JNJ', 'companyname': 'Johnson & Johnson', 'price': 165.30, 'mktcap': 435000, 'industry': 'Pharmaceuticals'}
]

SAMPLE_UNDERVALUATION_SCORES = [
    {'symbol': 'AAPL', 'undervaluation_score': 75.5, 'data_quality': 'high'},
    {'symbol': 'MSFT', 'undervaluation_score': 68.2, 'data_quality': 'high'}, 
    {'symbol': 'GOOGL', 'undervaluation_score': 82.1, 'data_quality': 'high'},
    {'symbol': 'AMZN', 'undervaluation_score': 71.8, 'data_quality': 'medium'},
    {'symbol': 'NVDA', 'undervaluation_score': 89.3, 'data_quality': 'high'}
]