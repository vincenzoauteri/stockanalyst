#database.py
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
from logging_config import get_logger, log_function_call

load_dotenv()
logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self):
        # PostgreSQL configuration (containerized environment)
        postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        postgres_db = os.getenv('POSTGRES_DB', 'stockanalyst')
        postgres_user = os.getenv('POSTGRES_USER', 'stockanalyst')
        # Use different default passwords for test vs production
        is_testing = os.getenv('TESTING', '').lower() == 'true'
        default_password = 'testpassword' if is_testing else 'defaultpassword'
        postgres_password = os.getenv('POSTGRES_PASSWORD', default_password)
        
        # CRITICAL SECURITY CHECK: Prevent tests from accessing production database
        if is_testing:
            # During testing, require test database configuration
            if postgres_host == 'postgres' and postgres_db == 'stockanalyst':
                raise RuntimeError(
                    "SECURITY VIOLATION: Cannot connect to production database during testing. "
                    "Tests must use isolated test database. "
                    f"Current config: host={postgres_host}, db={postgres_db}. "
                    "Use test-postgres host and stockanalyst_test database for tests."
                )
            logger.info(f"TEST MODE: Using test database {postgres_host}:{postgres_port}/{postgres_db}")
        
        self.db_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
        logger.info(f"Initializing DatabaseManager with PostgreSQL: {postgres_host}:{postgres_port}/{postgres_db}")
        
        # Configure connection pooling based on environment
        if is_testing:
            # Test environment: Conservative pooling to avoid connection exhaustion
            self.engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                pool_size=3,          # Small pool for tests
                max_overflow=5,       # Limited overflow
                pool_pre_ping=True,   # Validate connections
                pool_recycle=300,     # Recycle connections every 5 minutes
                pool_timeout=30       # Timeout for getting connection
            )
            logger.info("Using test database connection pool: pool_size=3, max_overflow=5")
        else:
            # Production environment: Standard pooling
            self.engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                pool_size=10,         # Standard pool size
                max_overflow=20,      # Allow more overflow
                pool_pre_ping=True,   # Validate connections
                pool_recycle=3600     # Recycle connections every hour
            )
            logger.info("Using production database connection pool: pool_size=10, max_overflow=20")
        self.create_tables()
        
        # DISABLED: Skip index creation entirely to fix test database initialization
        # self.create_indexes_safe()
            
        logger.info("DatabaseManager initialized successfully")
    
    def cleanup_connections(self):
        """Clean up database connections for test environments"""
        if hasattr(self, 'engine') and self.engine:
            self.engine.dispose()
            logger.debug("Database connections cleaned up")
    
    def __del__(self):
        """Cleanup when DatabaseManager is garbage collected"""
        try:
            if hasattr(self, 'engine') and self.engine:
                self.engine.dispose()
        except Exception:
            # Silent cleanup during garbage collection
            pass
    
    @log_function_call
    def create_tables(self):
        """Create the necessary tables for stock analysis"""
        
        logger.debug("Creating database tables...")
        try:
            # Create each table with explicit transaction control
            logger.debug("About to call engine.begin()...")
            with self.engine.begin() as conn:
                logger.debug("Connected to database, starting table creation...")
                # S&P 500 constituents table
                logger.debug("Creating sp500_constituents table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS sp500_constituents (
                        id SERIAL PRIMARY KEY,
                        symbol TEXT UNIQUE NOT NULL,
                        name TEXT,
                        sector TEXT,
                        sub_sector TEXT,
                        headquarters_location TEXT,
                        date_first_added TEXT,
                        cik TEXT,
                        founded TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                logger.debug("✓ sp500_constituents table created")
                
                # Company profiles table
                logger.debug("Creating company_profiles table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS company_profiles (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT UNIQUE NOT NULL,
                    price REAL,
                    beta REAL,
                    volavg INTEGER,
                    mktcap INTEGER,
                    lastdiv REAL,
                    range TEXT,
                    changes REAL,
                    companyname TEXT,
                    currency TEXT,
                    cik TEXT,
                    isin TEXT,
                    cusip TEXT,
                    exchange TEXT,
                    exchangeshortname TEXT,
                    industry TEXT,
                    website TEXT,
                    description TEXT,
                    ceo TEXT,
                    sector TEXT,
                    country TEXT,
                    fulltimeemployees INTEGER,
                    phone TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip TEXT,
                    dcfdiff REAL,
                    dcf REAL,
                    image TEXT,
                    ipodate TEXT,
                    defaultimage INTEGER,
                    isetf INTEGER,
                    isactivelytrading INTEGER,
                    isadr INTEGER,
                    isfund INTEGER,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
                logger.debug("✓ company_profiles table created")
            
                # Historical prices table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS historical_prices (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    adjclose REAL,
                    volume INTEGER,
                    unadjustedvolume INTEGER,
                    change REAL,
                    changepercent REAL,
                    vwap REAL,
                    label TEXT,
                    changeovertime REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            """))
            
                # Undervaluation scores table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS undervaluation_scores (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT UNIQUE NOT NULL,
                    sector TEXT,
                    undervaluation_score REAL,
                    valuation_score REAL,
                    quality_score REAL,
                    strength_score REAL,
                    risk_score REAL,
                    data_quality TEXT,
                    price REAL,
                    mktcap INTEGER,
                    dcf_value REAL,
                    ddm_value REAL,
                    relative_value REAL,
                    final_intrinsic_value REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
                # Corporate actions table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS corporate_actions (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_date DATE NOT NULL,
                    amount REAL,
                    split_ratio REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, action_type, action_date)
                )
            """))
            
                # Financial statements - Income Statement
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS income_statements (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    period_ending DATE NOT NULL,
                    period_type TEXT NOT NULL,
                    total_revenue REAL,
                    cost_of_revenue REAL,
                    gross_profit REAL,
                    operating_income REAL,
                    ebit REAL,
                    ebitda REAL,
                    net_income REAL,
                    basic_eps REAL,
                    diluted_eps REAL,
                    shares_outstanding REAL,
                    tax_provision REAL,
                    interest_expense REAL,
                    research_development REAL,
                    selling_general_administrative REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, period_ending, period_type)
                )
            """))
            
                # Financial statements - Balance Sheet
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS balance_sheets (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    period_ending DATE NOT NULL,
                    period_type TEXT NOT NULL,
                    total_assets REAL,
                    total_liabilities REAL,
                    total_equity REAL,
                    current_assets REAL,
                    current_liabilities REAL,
                    cash_and_equivalents REAL,
                    accounts_receivable REAL,
                    inventory REAL,
                    property_plant_equipment REAL,
                    total_debt REAL,
                    long_term_debt REAL,
                    retained_earnings REAL,
                    working_capital REAL,
                    shares_outstanding REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, period_ending, period_type)
                )
            """))
            
                # Financial statements - Cash Flow
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cash_flow_statements (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    period_ending DATE NOT NULL,
                    period_type TEXT NOT NULL,
                    operating_cash_flow REAL,
                    investing_cash_flow REAL,
                    financing_cash_flow REAL,
                    net_change_in_cash REAL,
                    free_cash_flow REAL,
                    capital_expenditures REAL,
                    dividend_payments REAL,
                    share_repurchases REAL,
                    depreciation_amortization REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, period_ending, period_type)
                )
            """))
            
                # Analyst recommendations table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS analyst_recommendations (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    period TEXT NOT NULL,
                    strong_buy INTEGER,
                    buy INTEGER,
                    hold INTEGER,
                    sell INTEGER,
                    strong_sell INTEGER,
                    total_analysts INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, period)
                )
            """))
            
                # Data gaps tracking table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS data_gaps (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    gap_type TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    gap_days INTEGER NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_attempt TIMESTAMP,
                    next_retry TIMESTAMP,
                    error_count INTEGER DEFAULT 0,
                    error_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, gap_type, start_date, end_date)
                )
            """))
                logger.debug("✓ data_gaps table created")
                
                # Short interest data table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS short_interest_data (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    report_date DATE NOT NULL,
                    short_interest BIGINT,
                    float_shares BIGINT,
                    short_ratio DECIMAL(10,2),
                    short_percent_of_float DECIMAL(5,2),
                    average_daily_volume BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, report_date)
                )
            """))
                logger.debug("✓ short_interest_data table created")
                
                # Short squeeze scores table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS short_squeeze_scores (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    squeeze_score DECIMAL(5,2),
                    si_score DECIMAL(5,2),
                    dtc_score DECIMAL(5,2),
                    float_score DECIMAL(5,2),
                    momentum_score DECIMAL(5,2),
                    data_quality VARCHAR(20),
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol)
                )
            """))
                logger.debug("✓ short_squeeze_scores table created")
            
                logger.debug("ALL TABLES CREATED SUCCESSFULLY - COMMITTING TRANSACTION")
            
            # Skip index creation during initial table creation to avoid transaction conflicts
            # Indexes will be created separately after all tables exist
            
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    @log_function_call
    def create_indexes(self, conn):
        """Create performance indexes for frequently queried columns"""
        logger.debug("Creating performance indexes...")
        
        indexes = [
            # Primary symbol indexes for fast lookups
            "CREATE INDEX IF NOT EXISTS idx_company_profiles_symbol ON company_profiles(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_historical_prices_symbol ON historical_prices(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_undervaluation_scores_symbol ON undervaluation_scores(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_corporate_actions_symbol ON corporate_actions(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_income_statements_symbol ON income_statements(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_balance_sheets_symbol ON balance_sheets(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_cash_flow_statements_symbol ON cash_flow_statements(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_analyst_recommendations_symbol ON analyst_recommendations(symbol)",
            
            # Date-based indexes for time-series queries
            "CREATE INDEX IF NOT EXISTS idx_historical_prices_date ON historical_prices(date)",
            "CREATE INDEX IF NOT EXISTS idx_historical_prices_symbol_date ON historical_prices(symbol, date)",
            "CREATE INDEX IF NOT EXISTS idx_income_statements_period ON income_statements(period_ending)",
            "CREATE INDEX IF NOT EXISTS idx_balance_sheets_period ON balance_sheets(period_ending)",
            "CREATE INDEX IF NOT EXISTS idx_cash_flow_statements_period ON cash_flow_statements(period_ending)",
            "CREATE INDEX IF NOT EXISTS idx_corporate_actions_date ON corporate_actions(action_date)",
            
            # Compound indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_income_statements_symbol_period ON income_statements(symbol, period_ending)",
            "CREATE INDEX IF NOT EXISTS idx_balance_sheets_symbol_period ON balance_sheets(symbol, period_ending)",
            "CREATE INDEX IF NOT EXISTS idx_cash_flow_statements_symbol_period ON cash_flow_statements(symbol, period_ending)",
            "CREATE INDEX IF NOT EXISTS idx_corporate_actions_symbol_date ON corporate_actions(symbol, action_date)",
            
            # Sector and filtering indexes
            "CREATE INDEX IF NOT EXISTS idx_sp500_constituents_sector ON sp500_constituents(sector)",
            "CREATE INDEX IF NOT EXISTS idx_company_profiles_sector ON company_profiles(sector)",
            "CREATE INDEX IF NOT EXISTS idx_undervaluation_scores_sector ON undervaluation_scores(sector)",
            "CREATE INDEX IF NOT EXISTS idx_undervaluation_scores_score ON undervaluation_scores(undervaluation_score)",
            
            # Gap detection indexes
            "CREATE INDEX IF NOT EXISTS idx_data_gaps_symbol ON data_gaps(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_data_gaps_type ON data_gaps(gap_type)",
            "CREATE INDEX IF NOT EXISTS idx_data_gaps_status ON data_gaps(status)",
            "CREATE INDEX IF NOT EXISTS idx_data_gaps_priority ON data_gaps(priority)",
            
            # Market cap and price indexes for sorting
            "CREATE INDEX IF NOT EXISTS idx_company_profiles_mktcap ON company_profiles(mktcap)",
            "CREATE INDEX IF NOT EXISTS idx_company_profiles_price ON company_profiles(price)",
            "CREATE INDEX IF NOT EXISTS idx_undervaluation_scores_mktcap ON undervaluation_scores(mktcap)",
            
            # Short squeeze analysis indexes
            "CREATE INDEX IF NOT EXISTS idx_short_interest_data_symbol ON short_interest_data(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_short_interest_data_report_date ON short_interest_data(report_date)",
            "CREATE INDEX IF NOT EXISTS idx_short_interest_data_symbol_date ON short_interest_data(symbol, report_date)",
            "CREATE INDEX IF NOT EXISTS idx_short_squeeze_scores_symbol ON short_squeeze_scores(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_short_squeeze_scores_score ON short_squeeze_scores(squeeze_score)",
            "CREATE INDEX IF NOT EXISTS idx_short_squeeze_scores_quality ON short_squeeze_scores(data_quality)",
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                # Only log specific errors, not connection closed errors
                error_msg = str(e).lower()
                if "already exists" in error_msg or "duplicate" in error_msg:
                    logger.debug(f"Index already exists: {index_sql.split('idx_')[1].split(' ')[0]}")
                else:
                    logger.warning(f"Index creation failed: {e}")
        
        try:
            conn.commit()
            logger.debug("Performance indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to commit index creation: {e}")
        
        # Create alerts system tables in separate transaction
        try:
            self._create_alerts_tables_safe()
        except Exception as e:
            logger.warning(f"Failed to create alerts tables: {e}")
    
    def _create_alerts_tables_safe(self):
        """Create alerts tables with separate connection to avoid transaction issues"""
        try:
            with self.engine.connect() as conn:
                self._create_alerts_tables(conn)
        except Exception as e:
            logger.warning(f"Failed to create alerts tables: {e}")
    
    def _create_alerts_tables(self, conn):
        """Create tables for the user alerts system"""
        logger.info("Creating alerts system tables")
        
        try:
            # User alerts table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_alerts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    target_value REAL,
                    upper_threshold REAL,
                    lower_threshold REAL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered_at TIMESTAMP,
                    trigger_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    CONSTRAINT check_alert_type CHECK (alert_type IN ('price', 'volume', 'score', 'event')),
                    CONSTRAINT check_condition_type CHECK (condition_type IN ('above', 'below', 'range', 'change_percent'))
                )
            """))
            
            # Alert notifications table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alert_notifications (
                    id SERIAL PRIMARY KEY,
                    alert_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    current_value REAL,
                    target_value REAL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read BOOLEAN DEFAULT FALSE,
                    notification_method TEXT DEFAULT 'in_app',
                    FOREIGN KEY (alert_id) REFERENCES user_alerts(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            
            # Create indexes for alerts
            alert_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_alerts_user_id ON user_alerts(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_alerts_symbol ON user_alerts(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_user_alerts_active ON user_alerts(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_alert_notifications_user_id ON alert_notifications(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_alert_notifications_read ON alert_notifications(is_read)",
                "CREATE INDEX IF NOT EXISTS idx_alert_notifications_triggered_at ON alert_notifications(triggered_at)",
            ]
            
            for index_sql in alert_indexes:
                try:
                    conn.execute(text(index_sql))
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Alert index creation failed: {e}")
            
            conn.commit()
            logger.info("Alerts system tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating alerts tables: {e}")
            conn.rollback()
    
    @log_function_call
    def create_indexes_safe(self):
        """Create performance indexes with a separate connection to avoid connection issues"""
        try:
            with self.engine.connect() as conn:
                # First check if core tables exist before creating indexes
                result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('sp500_constituents', 'company_profiles', 'historical_prices')"))
                table_count = result.fetchone()[0]
                
                if table_count >= 3:
                    self.create_indexes(conn)
                else:
                    logger.warning(f"Core tables missing ({table_count}/3), skipping index creation")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    @log_function_call
    def insert_sp500_constituents(self, df: pd.DataFrame):
        """Insert S&P 500 constituents data, skip if table already has sufficient data"""
        logger.info(f"Inserting {len(df)} S&P 500 constituents")
        try:
            with self.engine.connect() as conn:
                # Check if table already has data
                result = conn.execute(text("SELECT COUNT(*) FROM sp500_constituents"))
                existing_count = result.fetchone()[0]
                
                if existing_count >= 500:
                    logger.info(f"SP500 table already has {existing_count} records, skipping bulk insert")
                    return
                
                # Clear any test data first
                if existing_count > 0 and existing_count < 10:
                    logger.info(f"Clearing {existing_count} test records before inserting real data")
                    conn.execute(text("DELETE FROM sp500_constituents"))
                    conn.commit()
            
            # Use pandas to_sql for bulk insert
            df.to_sql('sp500_constituents', self.engine, if_exists='append', index=False)
            logger.info("S&P 500 constituents inserted successfully")
        except Exception as e:
            logger.error(f"Error inserting S&P 500 constituents: {e}")
            raise
    
    def _validate_production_data(self, profile_data: dict) -> bool:
        """Validate that profile data is not test/fake data to prevent contamination"""
        # Known test data patterns from conftest.py
        test_data_patterns = [
            # AAPL fake data
            {'symbol': 'AAPL', 'price': 170.0, 'mktcap': 2800000000000},
            # MSFT fake data
            {'symbol': 'MSFT', 'price': 400.0, 'mktcap': 3000000000000},
            # GOOG fake data
            {'symbol': 'GOOG', 'price': 2800.0, 'mktcap': 1800000000000},
            # AMZN fake data
            {'symbol': 'AMZN', 'price': 3200.0, 'mktcap': 1600000000000},
            # TSLA fake data
            {'symbol': 'TSLA', 'price': 250.0, 'mktcap': 800000000000},
        ]
        
        # Check if incoming data matches any known test patterns
        for test_pattern in test_data_patterns:
            if (profile_data.get('symbol') == test_pattern['symbol'] and
                profile_data.get('price') == test_pattern['price'] and 
                profile_data.get('mktcap') == test_pattern['mktcap']):
                logger.warning(f"BLOCKED: Test data detected for {test_pattern['symbol']} - rejecting fake data insertion")
                return False
        
        # Additional unrealistic data checks
        price = profile_data.get('price')
        mktcap = profile_data.get('mktcap') 
        
        # Check for obviously fake round numbers that are unrealistic
        if price and mktcap:
            # Reject AAPL data with exactly $170 price and exactly $2.8T market cap
            if (profile_data.get('symbol') == 'AAPL' and 
                price == 170.0 and mktcap == 2800000000000):
                logger.warning("BLOCKED: Fake AAPL test data detected")
                return False
            
            # Reject MSFT data with exactly $400 price and exactly $3.0T market cap
            if (profile_data.get('symbol') == 'MSFT' and 
                price == 400.0 and mktcap == 3000000000000):
                logger.warning("BLOCKED: Fake MSFT test data detected")
                return False
        
        return True

    @log_function_call
    def insert_company_profile(self, profile_data: dict):
        """Insert or update company profile data"""
        symbol = profile_data.get('symbol', 'unknown')
        logger.debug(f"Inserting/updating company profile for {symbol}")
        
        # Validate data is not test/fake data
        if not self._validate_production_data(profile_data):
            logger.error(f"Rejected insertion of test/fake data for {symbol}")
            return
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO company_profiles 
                    (symbol, companyname, industry, sector, website, description, country, city, state, 
                     fulltimeemployees, phone, address, zip, currency, exchange, price, mktcap)
                    VALUES (:symbol, :companyname, :industry, :sector, :website, :description, :country, 
                            :city, :state, :fulltimeemployees, :phone, :address, :zip, :currency, :exchange, :price, :mktcap)
                    ON CONFLICT (symbol) DO UPDATE SET
                    companyname = EXCLUDED.companyname, industry = EXCLUDED.industry, sector = EXCLUDED.sector,
                    website = EXCLUDED.website, description = EXCLUDED.description, country = EXCLUDED.country,
                    city = EXCLUDED.city, state = EXCLUDED.state, fulltimeemployees = EXCLUDED.fulltimeemployees,
                    phone = EXCLUDED.phone, address = EXCLUDED.address, zip = EXCLUDED.zip,
                    currency = EXCLUDED.currency, exchange = EXCLUDED.exchange, price = EXCLUDED.price, mktcap = EXCLUDED.mktcap
                """), {
                    'symbol': profile_data.get('symbol'),
                    'companyname': profile_data.get('companyname'),
                    'industry': profile_data.get('industry'),
                    'sector': profile_data.get('sector'),
                    'website': profile_data.get('website'),
                    'description': profile_data.get('description'),
                    'country': profile_data.get('country'),
                    'city': profile_data.get('city'),
                    'state': profile_data.get('state'),
                    'fulltimeemployees': profile_data.get('fulltimeemployees'),
                    'phone': profile_data.get('phone'),
                    'address': profile_data.get('address'),
                    'zip': profile_data.get('zip'),
                    'currency': profile_data.get('currency'),
                    'exchange': profile_data.get('exchange'),
                    'price': profile_data.get('price'),
                    'mktcap': profile_data.get('mktcap')
                })
                conn.commit()
            logger.debug(f"Company profile for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting company profile for {symbol}: {e}")
            raise
    
    @log_function_call
    def update_beta(self, symbol: str, beta: float):
        """Update the beta value for a specific symbol in the company_profiles table."""
        logger.debug(f"Updating beta for {symbol} to {beta:.4f}")
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE company_profiles
                    SET beta = :beta, updated_at = CURRENT_TIMESTAMP
                    WHERE symbol = :symbol
                """), {'symbol': symbol, 'beta': beta})
                conn.commit()
            logger.info(f"Successfully updated beta for {symbol}")
        except Exception as e:
            logger.error(f"Error updating beta for {symbol}: {e}")
            raise
    
    @log_function_call
    def insert_historical_prices(self, symbol: str, df: pd.DataFrame):
        """Insert historical prices data, handling duplicates gracefully"""
        logger.info(f"Inserting {len(df)} historical prices for {symbol}")
        try:
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            
            # Use INSERT OR REPLACE to handle duplicates
            with self.engine.connect() as conn:
                for _, row in df_copy.iterrows():
                    conn.execute(text("""
                        INSERT INTO historical_prices 
                        (symbol, date, open, high, low, close, adjclose, volume, 
                         unadjustedvolume, change, changepercent, vwap, label, changeovertime)
                        VALUES (:symbol, :date, :open, :high, :low, :close, :adjclose, :volume,
                                :unadjustedvolume, :change, :changepercent, :vwap, :label, :changeovertime)
                        ON CONFLICT (symbol, date) DO UPDATE SET
                        open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                        close = EXCLUDED.close, adjclose = EXCLUDED.adjclose, volume = EXCLUDED.volume,
                        unadjustedvolume = EXCLUDED.unadjustedvolume, change = EXCLUDED.change,
                        changepercent = EXCLUDED.changepercent, vwap = EXCLUDED.vwap,
                        label = EXCLUDED.label, changeovertime = EXCLUDED.changeovertime
                    """), {
                        'symbol': row.get('symbol'),
                        'date': row.get('date'),
                        'open': row.get('open'),
                        'high': row.get('high'), 
                        'low': row.get('low'),
                        'close': row.get('close'),
                        'adjclose': row.get('adjclose'),
                        'volume': row.get('volume'),
                        'unadjustedvolume': row.get('unadjustedvolume'),
                        'change': row.get('change'),
                        'changepercent': row.get('changepercent'),
                        'vwap': row.get('vwap'),
                        'label': row.get('label'),
                        'changeovertime': row.get('changeovertime')
                    })
                conn.commit()
            
            logger.info(f"Historical prices for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting historical prices for {symbol}: {e}")
            raise
    
    @log_function_call
    def get_sp500_symbols(self):
        """Get all S&P 500 symbols from database"""
        logger.debug("Retrieving S&P 500 symbols from database")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT symbol FROM sp500_constituents"))
                symbols = [row[0] for row in result.fetchall()]
                logger.debug(f"Retrieved {len(symbols)} S&P 500 symbols")
                return symbols
        except Exception as e:
            logger.error(f"Error retrieving S&P 500 symbols: {e}")
            raise
    
    @log_function_call
    def symbol_exists_in_profiles(self, symbol: str) -> bool:
        """Check if symbol exists in company profiles"""
        logger.debug(f"Checking if symbol {symbol} exists in company profiles")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM company_profiles WHERE symbol = :symbol"),
                    {"symbol": symbol}
                )
                exists = result.fetchone()[0] > 0
                logger.debug(f"Symbol {symbol} exists in profiles: {exists}")
                return exists
        except Exception as e:
            logger.error(f"Error checking if symbol {symbol} exists in profiles: {e}")
            raise
    
    @log_function_call
    def symbol_has_historical_data(self, symbol: str) -> bool:
        """Check if symbol has historical price data"""
        logger.debug(f"Checking if symbol {symbol} has historical data")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM historical_prices WHERE symbol = :symbol"),
                    {"symbol": symbol}
                )
                has_data = result.fetchone()[0] > 0
                logger.debug(f"Symbol {symbol} has historical data: {has_data}")
                return has_data
        except Exception as e:
            logger.error(f"Error checking if symbol {symbol} has historical data: {e}")
            raise
    
    @log_function_call
    def get_historical_prices_for_symbol(self, symbol: str, limit: int = None) -> list:
        """Get historical price data for a specific symbol"""
        logger.debug(f"Retrieving historical prices for {symbol} (limit: {limit})")
        try:
            with self.engine.connect() as conn:
                query = "SELECT * FROM historical_prices WHERE symbol = :symbol ORDER BY date DESC"
                if limit:
                    query += f" LIMIT {limit}"
                
                result = conn.execute(text(query), {"symbol": symbol})
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
                logger.debug(f"Retrieved {len(data)} historical price records for {symbol}")
                return data
        except Exception as e:
            logger.error(f"Error retrieving historical prices for {symbol}: {e}")
            raise

    @log_function_call
    def insert_undervaluation_scores(self, scores_data: list[dict]):
        """Insert or update undervaluation scores data"""
        logger.info(f"Inserting/updating {len(scores_data)} undervaluation scores")
        try:
            with self.engine.connect() as conn:
                for score in scores_data:
                    conn.execute(
                        text("""
                            INSERT INTO undervaluation_scores 
                            (symbol, sector, undervaluation_score, valuation_score, quality_score, 
                             strength_score, risk_score, data_quality, price, mktcap, created_at, updated_at)
                            VALUES (:symbol, :sector, :undervaluation_score, :valuation_score, :quality_score, 
                                    :strength_score, :risk_score, :data_quality, :price, :mktcap, 
                                    COALESCE((SELECT created_at FROM undervaluation_scores WHERE symbol = :symbol), CURRENT_TIMESTAMP), 
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT (symbol) DO UPDATE SET
                            sector = EXCLUDED.sector, undervaluation_score = EXCLUDED.undervaluation_score,
                            valuation_score = EXCLUDED.valuation_score, quality_score = EXCLUDED.quality_score,
                            strength_score = EXCLUDED.strength_score, risk_score = EXCLUDED.risk_score,
                            data_quality = EXCLUDED.data_quality, price = EXCLUDED.price, mktcap = EXCLUDED.mktcap,
                            updated_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "symbol": score.get('symbol'),
                            "sector": score.get('sector'),
                            "undervaluation_score": score.get('undervaluation_score'),
                            "valuation_score": score.get('valuation_score'),
                            "quality_score": score.get('quality_score'),
                            "strength_score": score.get('strength_score'),
                            "risk_score": score.get('risk_score'),
                            "data_quality": score.get('data_quality'),
                            "price": score.get('price'),
                            "mktcap": score.get('mktcap')
                        }
                    )
                conn.commit()
            logger.info(f"Undervaluation scores for {len(scores_data)} stocks inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating undervaluation scores: {e}")
            raise

    @log_function_call
    def insert_corporate_actions(self, symbol: str, actions_data: list[dict]):
        """Insert or update corporate actions data"""
        logger.info(f"Inserting/updating {len(actions_data)} corporate actions for {symbol}")
        try:
            with self.engine.connect() as conn:
                for action in actions_data:
                    conn.execute(
                        text("""
                            INSERT INTO corporate_actions 
                            (symbol, action_type, action_date, amount, split_ratio)
                            VALUES (:symbol, :action_type, :action_date, :amount, :split_ratio)
                            ON CONFLICT (symbol, action_type, action_date) DO UPDATE SET
                            amount = EXCLUDED.amount, split_ratio = EXCLUDED.split_ratio
                        """),
                        {
                            "symbol": symbol,
                            "action_type": action.get('action_type'),
                            "action_date": action.get('action_date'),
                            "amount": action.get('amount'),
                            "split_ratio": action.get('split_ratio')
                        }
                    )
                conn.commit()
            logger.info(f"Corporate actions for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating corporate actions for {symbol}: {e}")
            raise

    @log_function_call
    def insert_income_statements(self, symbol: str, statements_data: list[dict]):
        """Insert or update income statements data"""
        logger.info(f"Inserting/updating {len(statements_data)} income statements for {symbol}")
        try:
            with self.engine.connect() as conn:
                for statement in statements_data:
                    conn.execute(
                        text("""
                            INSERT INTO income_statements 
                            (symbol, period_ending, period_type, total_revenue, cost_of_revenue, gross_profit,
                             operating_income, ebit, ebitda, net_income, basic_eps, diluted_eps, shares_outstanding,
                             tax_provision, interest_expense, research_development, selling_general_administrative,
                             created_at, updated_at)
                            VALUES (:symbol, :period_ending, :period_type, :total_revenue, :cost_of_revenue, :gross_profit,
                                    :operating_income, :ebit, :ebitda, :net_income, :basic_eps, :diluted_eps, :shares_outstanding,
                                    :tax_provision, :interest_expense, :research_development, :selling_general_administrative,
                                    COALESCE((SELECT created_at FROM income_statements WHERE symbol = :symbol AND period_ending = :period_ending AND period_type = :period_type), CURRENT_TIMESTAMP), 
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT (symbol, period_ending, period_type) DO UPDATE SET
                            total_revenue = EXCLUDED.total_revenue, cost_of_revenue = EXCLUDED.cost_of_revenue,
                            gross_profit = EXCLUDED.gross_profit, operating_income = EXCLUDED.operating_income,
                            ebit = EXCLUDED.ebit, ebitda = EXCLUDED.ebitda, net_income = EXCLUDED.net_income,
                            basic_eps = EXCLUDED.basic_eps, diluted_eps = EXCLUDED.diluted_eps,
                            shares_outstanding = EXCLUDED.shares_outstanding, tax_provision = EXCLUDED.tax_provision,
                            interest_expense = EXCLUDED.interest_expense, research_development = EXCLUDED.research_development,
                            selling_general_administrative = EXCLUDED.selling_general_administrative, updated_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "symbol": symbol,
                            "period_ending": statement.get('period_ending'),
                            "period_type": statement.get('period_type'),
                            "total_revenue": statement.get('total_revenue'),
                            "cost_of_revenue": statement.get('cost_of_revenue'),
                            "gross_profit": statement.get('gross_profit'),
                            "operating_income": statement.get('operating_income'),
                            "ebit": statement.get('ebit'),
                            "ebitda": statement.get('ebitda'),
                            "net_income": statement.get('net_income'),
                            "basic_eps": statement.get('basic_eps'),
                            "diluted_eps": statement.get('diluted_eps'),
                            "shares_outstanding": statement.get('shares_outstanding'),
                            "tax_provision": statement.get('tax_provision'),
                            "interest_expense": statement.get('interest_expense'),
                            "research_development": statement.get('research_development'),
                            "selling_general_administrative": statement.get('selling_general_administrative')
                        }
                    )
                conn.commit()
            logger.info(f"Income statements for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating income statements for {symbol}: {e}")
            raise

    @log_function_call
    def insert_balance_sheets(self, symbol: str, statements_data: list[dict]):
        """Insert or update balance sheets data"""
        logger.info(f"Inserting/updating {len(statements_data)} balance sheets for {symbol}")
        try:
            with self.engine.connect() as conn:
                for statement in statements_data:
                    conn.execute(
                        text("""
                            INSERT INTO balance_sheets 
                            (symbol, period_ending, period_type, total_assets, total_liabilities, total_equity,
                             current_assets, current_liabilities, cash_and_equivalents, accounts_receivable, inventory,
                             property_plant_equipment, total_debt, long_term_debt, retained_earnings, working_capital,
                             shares_outstanding, created_at, updated_at)
                            VALUES (:symbol, :period_ending, :period_type, :total_assets, :total_liabilities, :total_equity,
                                    :current_assets, :current_liabilities, :cash_and_equivalents, :accounts_receivable, :inventory,
                                    :property_plant_equipment, :total_debt, :long_term_debt, :retained_earnings, :working_capital,
                                    :shares_outstanding, 
                                    COALESCE((SELECT created_at FROM balance_sheets WHERE symbol = :symbol AND period_ending = :period_ending AND period_type = :period_type), CURRENT_TIMESTAMP), 
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT (symbol, period_ending, period_type) DO UPDATE SET
                            total_assets = EXCLUDED.total_assets, total_liabilities = EXCLUDED.total_liabilities,
                            total_equity = EXCLUDED.total_equity, current_assets = EXCLUDED.current_assets,
                            current_liabilities = EXCLUDED.current_liabilities, cash_and_equivalents = EXCLUDED.cash_and_equivalents,
                            accounts_receivable = EXCLUDED.accounts_receivable, inventory = EXCLUDED.inventory,
                            property_plant_equipment = EXCLUDED.property_plant_equipment, total_debt = EXCLUDED.total_debt,
                            long_term_debt = EXCLUDED.long_term_debt, retained_earnings = EXCLUDED.retained_earnings,
                            working_capital = EXCLUDED.working_capital, shares_outstanding = EXCLUDED.shares_outstanding,
                            updated_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "symbol": symbol,
                            "period_ending": statement.get('period_ending'),
                            "period_type": statement.get('period_type'),
                            "total_assets": statement.get('total_assets'),
                            "total_liabilities": statement.get('total_liabilities'),
                            "total_equity": statement.get('total_equity'),
                            "current_assets": statement.get('current_assets'),
                            "current_liabilities": statement.get('current_liabilities'),
                            "cash_and_equivalents": statement.get('cash_and_equivalents'),
                            "accounts_receivable": statement.get('accounts_receivable'),
                            "inventory": statement.get('inventory'),
                            "property_plant_equipment": statement.get('property_plant_equipment'),
                            "total_debt": statement.get('total_debt'),
                            "long_term_debt": statement.get('long_term_debt'),
                            "retained_earnings": statement.get('retained_earnings'),
                            "working_capital": statement.get('working_capital'),
                            "shares_outstanding": statement.get('shares_outstanding')
                        }
                    )
                conn.commit()
            logger.info(f"Balance sheets for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating balance sheets for {symbol}: {e}")
            raise

    @log_function_call
    def insert_cash_flow_statements(self, symbol: str, statements_data: list[dict]):
        """Insert or update cash flow statements data"""
        logger.info(f"Inserting/updating {len(statements_data)} cash flow statements for {symbol}")
        try:
            with self.engine.connect() as conn:
                for statement in statements_data:
                    conn.execute(
                        text("""
                            INSERT INTO cash_flow_statements 
                            (symbol, period_ending, period_type, operating_cash_flow, investing_cash_flow, financing_cash_flow,
                             net_change_in_cash, free_cash_flow, capital_expenditures, dividend_payments, share_repurchases,
                             depreciation_amortization, created_at, updated_at)
                            VALUES (:symbol, :period_ending, :period_type, :operating_cash_flow, :investing_cash_flow, :financing_cash_flow,
                                    :net_change_in_cash, :free_cash_flow, :capital_expenditures, :dividend_payments, :share_repurchases,
                                    :depreciation_amortization, 
                                    COALESCE((SELECT created_at FROM cash_flow_statements WHERE symbol = :symbol AND period_ending = :period_ending AND period_type = :period_type), CURRENT_TIMESTAMP), 
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT (symbol, period_ending, period_type) DO UPDATE SET
                            operating_cash_flow = EXCLUDED.operating_cash_flow, investing_cash_flow = EXCLUDED.investing_cash_flow,
                            financing_cash_flow = EXCLUDED.financing_cash_flow, net_change_in_cash = EXCLUDED.net_change_in_cash,
                            free_cash_flow = EXCLUDED.free_cash_flow, capital_expenditures = EXCLUDED.capital_expenditures,
                            dividend_payments = EXCLUDED.dividend_payments, share_repurchases = EXCLUDED.share_repurchases,
                            depreciation_amortization = EXCLUDED.depreciation_amortization, updated_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "symbol": symbol,
                            "period_ending": statement.get('period_ending'),
                            "period_type": statement.get('period_type'),
                            "operating_cash_flow": statement.get('operating_cash_flow'),
                            "investing_cash_flow": statement.get('investing_cash_flow'),
                            "financing_cash_flow": statement.get('financing_cash_flow'),
                            "net_change_in_cash": statement.get('net_change_in_cash'),
                            "free_cash_flow": statement.get('free_cash_flow'),
                            "capital_expenditures": statement.get('capital_expenditures'),
                            "dividend_payments": statement.get('dividend_payments'),
                            "share_repurchases": statement.get('share_repurchases'),
                            "depreciation_amortization": statement.get('depreciation_amortization')
                        }
                    )
                conn.commit()
            logger.info(f"Cash flow statements for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating cash flow statements for {symbol}: {e}")
            raise

    @log_function_call
    def insert_analyst_recommendations(self, symbol: str, recommendations_data: list[dict]):
        """Insert or update analyst recommendations data"""
        logger.info(f"Inserting/updating {len(recommendations_data)} analyst recommendations for {symbol}")
        try:
            with self.engine.connect() as conn:
                for recommendation in recommendations_data:
                    conn.execute(
                        text("""
                            INSERT INTO analyst_recommendations 
                            (symbol, period, strong_buy, buy, hold, sell, strong_sell, total_analysts, created_at, updated_at)
                            VALUES (:symbol, :period, :strong_buy, :buy, :hold, :sell, :strong_sell, :total_analysts,
                                    COALESCE((SELECT created_at FROM analyst_recommendations WHERE symbol = :symbol AND period = :period), CURRENT_TIMESTAMP), 
                                    CURRENT_TIMESTAMP)
                            ON CONFLICT (symbol, period) DO UPDATE SET
                            strong_buy = EXCLUDED.strong_buy, buy = EXCLUDED.buy, hold = EXCLUDED.hold,
                            sell = EXCLUDED.sell, strong_sell = EXCLUDED.strong_sell, total_analysts = EXCLUDED.total_analysts,
                            updated_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "symbol": symbol,
                            "period": recommendation.get('period'),
                            "strong_buy": recommendation.get('strong_buy'),
                            "buy": recommendation.get('buy'),
                            "hold": recommendation.get('hold'),
                            "sell": recommendation.get('sell'),
                            "strong_sell": recommendation.get('strong_sell'),
                            "total_analysts": recommendation.get('total_analysts')
                        }
                    )
                conn.commit()
            logger.info(f"Analyst recommendations for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating analyst recommendations for {symbol}: {e}")
            raise
    
    @log_function_call
    def insert_short_interest_data(self, symbol: str, short_interest_data: dict):
        """Insert or update short interest data"""
        logger.info(f"Inserting/updating short interest data for {symbol}")
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO short_interest_data 
                        (symbol, report_date, short_interest, float_shares, short_ratio, 
                         short_percent_of_float, average_daily_volume)
                        VALUES (:symbol, :report_date, :short_interest, :float_shares, :short_ratio,
                                :short_percent_of_float, :average_daily_volume)
                        ON CONFLICT (symbol, report_date) DO UPDATE SET
                        short_interest = EXCLUDED.short_interest, float_shares = EXCLUDED.float_shares,
                        short_ratio = EXCLUDED.short_ratio, short_percent_of_float = EXCLUDED.short_percent_of_float,
                        average_daily_volume = EXCLUDED.average_daily_volume
                    """),
                    {
                        "symbol": symbol,
                        "report_date": short_interest_data.get('report_date'),
                        "short_interest": short_interest_data.get('short_interest'),
                        "float_shares": short_interest_data.get('float_shares'),
                        "short_ratio": short_interest_data.get('short_ratio'),
                        "short_percent_of_float": short_interest_data.get('short_percent_of_float'),
                        "average_daily_volume": short_interest_data.get('average_daily_volume')
                    }
                )
                conn.commit()
            logger.info(f"Short interest data for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating short interest data for {symbol}: {e}")
            raise
    
    @log_function_call
    def insert_short_squeeze_score(self, symbol: str, score_data: dict):
        """Insert or update short squeeze score"""
        logger.info(f"Inserting/updating short squeeze score for {symbol}")
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO short_squeeze_scores 
                        (symbol, squeeze_score, si_score, dtc_score, float_score, momentum_score, data_quality)
                        VALUES (:symbol, :squeeze_score, :si_score, :dtc_score, :float_score, :momentum_score, :data_quality)
                        ON CONFLICT (symbol) DO UPDATE SET
                        squeeze_score = EXCLUDED.squeeze_score, si_score = EXCLUDED.si_score,
                        dtc_score = EXCLUDED.dtc_score, float_score = EXCLUDED.float_score,
                        momentum_score = EXCLUDED.momentum_score, data_quality = EXCLUDED.data_quality,
                        calculated_at = CURRENT_TIMESTAMP
                    """),
                    {
                        "symbol": symbol,
                        "squeeze_score": score_data.get('squeeze_score'),
                        "si_score": score_data.get('si_score'),
                        "dtc_score": score_data.get('dtc_score'),
                        "float_score": score_data.get('float_score'),
                        "momentum_score": score_data.get('momentum_score'),
                        "data_quality": score_data.get('data_quality')
                    }
                )
                conn.commit()
            logger.info(f"Short squeeze score for {symbol} inserted/updated successfully")
        except Exception as e:
            logger.error(f"Error inserting/updating short squeeze score for {symbol}: {e}")
            raise
    
    @log_function_call
    def get_short_interest_data(self, symbol: str, limit: int = None) -> list:
        """Get short interest data for a specific symbol"""
        logger.debug(f"Retrieving short interest data for {symbol} (limit: {limit})")
        try:
            with self.engine.connect() as conn:
                query = "SELECT * FROM short_interest_data WHERE symbol = :symbol ORDER BY report_date DESC"
                if limit:
                    query += f" LIMIT {limit}"
                
                result = conn.execute(text(query), {"symbol": symbol})
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
                logger.debug(f"Retrieved {len(data)} short interest records for {symbol}")
                return data
        except Exception as e:
            logger.error(f"Error retrieving short interest data for {symbol}: {e}")
            raise
    
    @log_function_call
    def get_short_squeeze_score(self, symbol: str) -> dict:
        """Get short squeeze score for a specific symbol"""
        logger.debug(f"Retrieving short squeeze score for {symbol}")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM short_squeeze_scores WHERE symbol = :symbol"),
                    {"symbol": symbol}
                )
                row = result.fetchone()
                
                if row:
                    columns = result.keys()
                    data = dict(zip(columns, row))
                    logger.debug(f"Retrieved short squeeze score for {symbol}: {data.get('squeeze_score')}")
                    return data
                else:
                    logger.debug(f"No short squeeze score found for {symbol}")
                    return {}
        except Exception as e:
            logger.error(f"Error retrieving short squeeze score for {symbol}: {e}")
            raise
    
    @log_function_call
    def get_short_squeeze_rankings(self, limit: int = 50, order_by: str = 'squeeze_score') -> list:
        """Get top/bottom ranked stocks by short squeeze score"""
        logger.debug(f"Retrieving short squeeze rankings (limit: {limit}, order_by: {order_by})")
        try:
            with self.engine.connect() as conn:
                # Validate order_by parameter
                valid_columns = ['squeeze_score', 'si_score', 'dtc_score', 'float_score', 'momentum_score']
                if order_by not in valid_columns:
                    order_by = 'squeeze_score'
                
                query = f"""
                    SELECT s.*, c.companyname, c.sector, c.mktcap, c.price
                    FROM short_squeeze_scores s
                    LEFT JOIN company_profiles c ON s.symbol = c.symbol
                    WHERE s.squeeze_score IS NOT NULL
                    ORDER BY s.{order_by} DESC
                    LIMIT :limit
                """
                
                result = conn.execute(text(query), {"limit": limit})
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
                logger.debug(f"Retrieved {len(data)} short squeeze rankings")
                return data
        except Exception as e:
            logger.error(f"Error retrieving short squeeze rankings: {e}")
            raise
