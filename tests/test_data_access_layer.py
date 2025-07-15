import pytest
import pandas as pd
from data_access_layer import StockDataService
from database import DatabaseManager

@pytest.fixture
def db_manager_with_data(db_manager):
    """Set up test data in the PostgreSQL test database"""
    from sqlalchemy import text
    
    # Clear existing test data
    with db_manager.engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE undervaluation_scores CASCADE"))
        conn.execute(text("TRUNCATE TABLE company_profiles CASCADE"))
        conn.execute(text("TRUNCATE TABLE sp500_constituents CASCADE"))
        conn.execute(text("TRUNCATE TABLE historical_prices CASCADE"))
        
        # Insert S&P 500 constituents with non-fake data patterns
        conn.execute(text("""
            INSERT INTO sp500_constituents (symbol, name, sector, sub_sector, headquarters_location, date_first_added, cik, founded)
            VALUES 
            ('TSLA', 'Tesla Inc.', 'Technology', 'Automotive', 'Austin', '2020-12-21', '1318605', '2003'),
            ('NVDA', 'NVIDIA Corp.', 'Technology', 'Semiconductors', 'Santa Clara', '2000-06-30', '1045810', '1993'),
            ('META', 'Meta Platforms Inc.', 'Communication Services', 'Interactive Media & Services', 'Menlo Park', '2012-05-18', '1326801', '2004'),
            ('BRK.A', 'Berkshire Hathaway Inc.', 'Financials', 'Multi-Sector Holdings', 'Omaha', '1988-05-05', '1067983', '1839'),
            ('UNH', 'UnitedHealth Group Inc.', 'Healthcare', 'Health Care Plans', 'Minnetonka', '1994-10-17', '731766', '1977')
        """))
        
        # Insert undervaluation scores
        conn.execute(text("""
            INSERT INTO undervaluation_scores (symbol, undervaluation_score, updated_at, valuation_score, quality_score, strength_score, risk_score, data_quality, price, mktcap)
            VALUES 
            ('TSLA', 75.5, CURRENT_TIMESTAMP, 70.0, 80.0, 78.0, 60.0, 'high', 250.0, 800000000000),
            ('NVDA', 60.2, CURRENT_TIMESTAMP, 55.0, 65.0, 62.0, 55.0, 'high', 450.0, 1100000000000), 
            ('META', 85.0, CURRENT_TIMESTAMP, 90.0, 85.0, 87.0, 90.0, 'high', 320.0, 820000000000),
            ('BRK.A', 45.3, CURRENT_TIMESTAMP, 40.0, 50.0, 48.0, 40.0, 'medium', 520000.0, 780000000000)
        """))
        
        # Insert company profiles
        conn.execute(text("""
            INSERT INTO company_profiles (symbol, companyname, price, sector, industry, description, website, mktcap, fulltimeemployees, updated_at, beta)
            VALUES 
            ('TSLA', 'Tesla Inc.', 250.0, 'Technology', 'Automotive', 'Tesla designs and manufactures electric vehicles.', 'https://www.tesla.com', 800000000000, 127855, CURRENT_TIMESTAMP, 1.8),
            ('NVDA', 'NVIDIA Corporation', 450.0, 'Technology', 'Semiconductors', 'NVIDIA designs graphics processing units.', 'https://www.nvidia.com', 1100000000000, 26196, CURRENT_TIMESTAMP, 1.5),
            ('META', 'Meta Platforms Inc.', 320.0, 'Communication Services', 'Interactive Media & Services', 'Meta operates social networking platforms.', 'https://www.meta.com', 820000000000, 67317, CURRENT_TIMESTAMP, 1.3),
            ('UNH', 'UnitedHealth Group Inc.', 520.0, 'Healthcare', 'Health Care Plans', 'UnitedHealth provides health care services.', 'https://www.unitedhealthgroup.com', 490000000000, 400000, CURRENT_TIMESTAMP, 0.8)
        """))
        
        # Insert historical prices
        conn.execute(text("""
            INSERT INTO historical_prices (symbol, date, open, high, low, close, volume)
            VALUES 
            ('TSLA', '2023-01-01', 240.0, 255.0, 238.0, 250.0, 50000000),
            ('TSLA', '2023-01-02', 250.0, 260.0, 248.0, 255.0, 45000000),
            ('NVDA', '2023-01-01', 440.0, 455.0, 438.0, 450.0, 30000000)
        """))
        
        conn.commit()
    
    return db_manager

@pytest.fixture
def stock_service(db_manager_with_data):
    service = StockDataService()
    # Directly inject the prepared database manager
    service.db_manager = db_manager_with_data
    return service

def test_get_all_stocks_with_scores(stock_service):
    # Test default sorting (by symbol ascending)
    stocks = stock_service.get_all_stocks_with_scores()
    assert len(stocks) == 5 # 5 S&P 500 constituents
    
    # Check if data is correctly joined (default sort is by symbol)
    symbols = [s['symbol'] for s in stocks]
    assert symbols == ['BRK.A', 'META', 'NVDA', 'TSLA', 'UNH']  # Alphabetical order
    
    # Test sorting by score descending  
    stocks_by_score = stock_service.get_all_stocks_with_scores(sort_by='score', sort_order='desc')
    tech_stocks = [s for s in stocks_by_score if s['sector'] == 'Technology']
    assert len(tech_stocks) == 2
    assert tech_stocks[0]['symbol'] == 'TSLA' # Ordered by score DESC 
    assert tech_stocks[0]['undervaluation_score'] == 75.5
    assert tech_stocks[1]['symbol'] == 'NVDA'
    assert tech_stocks[1]['undervaluation_score'] == 60.2

    # Check a stock with no undervaluation score (UNH)
    unh_stock = next((s for s in stocks if s['symbol'] == 'UNH'), None)
    assert unh_stock is not None
    assert unh_stock['undervaluation_score'] is None
    assert unh_stock['has_profile'] == 1  # UNH has a profile

