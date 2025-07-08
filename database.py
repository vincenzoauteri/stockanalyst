import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from logging_config import get_logger, log_function_call

load_dotenv()
logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self):
        # Check if we're using PostgreSQL (containerized) or SQLite (legacy)
        postgres_host = os.getenv('POSTGRES_HOST')
        if postgres_host:
            # PostgreSQL configuration
            postgres_port = os.getenv('POSTGRES_PORT', '5432')
            postgres_db = os.getenv('POSTGRES_DB', 'stockanalyst')
            postgres_user = os.getenv('POSTGRES_USER', 'stockanalyst')
            postgres_password = os.getenv('POSTGRES_PASSWORD', 'defaultpassword')
            
            self.db_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
            logger.info(f"Initializing DatabaseManager with PostgreSQL: {postgres_host}:{postgres_port}/{postgres_db}")
        else:
            # SQLite configuration (legacy/fallback)
            self.db_path = os.getenv('DATABASE_PATH', 'stock_analysis.db')
            self.db_url = f'sqlite:///{self.db_path}'
            logger.info(f"Initializing DatabaseManager with SQLite: {self.db_path}")
        
        self.engine = create_engine(self.db_url)
        self.create_tables()
        logger.info("DatabaseManager initialized successfully")
    
    @log_function_call
    def create_tables(self):
        """Create the necessary tables for stock analysis"""
        logger.debug("Creating database tables...")
        try:
            with self.engine.connect() as conn:
                # S&P 500 constituents table
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
                
                # Company profiles table
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
            
            logger.debug("Database tables created successfully")
            
            # Create performance indexes in a separate connection to avoid connection issues
            self.create_indexes_safe()
            
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
    
    @log_function_call
    def create_indexes_safe(self):
        """Create performance indexes with a separate connection to avoid connection issues"""
        try:
            with self.engine.connect() as conn:
                self.create_indexes(conn)
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    @log_function_call
    def insert_sp500_constituents(self, df: pd.DataFrame):
        """Insert S&P 500 constituents data"""
        logger.info(f"Inserting {len(df)} S&P 500 constituents")
        try:
            df.to_sql('sp500_constituents', self.engine, if_exists='replace', index=False)
            logger.info("S&P 500 constituents inserted successfully")
        except Exception as e:
            logger.error(f"Error inserting S&P 500 constituents: {e}")
            raise
    
    @log_function_call
    def insert_company_profile(self, profile_data: dict):
        """Insert or update company profile data"""
        symbol = profile_data.get('symbol', 'unknown')
        logger.debug(f"Inserting/updating company profile for {symbol}")
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