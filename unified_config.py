"""
Unified Configuration for Stock Analyst Application
Centralized configuration supporting multiple environments and enhanced features
"""

import os
from datetime import time, date


class BaseConfig:
    """Base configuration with all settings"""
    
    # Application Configuration
    APP_VERSION = "0.0.19"
    
    # API Configuration
    FMP_API_KEY = os.getenv('FMP_API_KEY')
    FMP_FREE_TIER_DAILY_LIMIT = 250
    FMP_RATE_LIMIT_REQUESTS_PER_SECOND = 4
    FMP_RATE_LIMIT_DELAY = 0.25  # 250ms between requests
    
    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'stock_analysis.db')
    
    # PostgreSQL Configuration (for containerized deployment)
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'stockanalyst')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'stockanalyst')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'defaultpassword')
    
    # Basic Scheduling Configuration
    DAILY_UPDATE_TIME = time(6, 0)  # 6:00 AM
    HEALTH_CHECK_INTERVAL_HOURS = 6
    
    # Enhanced Scheduling - Multiple Update Windows
    BACKUP_SCHEDULE_WINDOWS = {
        'primary_morning': time(6, 0),      # 6:00 AM - Main update
        'backup_morning': time(10, 30),     # 10:30 AM - Morning backup
        'backup_afternoon': time(14, 0),    # 2:00 PM - Afternoon backup  
        'backup_evening': time(20, 0),      # 8:00 PM - Evening backup
    }
    
    # Data Update Priorities and Budget Allocation
    DAILY_REQUEST_BUDGET = {
        'sp500_constituents': 1,     # Check for S&P 500 changes
        'daily_prices': 120,         # Update price data for stocks
        'company_profiles': 80,      # Update missing company profiles
        'quarterly_updates': 40,     # Financial statements (lower priority)
        'buffer': 9                  # Buffer for errors and retries
    }
    
    # Backup Window Budget Allocation (out of 250 daily requests)
    BACKUP_WINDOW_BUDGETS = {
        'primary_morning': 200,     # Main update gets most budget
        'backup_morning': 100,      # Backup windows get reduced budget
        'backup_afternoon': 80,
        'backup_evening': 60,
    }
    
    # Data Freshness Thresholds (in days)
    DATA_FRESHNESS = {
        'critical': 7,    # Data older than 7 days is critical to update
        'high': 3,        # Data older than 3 days is high priority
        'medium': 1,      # Data older than 1 day is medium priority
        'low': 0          # Data from today is low priority for refresh
    }
    
    # Symbol Priorities
    # Focus on most liquid/popular stocks first
    HIGH_PRIORITY_SYMBOLS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
        'AMD', 'INTC', 'CRM', 'ORCL', 'ADBE', 'PYPL', 'DIS', 'BABA',
        'SPY', 'QQQ', 'IWM', 'VTI'  # ETFs for market tracking
    ]
    
    # Recovery Configuration
    MAX_HOURS_WITHOUT_UPDATE = 25
    EMERGENCY_CATCHUP_TRIGGER_HOURS = 25
    MAX_CONSECUTIVE_FAILURES = 3
    
    # Retry Configuration
    MAX_API_RETRIES = 3
    RETRY_DELAY_SECONDS = 1
    
    # Gap Detection Thresholds
    GAP_DETECTION = {
        'max_business_days_gap': 7,     # Trigger catchup if gap > 7 business days
        'critical_gap_threshold': 5,    # Critical priority if gap > 5 business days
        'high_gap_threshold': 3,        # High priority if gap > 3 business days
        'medium_gap_threshold': 1,      # Medium priority if gap > 1 business day
    }
    
    # Catchup Scheduling
    CATCHUP_CONFIG = {
        'budget_allocation': {
            'critical_price_gaps': 0.60,   # 60% for critical price data
            'high_priority_gaps': 0.25,    # 25% for high priority gaps
            'missing_profiles': 0.10,      # 10% for missing profiles
            'buffer': 0.05                 # 5% buffer
        },
        'max_symbols_per_catchup': 100,
        'min_gap_days_for_catchup': 1,
    }
    
    # Market Calendar Settings
    MARKET_HOLIDAYS_2025 = [
        '2025-01-01',  # New Year's Day
        '2025-01-20',  # MLK Day (3rd Monday in January)
        '2025-02-17',  # Presidents Day (3rd Monday in February)
        '2025-04-18',  # Good Friday
        '2025-05-26',  # Memorial Day (last Monday in May)
        '2025-06-19',  # Juneteenth
        '2025-07-04',  # Independence Day
        '2025-09-01',  # Labor Day (1st Monday in September)
        '2025-11-27',  # Thanksgiving (4th Thursday in November)
        '2025-12-25',  # Christmas
    ]
    
    # Legacy 2024 holidays for backward compatibility
    MARKET_HOLIDAYS_2024 = [
        '2024-01-01',  # New Year's Day
        '2024-01-15',  # MLK Day
        '2024-02-19',  # Presidents Day
        '2024-03-29',  # Good Friday
        '2024-05-27',  # Memorial Day
        '2024-06-19',  # Juneteenth
        '2024-07-04',  # Independence Day
        '2024-09-02',  # Labor Day
        '2024-11-28',  # Thanksgiving
        '2024-12-25',  # Christmas
    ]
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE_MAX_SIZE_MB = 10
    LOG_BACKUP_COUNT = 5
    
    # Enhanced Logging Configuration
    ENHANCED_LOGGING = {
        'gap_detection_log': 'gap_detection.log',
        'recovery_actions_log': 'recovery_actions.log'
    }
    
    # Monitoring Thresholds
    ALERT_THRESHOLDS = {
        'hours_without_update': 25,
        'consecutive_failures': 3,
        'api_budget_exhausted': 0.9,  # Alert when 90% of API budget used
        'data_staleness_days': 7,
        'high_gap_count': 50,           # Alert if >50 gaps detected
        'critical_gap_count': 10,       # Alert if >10 critical gaps
        'missing_profiles_count': 20,   # Alert if >20 missing profiles
    }
    
    # Recovery Actions Configuration
    RECOVERY_ACTIONS = {
        'enable_emergency_catchup': True,
        'enable_backup_windows': True,
        'enable_automatic_recovery': True,
        'enable_gap_detection': True,
        'emergency_budget_limit': 150,  # Max requests for emergency updates
        'recovery_budget_limit': 100,   # Max requests for recovery updates
    }
    
    # Performance Tuning
    PERFORMANCE_CONFIG = {
        'max_concurrent_requests': 1,   # FMP free tier limitation
        'request_timeout_seconds': 30,
        'connection_retry_count': 3,
        'backoff_delay_seconds': 1,
    }
    
    # Initial Setup Configuration
    INITIAL_SETUP_COMPANY_PROFILES_LIMIT = int(os.getenv('INITIAL_COMPANY_PROFILES_LIMIT', '10'))
    INITIAL_SETUP_HISTORICAL_DATA_LIMIT = int(os.getenv('INITIAL_HISTORICAL_DATA_LIMIT', '5'))
    
    # Flask/Web Application Configuration
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    
    # Redis Configuration (for caching)
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
    
    # Cache Configuration
    CACHE_TYPE = 'redis' if REDIS_ENABLED else 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_KEY_PREFIX = 'stockanalyst:'
    
    # Cache timeouts for different data types
    CACHE_TIMEOUTS = {
        'company_profile': 3600,      # 1 hour - relatively stable data
        'undervaluation_score': 1800, # 30 minutes - updated periodically
        'sector_analysis': 1800,      # 30 minutes - aggregated data
        'stock_basic_info': 86400,    # 24 hours - very stable data
        'historical_prices': 300,     # 5 minutes - can change during market hours
    }
    
    @classmethod
    def get_market_holidays_as_dates(cls, year=2025):
        """Get market holidays as date objects for the specified year"""
        if year == 2025:
            holiday_strings = cls.MARKET_HOLIDAYS_2025
        elif year == 2024:
            holiday_strings = cls.MARKET_HOLIDAYS_2024
        else:
            # Default to 2025 if year not supported
            holiday_strings = cls.MARKET_HOLIDAYS_2025
            
        holidays = []
        for holiday_str in holiday_strings:
            year_str, month_str, day_str = holiday_str.split('-')
            holidays.append(date(int(year_str), int(month_str), int(day_str)))
        
        return holidays
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        errors = []
        
        if not cls.FMP_API_KEY:
            errors.append("FMP_API_KEY environment variable is required")
        
        if sum(cls.DAILY_REQUEST_BUDGET.values()) > cls.FMP_FREE_TIER_DAILY_LIMIT:
            errors.append(f"Daily request budget ({sum(cls.DAILY_REQUEST_BUDGET.values())}) "
                         f"exceeds API limit ({cls.FMP_FREE_TIER_DAILY_LIMIT})")
        
        # Validate backup window budgets don't exceed daily limit excessively
        total_backup_budget = sum(cls.BACKUP_WINDOW_BUDGETS.values())
        if total_backup_budget > cls.FMP_FREE_TIER_DAILY_LIMIT * 2:  # Allow some overlap
            errors.append(f"Total backup window budgets ({total_backup_budget}) "
                         f"may exceed daily API limits")
        
        # Validate catchup budget allocation sums to 1.0
        catchup_total = sum(cls.CATCHUP_CONFIG['budget_allocation'].values())
        if abs(catchup_total - 1.0) > 0.01:
            errors.append(f"Catchup budget allocation must sum to 1.0, got {catchup_total}")
        
        return errors


