import pytest
import pandas as pd
from data_access_layer import StockDataService
from database import DatabaseManager

@pytest.fixture
def db_manager_with_data():
    import tempfile
    import os
    from unittest.mock import patch
    
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False)
    db_path = temp_db.name
    temp_db.close()
    
    # Use environment variable patching
    with patch.dict(os.environ, {'DATABASE_PATH': db_path}):
        manager = DatabaseManager()

    # Insert sample S&P 500 constituents
    sp500_data = {
        'symbol': ['AAPL', 'MSFT', 'GOOG', 'JPM', 'XOM'],
        'name': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'JPMorgan Chase & Co.', 'Exxon Mobil Corp.'],
        'sector': ['Technology', 'Technology', 'Communication Services', 'Financials', 'Energy'],
        'sub_sector': ['Consumer Electronics', 'Software', 'Interactive Media & Services', 'Diversified Banks', 'Integrated Oil & Gas'],
        'headquarters_location': ['Cupertino', 'Redmond', 'Mountain View', 'New York', 'Irving'],
        'date_first_added': ['1980-12-12', '1986-03-13', '2004-08-19', '1976-06-30', '1928-10-01'],
        'cik': ['1', '2', '3', '4', '5'],
        'founded': ['1976', '1975', '1998', '1799', '1870']
    }
    manager.insert_sp500_constituents(pd.DataFrame(sp500_data))

    # Insert sample company profiles
    profile_data = [
        {'symbol': 'AAPL', 'companyname': 'Apple Inc.', 'price': 170.0, 'mktcap': 2800000000000, 'sector': 'Technology', 'beta': 1.2},
        {'symbol': 'MSFT', 'companyname': 'Microsoft Corp.', 'price': 400.0, 'mktcap': 3000000000000, 'sector': 'Technology', 'beta': 0.9},
        {'symbol': 'GOOG', 'companyname': 'Alphabet Inc.', 'price': 150.0, 'mktcap': 1900000000000, 'sector': 'Communication Services', 'beta': 1.1},
        {'symbol': 'JPM', 'companyname': 'JPMorgan Chase & Co.', 'price': 180.0, 'mktcap': 500000000000, 'sector': 'Financials', 'beta': 1.0},
    ]
    for profile in profile_data:
        manager.insert_company_profile(profile)

    # Insert sample undervaluation scores
    undervaluation_scores = [
        {'symbol': 'AAPL', 'sector': 'Technology', 'undervaluation_score': 75.5, 'valuation_score': 70.0, 'quality_score': 80.0, 'strength_score': 78.0, 'risk_score': 60.0, 'data_quality': 'high', 'price': 170.0, 'mktcap': 2800000000000},
        {'symbol': 'MSFT', 'sector': 'Technology', 'undervaluation_score': 60.2, 'valuation_score': 55.0, 'quality_score': 65.0, 'strength_score': 62.0, 'risk_score': 55.0, 'data_quality': 'high', 'price': 400.0, 'mktcap': 3000000000000},
        {'symbol': 'GOOG', 'sector': 'Communication Services', 'undervaluation_score': 88.1, 'valuation_score': 90.0, 'quality_score': 85.0, 'strength_score': 87.0, 'risk_score': 90.0, 'data_quality': 'high', 'price': 150.0, 'mktcap': 1900000000000},
        {'symbol': 'JPM', 'sector': 'Financials', 'undervaluation_score': 45.0, 'valuation_score': 40.0, 'quality_score': 50.0, 'strength_score': 48.0, 'risk_score': 40.0, 'data_quality': 'medium', 'price': 180.0, 'mktcap': 500000000000},
    ]
    manager.insert_undervaluation_scores(undervaluation_scores)

    # Insert sample historical prices
    historical_prices = [
        {'symbol': 'AAPL', 'date': '2023-01-01', 'open': 100, 'high': 105, 'low': 99, 'close': 104, 'volume': 100000},
        {'symbol': 'AAPL', 'date': '2023-01-02', 'open': 104, 'high': 106, 'low': 103, 'close': 105, 'volume': 120000},
        {'symbol': 'MSFT', 'date': '2023-01-01', 'open': 200, 'high': 205, 'low': 199, 'close': 204, 'volume': 50000},
    ]
    for price_data in historical_prices:
        df = pd.DataFrame([price_data])
        manager.insert_historical_prices(price_data['symbol'], df)

    yield manager
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass

@pytest.fixture
def stock_service(db_manager_with_data):
    service = StockDataService()
    # Directly inject the prepared database manager
    service.db_manager = db_manager_with_data
    return service

def test_get_all_stocks_with_scores(stock_service):
    stocks = stock_service.get_all_stocks_with_scores()
    assert len(stocks) == 5 # 5 S&P 500 constituents
    
    # Check if data is correctly joined and ordered
    tech_stocks = [s for s in stocks if s['sector'] == 'Technology']
    assert len(tech_stocks) == 2
    assert tech_stocks[0]['symbol'] == 'AAPL' # Ordered by score DESC, then symbol
    assert tech_stocks[0]['undervaluation_score'] == 75.5
    assert tech_stocks[1]['symbol'] == 'MSFT'
    assert tech_stocks[1]['undervaluation_score'] == 60.2

    # Check a stock with no undervaluation score (XOM)
    xom_stock = next((s for s in stocks if s['symbol'] == 'XOM'), None)
    assert xom_stock is not None
    assert xom_stock['undervaluation_score'] is None
    assert xom_stock['has_profile'] == 0