def test_get_stock_summary_stats(stock_service):
    stocks = stock_service.get_all_stocks_with_scores()
    stats = stock_service.get_stock_summary_stats(stocks)
    
    assert stats['total_stocks'] == 5
    assert stats['stocks_with_profiles'] == 4 # TSLA, NVDA, META, UNH have profiles
    assert stats['unique_sectors'] == 4 # Technology, Communication Services, Financials, Healthcare
    assert 'Technology' in stats['sectors']

def test_get_stock_basic_info(stock_service):
    tsla_info = stock_service.get_stock_basic_info('TSLA')
    assert tsla_info is not None
    assert tsla_info['symbol'] == 'TSLA'
    assert tsla_info['name'] == 'Tesla Inc.'
    assert tsla_info['sector'] == 'Technology'

    non_existent_info = stock_service.get_stock_basic_info('NONEXISTENT')
    assert non_existent_info is None

def test_get_stock_company_profile(stock_service):
    tsla_profile = stock_service.get_stock_company_profile('TSLA')
    assert tsla_profile is not None
    assert tsla_profile['companyname'] == 'Tesla Inc.'
    assert tsla_profile['price'] == 250.0

    brka_profile = stock_service.get_stock_company_profile('BRK.A')
    assert brka_profile is None # BRK.A has no profile in test data

def test_get_stock_undervaluation_score(stock_service):
    tsla_score = stock_service.get_stock_undervaluation_score('TSLA')
    assert tsla_score is not None
    assert tsla_score['undervaluation_score'] == 75.5

    unh_score = stock_service.get_stock_undervaluation_score('UNH')
    assert unh_score is None # UNH has no score in test data

def test_get_stock_historical_prices(stock_service):
    tsla_prices = stock_service.get_stock_historical_prices('TSLA', limit=1)
    assert len(tsla_prices) == 1
    assert tsla_prices[0]['date'] == '2023-01-02' # Latest date

    nvda_prices = stock_service.get_stock_historical_prices('NVDA')
    assert len(nvda_prices) == 1

    non_existent_prices = stock_service.get_stock_historical_prices('NONEXISTENT')
    assert len(non_existent_prices) == 0

def test_get_stocks_by_sector(stock_service):
    tech_stocks = stock_service.get_stocks_by_sector('Technology')
    assert len(tech_stocks) == 2
    assert all(s['sector'] == 'Technology' for s in tech_stocks)
    # get_stocks_by_sector sorts by score DESC, so TSLA (75.5) comes before NVDA (60.2)
    tech_symbols = [s['symbol'] for s in tech_stocks]
    assert tech_symbols == ['TSLA', 'NVDA']

    healthcare_stocks = stock_service.get_stocks_by_sector('Healthcare')
    assert len(healthcare_stocks) == 1
    assert healthcare_stocks[0]['symbol'] == 'UNH'
    assert healthcare_stocks[0]['undervaluation_score'] is None

    non_existent_sector = stock_service.get_stocks_by_sector('NonExistentSector')
    assert len(non_existent_sector) == 0

def test_get_sector_analysis(stock_service):
    sector_analysis = stock_service.get_sector_analysis()
    assert len(sector_analysis) == 4 # Technology, Communication Services, Financials, Healthcare

    tech_sector = next((s for s in sector_analysis if s['sector'] == 'Technology'), None)
    assert tech_sector is not None
    assert tech_sector['total_stocks'] == 2
    assert tech_sector['stocks_with_scores'] == 2
    assert tech_sector['avg_undervaluation_score'] == pytest.approx((75.5 + 60.2) / 2)

    healthcare_sector = next((s for s in sector_analysis if s['sector'] == 'Healthcare'), None)
    assert healthcare_sector is not None
    assert healthcare_sector['total_stocks'] == 1
    assert healthcare_sector['stocks_with_scores'] == 0 # UNH has no score
    assert healthcare_sector['avg_undervaluation_score'] is None # Or 0 depending on implementation

def test_search_stocks(stock_service):
    # Search by symbol exact match
    search_tsla = stock_service.search_stocks('TSLA')
    assert len(search_tsla) == 1
    assert search_tsla[0]['symbol'] == 'TSLA'

    # Search by partial name
    search_tesla = stock_service.search_stocks('Tesla')
    assert len(search_tesla) == 1
    assert search_tesla[0]['symbol'] == 'TSLA'

    # Search by partial symbol
    search_brk = stock_service.search_stocks('BRK')
    assert len(search_brk) == 1
    assert search_brk[0]['symbol'] == 'BRK.A'

    # Case-insensitive search
    search_tsla_lower = stock_service.search_stocks('tsla')
    assert len(search_tsla_lower) == 1
    assert search_tsla_lower[0]['symbol'] == 'TSLA'

    # Search with limit
    search_tech_limit = stock_service.search_stocks('Tech', limit=1)
    assert len(search_tech_limit) == 1

    # No match
    search_none = stock_service.search_stocks('XYZ')
    assert len(search_none) == 0