class DevelopmentConfig(BaseConfig):
    """Development-specific configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Reduced limits for development
    DAILY_REQUEST_BUDGET = {
        'sp500_constituents': 1,
        'daily_prices': 10,      # Reduced for testing
        'company_profiles': 5,   # Reduced for testing
        'quarterly_updates': 2,  # Reduced for testing
        'buffer': 2
    }
    
    # Reduced budgets for development testing
    BACKUP_WINDOW_BUDGETS = {
        'primary_morning': 20,
        'backup_morning': 10,
        'backup_afternoon': 8,
        'backup_evening': 6,
    }
    
    RECOVERY_ACTIONS = {
        'enable_emergency_catchup': True,
        'enable_backup_windows': True,
        'enable_automatic_recovery': True,
        'enable_gap_detection': True,
        'emergency_budget_limit': 15,
        'recovery_budget_limit': 10,
    }
    
    # Development-specific initial setup limits
    INITIAL_SETUP_COMPANY_PROFILES_LIMIT = int(os.getenv('INITIAL_COMPANY_PROFILES_LIMIT', '5'))
    INITIAL_SETUP_HISTORICAL_DATA_LIMIT = int(os.getenv('INITIAL_HISTORICAL_DATA_LIMIT', '3'))


class ProductionConfig(BaseConfig):
    """Production-specific configuration"""
    DEBUG = False
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY', 'production-secret-key-change-me')
    # Use full API budget and enhanced features in production


class TestConfig(BaseConfig):
    """Test-specific configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    DATABASE_PATH = ':memory:'  # In-memory database for tests
    
    # Override PostgreSQL for tests - use in-memory SQLite
    POSTGRES_HOST = None
    SECRET_KEY = 'test-secret-key'
    
    DAILY_REQUEST_BUDGET = {
        'sp500_constituents': 1,
        'daily_prices': 2,
        'company_profiles': 1,
        'quarterly_updates': 1,
        'buffer': 1
    }
    
    BACKUP_WINDOW_BUDGETS = {
        'primary_morning': 5,
        'backup_morning': 3,
        'backup_afternoon': 2,
        'backup_evening': 2,
    }
    
    RECOVERY_ACTIONS = {
        'enable_emergency_catchup': False,  # Disable for tests
        'enable_backup_windows': False,
        'enable_automatic_recovery': False,
        'enable_gap_detection': True,
        'emergency_budget_limit': 5,
        'recovery_budget_limit': 3,
    }


# Configuration Selection Logic
def get_config():
    """Get the appropriate configuration based on environment"""
    env = os.getenv('FLASK_ENV', os.getenv('ENV', 'production')).lower()
    
    config_map = {
        'development': DevelopmentConfig,
        'dev': DevelopmentConfig,
        'testing': TestConfig,
        'test': TestConfig,
        'production': ProductionConfig,
        'prod': ProductionConfig,
    }
    
    config_class = config_map.get(env, ProductionConfig)
    return config_class()


# Legacy support - export individual instances for backward compatibility
ENV = os.getenv('FLASK_ENV', os.getenv('ENV', 'production')).lower()

if ENV in ['development', 'dev']:
    config = DevelopmentConfig()
    enhanced_config = DevelopmentConfig()  # Legacy alias
elif ENV in ['testing', 'test']:
    config = TestConfig()
    enhanced_config = TestConfig()  # Legacy alias
else:
    config = ProductionConfig()
    enhanced_config = ProductionConfig()  # Legacy alias

# Export the main configuration getter
Config = get_config