def test_get_stock_summary_stats(stock_service):
    stocks = stock_service.get_all_stocks_with_scores()
    stats = stock_service.get_stock_summary_stats(stocks)
    
    assert stats['total_stocks'] == 5
    assert stats['stocks_with_profiles'] == 4 # AAPL, MSFT, GOOG, JPM have profiles
    assert stats['unique_sectors'] == 4 # Technology, Communication Services, Financials, Energy
    assert 'Technology' in stats['sectors']

def test_get_stock_basic_info(stock_service):
    aapl_info = stock_service.get_stock_basic_info('AAPL')
    assert aapl_info is not None
    assert aapl_info['symbol'] == 'AAPL'
    assert aapl_info['name'] == 'Apple Inc.'
    assert aapl_info['sector'] == 'Technology'

    non_existent_info = stock_service.get_stock_basic_info('NONEXISTENT')
    assert non_existent_info is None

def test_get_stock_company_profile(stock_service):
    aapl_profile = stock_service.get_stock_company_profile('AAPL')
    assert aapl_profile is not None
    assert aapl_profile['companyname'] == 'Apple Inc.'
    assert aapl_profile['price'] == 170.0

    xom_profile = stock_service.get_stock_company_profile('XOM')
    assert xom_profile is None # XOM has no profile in test data

def test_get_stock_undervaluation_score(stock_service):
    aapl_score = stock_service.get_stock_undervaluation_score('AAPL')
    assert aapl_score is not None
    assert aapl_score['undervaluation_score'] == 75.5

    xom_score = stock_service.get_stock_undervaluation_score('XOM')
    assert xom_score is None # XOM has no score in test data

def test_get_stock_historical_prices(stock_service):
    aapl_prices = stock_service.get_stock_historical_prices('AAPL', limit=1)
    assert len(aapl_prices) == 1
    assert aapl_prices[0]['date'] == '2023-01-02' # Latest date

    msft_prices = stock_service.get_stock_historical_prices('MSFT')
    assert len(msft_prices) == 1

    non_existent_prices = stock_service.get_stock_historical_prices('NONEXISTENT')
    assert len(non_existent_prices) == 0

def test_get_stocks_by_sector(stock_service):
    tech_stocks = stock_service.get_stocks_by_sector('Technology')
    assert len(tech_stocks) == 2
    assert all(s['sector'] == 'Technology' for s in tech_stocks)
    assert tech_stocks[0]['symbol'] == 'AAPL' # Ordered by score DESC

    energy_stocks = stock_service.get_stocks_by_sector('Energy')
    assert len(energy_stocks) == 1
    assert energy_stocks[0]['symbol'] == 'XOM'
    assert energy_stocks[0]['undervaluation_score'] is None

    non_existent_sector = stock_service.get_stocks_by_sector('NonExistentSector')
    assert len(non_existent_sector) == 0

def test_get_sector_analysis(stock_service):
    sector_analysis = stock_service.get_sector_analysis()
    assert len(sector_analysis) == 4 # Technology, Communication Services, Financials, Energy

    tech_sector = next((s for s in sector_analysis if s['sector'] == 'Technology'), None)
    assert tech_sector is not None
    assert tech_sector['total_stocks'] == 2
    assert tech_sector['stocks_with_scores'] == 2
    assert tech_sector['avg_undervaluation_score'] == pytest.approx((75.5 + 60.2) / 2)

    energy_sector = next((s for s in sector_analysis if s['sector'] == 'Energy'), None)
    assert energy_sector is not None
    assert energy_sector['total_stocks'] == 1
    assert energy_sector['stocks_with_scores'] == 0 # XOM has no score
    assert energy_sector['avg_undervaluation_score'] is None # Or 0 depending on implementation

def test_search_stocks(stock_service):
    # Search by symbol exact match
    search_aapl = stock_service.search_stocks('AAPL')
    assert len(search_aapl) == 1
    assert search_aapl[0]['symbol'] == 'AAPL'

    # Search by partial name
    search_microsoft = stock_service.search_stocks('Micro')
    assert len(search_microsoft) == 1
    assert search_microsoft[0]['symbol'] == 'MSFT'

    # Search by partial symbol
    search_jp = stock_service.search_stocks('JP')
    assert len(search_jp) == 1
    assert search_jp[0]['symbol'] == 'JPM'

    # Case-insensitive search
    search_apple_lower = stock_service.search_stocks('aapl')
    assert len(search_apple_lower) == 1
    assert search_apple_lower[0]['symbol'] == 'AAPL'

    # Search with limit
    search_tech_limit = stock_service.search_stocks('Tech', limit=1)
    assert len(search_tech_limit) == 1

    # No match
    search_none = stock_service.search_stocks('XYZ')
    assert len(search_none) == 0
