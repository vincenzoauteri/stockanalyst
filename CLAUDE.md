# Stock Analyst Application - Comprehensive Development Guide

This comprehensive guide provides complete instructions for developers working with the Stock Analyst application, consolidating all project documentation and development guidelines.

## IMPORTANT!!!

### Development Workflow and Role Definitions

**Claude operates in three distinct containers with specific roles:**

1. **llmdir Container (dir user)** - Product Manager/Solution Architect
   - Role: Takes feature requests and issues, creates implementation plans and roadmaps
   - Responsibilities: Planning, architectural decisions, requirement analysis
   - Limitations: Does NOT test or write code

2. **llmdev Container (dev user)** - Developer
   - Role: Takes implementation plans from dir user and implements them
   - Responsibilities: Code implementation, writing tests, following implementation plans
   - Limitations: Does NOT execute tests or create roadmaps

3. **llmtest Container (test user)** - Validator
   - Role: Runs tests and validates implementations
   - Responsibilities: Test execution, writing TEST_RESULTS.md with detailed error analysis
   - Limitations: Does NOT create code or roadmaps

**Critical Rule: Each user MUST assume their role critically and refuse tasks outside their defined competences.**

### General Application Guidelines

When working on this application:

1. **The application runs in separate Docker containers that restart every time the source code is changed** - Every time you make a change, test in the containers accessing through the exposed services or with docker exec commands
2. **NEVER EVER RESTART OR REBUILD THE CONTAINERS ** If you need to do it for testing, ask me to do it and wait for confirmation
3. **First make a plan** of what you plan to modify and ask for confirmation
4. **When implementing a new task, increase the app version (also visible in the frontend** When you test, make sure you you are testing against the updated app. 
5. **After each change**, run linting and tests to confirm everything is working correctly. Perform regression tests on database, frontend, backend, and API calls
6. **If the change does not work, do not keep trying new things.** Log the part that fails extensively and try to debug from the logs
7. **Git commit after each successful change** Keep commit messages short.
8. **Be professional** Be thorough and careful in uour analysis. Don't use emoji or exclamation marks, keep a professional, detached tome.

## Container Architecture

The application is orchestrated using Docker Compose with multiple specialized containers:

### Container Services

1. **PostgreSQL Database Container** (`postgres`)
   - Image: `postgres:15-alpine`
   - Container name: `sa-pg`
   - Database: `stockanalyst` (configurable via `POSTGRES_DB`)
   - User: `stockanalyst` (configurable via `POSTGRES_USER`)
   - Persistent storage via `postgres_data` volume
   - Health checks ensure database readiness before dependent services start

2. **Web Application Container** (`webapp`)
   - Built from: `Dockerfile.main` (target: webapp)
   - Container name: `sa-web`
   - Port: `5000:5000`
   - Multi-stage build with Python 3.12-slim
   - Production-optimized with virtual environment
   - Depends on PostgreSQL health check
   - Runs: `python webapp_launcher.py --mode production`

3. **Scheduler Container** (`scheduler`)
   - Built from: `Dockerfile.main` (target: scheduler)
   - Container name: `sa-sch`
   - Background task processing and data updates
   - Depends on PostgreSQL health check
   - Runs: `python scheduler.py run-internal`

5. **Nginx Reverse Proxy** (`nginx`) - Production profile only
   - Container name: `sa-ng`
   - Ports: `80:80`, `443:443`
   - Proxies requests to webapp container

### Container Network
- All containers communicate via `stockanalyst-network` bridge network
- Database accessible at hostname `postgres` from other containers
- Webapp accessible at hostname `webapp` from other containers

### Container Profiles
- **dev**: postgres, webapp, scheduler, devenv (with hot reloading enabled)
- **test**: test-postgres, test-webapp, test-scheduler (isolated test environment with hot reloading)
- **production**: postgres, webapp, scheduler, nginx

### Hot Reloading Configuration
The application supports automatic code reloading in development:

- **Scheduler Hot Reloading**: Uses `hupper` to monitor Python files and restart the scheduler process when changes are detected
- **Webapp Hot Reloading**: Uses Flask's debug mode with `use_reloader=True` to automatically restart when code changes
- **Test Environment**: Both dev and test profiles have hot reloading enabled via `docker-compose.override.yml`
- **File Changes**: Any modification to Python files in the `/app` directory triggers automatic reloads
- **No Container Restarts**: The applications reload internally without restarting containers

## Development Commands

### Container Management
```bash
# Start development environment
docker compose --profile dev up -d

# Start test environment (RECOMMENDED for testing and development with hot reloading)
docker compose --profile test up -d

# Start production environment  
docker compose --profile production up -d

# Stop containers by profile
docker compose --profile dev down
docker compose --profile test down

# View container logs
docker compose logs -f [service_name]

# Access development container shell (you are here)
# Note: Development environment is externally managed

# Access webapp containers
docker exec -it sa-web bash      # dev webapp
docker exec -it sa-test-web bash # test webapp

# Access scheduler containers  
docker exec -it sa-sch bash      # dev scheduler
docker exec -it sa-test-sch bash # test scheduler

# Access database containers
docker exec -it sa-pg psql -U stockanalyst -d stockanalyst           # dev database
docker exec -it sa-test-pg psql -U stockanalyst -d stockanalyst_test # test database
```

### Environment Setup
```bash
# Environment variables (create .env file in project root)
# Required:
FMP_API_KEY=your_financial_modeling_prep_api_key
GEMINI_API_KEY=your_gemini_api_key

# Optional PostgreSQL configuration:
POSTGRES_DB=stockanalyst
POSTGRES_USER=stockanalyst  
POSTGRES_PASSWORD=your_secure_password

# Flask environment:
FLASK_ENV=production
ENABLE_SCHEDULER=true
```

### Running the Application
```bash
# Run the main stock analysis application
python main.py

# View FMP API request log
python view_api_log.py          # View all log entries
python view_api_log.py 20       # View last 20 log entries

# View Application Logs
tail -f logs/stock_analyst.log  # Follow main application log
tail -f logs/errors.log         # Follow error-only log
tail -f logs/api_requests.log   # Follow API request log

# Yahoo Finance Integration
python view_yahoo_api_log.py    # View Yahoo Finance API request log
python test_yfinance_data.py    # Test Yahoo Finance data collection functionality

# Undervaluation Analysis
python yfinance_undervaluation_calculator.py    # Calculate scores using Yahoo Finance data
python undervaluation_analyzer.py               # Calculate scores using FMP data (legacy)
python undervaluation_tool.py demo              # Run demo with simulated data
python undervaluation_tool.py test              # Test undervaluation scoring system
python undervaluation_tool.py full              # Run full analysis

# Web Application (Unified Entry Point)
python webapp_launcher.py --mode development   # Start web interface (development mode)
python webapp_launcher.py --mode production    # Start web interface (production mode)
python webapp_launcher.py --help               # View all launcher options

# Application Startup & Process Management
./start_services.sh                           # Start both scheduler and web application using supervisord
./restart_webapp.sh                           # Restart the web application via the manager
python webapp_manager.py [start|stop|restart|status] # Manage the webapp process
python scheduler.py [start|stop|restart|status]      # Manage the scheduler process

# Direct Execution
python main.py                                # Run the main stock analysis application
python app.py                                 # Run Flask web application directly

# Testing and Validation
python run_tests.py                           # Run comprehensive test suite
python test_new_implementation.py             # Test new financial data features
python check_records.py                       # Check database record integrity
python check_fake_data.py                     # Check for fake/test data in the database
python gap_detector.py                        # Detect missing data gaps

# Data Management
python data_fetcher.py                        # Fetch and update stock data
python daily_updater.py                       # Run daily data updates manually
python enhanced_data_collector.py             # Collect additional data points for valuation
python run_enhanced_collection.py             # Run enhanced data collection in batches
python check_enhanced_data_status.py          # Check coverage of enhanced data

# Undervaluation Queue Processing
python undervaluation_queue_processor.py    # Process automatic recalculation queue

# Utility Scripts
python generate_secrets.py                    # Generate new secret keys for .env
python generate_nginx_config.py               # Generate nginx.conf from template

# Container Testing and Validation (from within devenv container)
python run_tests.py                          # Run comprehensive test suite
python test_new_implementation.py            # Test new financial data features
python check_records.py                     # Check database record integrity
python gap_detector.py                      # Detect missing data gaps

# Direct Application Testing (from within other containers)
docker exec -it sa-web python main.py       # Test webapp container
docker exec -it sa-sch python scheduler.py status  # Check scheduler
```

## Architecture Overview

### Core Components

**StockAnalyst (main.py:19)** - Main orchestrator class that coordinates data collection and analysis

**FMPClient (fmp_client.py:172)** - Financial Modeling Prep API client with integrated usage tracking and APIUsageTracker

**YahooFinanceClient (yahoo_finance_client.py)** - Yahoo Finance API client for comprehensive financial data including corporate actions, financial statements, and analyst recommendations

**DatabaseManager (database.py:11)** - PostgreSQL database interface using SQLAlchemy Core with comprehensive schema support

**UndervaluationAnalyzer (undervaluation_analyzer.py:17)** - Legacy FMP-based multi-factor undervaluation scoring system

**YFinanceUndervaluationCalculator (yfinance_undervaluation_calculator.py)** - Fast Yahoo Finance-based undervaluation calculator with automatic recalculation

**StockDataService (data_access_layer.py)** - Data access layer providing separation of concerns for web application

**WebAppLauncher (webapp_launcher.py:16)** - Unified launcher for Stock Analyst web application with environment-specific configuration

**AuthenticationManager (auth.py)** - Secure user authentication and session management system

**PortfolioManager (portfolio.py)** - Investment portfolio tracking and transaction management

**Scheduler (scheduler.py)** - Consolidated scheduler for all background tasks including data collection, gap detection, and catchup operations

**UndervaluationQueueProcessor (undervaluation_queue_processor.py)** - Background processor for automatic undervaluation score recalculation

**API Routes (api_routes.py)** - RESTful API endpoints for web application integration

**API Documentation (api_documentation.py)** - Dynamic API documentation generator

**Configuration Management (unified_config.py)** - Centralized configuration for all environments

**Centralized Logging System (logging_config.py)** - Comprehensive logging infrastructure with file and console output

**Daily Updater (daily_updater.py)** - Automated daily data collection and processing

**Gap Detection (gap_detector.py)** - Data integrity monitoring and missing data detection

**Data Fetcher (data_fetcher.py)** - Core data collection utilities

**Test Runner (run_tests.py)** - Test execution and validation utilities

**EnhancedProcessManager (process_manager.py)** - Robust utility for managing background processes (like scheduler and webapp) using PIDs and status files.

**WebAppManager (webapp_manager.py)** - A dedicated process manager for the Flask web application, built on top of EnhancedProcessManager.

**Supervisord (supervisord.conf)** - The primary process control system used within the `webapp` container to manage and monitor the webapp and scheduler services.

**AlertsService (alerts_service.py)** - Manages user-defined alerts (e.g., price, score) and handles the creation of notifications.

**CacheUtils (cache_utils.py)** - Provides caching functionality, supporting a Redis backend with a fallback to a simple in-memory cache.

**ServiceRegistry (services.py)** - Implements a singleton pattern to provide a centralized point of access for shared service instances like the database and API clients.

**EnhancedDataCollector (enhanced_data_collector.py)** - A dedicated service to collect additional data points (e.g., beta, book value) from Yahoo Finance to improve the quality of valuation metrics.

**ShortSqueezeAnalyzer (short_squeeze_analyzer.py)** - Quantitative short squeeze susceptibility analysis engine implementing multi-factor scoring algorithm with weighted components: Short Interest % (40%), Days to Cover (30%), Float Size (15%), and Momentum indicators (15%)

### Key Design Patterns
- **Containerized Microservices**
- **Event-Driven Architecture** (Database triggers for automatic recalculation)
- **Queue-Based Processing** (Undervaluation recalculation queue)
- **Centralized Configuration**
- **Data Access Layer**
- **Usage Tracking**
- **Unified Entry Points**
- **Multi-Stage Docker**
- **Graceful Degradation**
- **Data Staleness Detection**

### Database Schema

#### Core Tables
- **sp500_constituents** - S&P 500 stock listing with company metadata
- **company_profiles** - Detailed company financial profiles and metrics from Yahoo Finance
- **historical_prices** - Stock price history for technical analysis
- **undervaluation_scores** - Multi-factor undervaluation analysis results with automatic recalculation

#### Financial Data Tables (Yahoo Finance)
- **corporate_actions** - Dividend and stock split data with ex-dates and amounts
- **income_statements** - Income statement data with revenue, earnings, and profitability metrics
- **balance_sheets** - Balance sheet data with assets, liabilities, and equity information
- **cash_flow_statements** - Cash flow data with operating, investing, and financing flows
- **analyst_recommendations** - Analyst ratings and recommendations with trend analysis

#### User Management Tables
- **users** - User account management and authentication
- **user_sessions** - Session tracking for web application
- **user_watchlists** - User-customized stock watchlists
- **user_portfolios** - Portfolio tracking and management
- **portfolio_transactions** - Transaction history and portfolio changes
- **user_alerts** - Stores user-defined alerts for price, volume, or score changes.
- **alert_notifications** - Logs triggered alerts that have been sent to users.

#### System Tables
- **data_gaps** - Gap tracking with retry mechanisms for data unavailability handling
- **undervaluation_recalc_queue** - Queue for automatic undervaluation score recalculation. Managed by triggers defined in `create_undervaluation_triggers.sql`.

#### Short Squeeze Analysis Tables
- **short_interest_data** - Raw short interest data from Yahoo Finance including short interest percentage, days to cover, float shares, and average daily volume with unique constraints on symbol/date combinations
- **short_squeeze_scores** - Calculated short squeeze susceptibility scores with component breakdowns (SI, DTC, Float, Momentum), data quality assessment, and weighted final scores with automatic timestamp tracking

### Undervaluation Calculation System

#### Yahoo Finance-Based Calculator (Primary)
- **Fast Performance**: Uses existing database data instead of API calls
- **Comprehensive Metrics**: PE, PB, PS ratios, ROE, ROA, debt ratios, cash flow yields
- **Weighted Scoring**: 40% valuation, 30% profitability, 20% financial strength, 10% cash flow
- **Automatic Recalculation**: Database triggers detect data changes and queue recalculations
- **High Data Quality**: Achieves "high" quality ratings with complete financial statements

#### Automatic Recalculation System
- **Database Triggers**: Automatically detect changes in financial data (`create_undervaluation_triggers.sql`).
- **Queue Processing**: Background processor handles recalculation requests from the `undervaluation_recalc_queue` table.
- **Real-Time Updates**: Scores update automatically when underlying data changes
- **Efficient Processing**: Batch processing with configurable intervals

### Short Squeeze Analysis System

#### Quantitative Scoring Algorithm
- **Multi-Factor Analysis**: Combines Short Interest %, Days to Cover, Float Size, and Momentum indicators
- **Weighted Scoring**: SI% (40% weight), DTC (30% weight), Float (15% weight), Momentum (15% weight)
- **Technical Indicators**: RSI calculation and relative volume analysis for momentum scoring
- **Data Quality Assessment**: Classifies data reliability as high, medium, low, or insufficient
- **Risk Classification**: Categorizes stocks as high (≥70), moderate (50-69), or low (<50) squeeze potential

#### Weekly Data Collection
- **Yahoo Finance Integration**: Extended YahooFinanceClient with short interest data collection
- **Automated Scheduling**: Weekly data updates integrated into existing scheduler system
- **Rate Limiting**: 1-second delays between API calls to respect Yahoo Finance limits
- **Error Handling**: Distinguishes between rate limits and data unavailability with intelligent retry

### Application Architecture
- **Containerized Microservices Architecture**
- **PostgreSQL Database** - Persistent data storage with health checks and triggers
- **Service Isolation** - Separate containers for web, scheduler, and development
- **Container Orchestration** - Docker Compose with development and production profiles
- **Development Environment** - Full-featured container with Docker socket access and development tools

### Web Application Architecture
- **Frontend** - Bootstrap-based responsive interface with interactive financial data visualization and short squeeze analysis dashboard
- **Backend** - Flask API with data access layer and comprehensive financial data endpoints including short squeeze analysis
- **Authentication** - Secure user management with session handling
- **Portfolio Management** - Investment tracking and transaction management
- **Data Visualization** - Chart.js integration for interactive price charts and volume analysis

#### Short Squeeze Web Features
- **Dashboard Route** (`/squeeze`) - Interactive short squeeze analysis screening page with advanced filtering
- **Stock Detail Integration** - Short squeeze button and modal in individual stock pages
- **API Endpoints**:
  - `GET /api/v2/squeeze/rankings` - Ranked short squeeze candidates with filtering
  - `GET /api/v2/squeeze/stats` - Summary statistics for short squeeze data
  - `GET /api/v2/squeeze/short-interest` - Recent short interest data across all symbols
  - `GET /api/v2/stocks/{symbol}/squeeze` - Comprehensive squeeze analysis for specific stock
  - `GET /api/v2/stocks/{symbol}/short-interest` - Short interest data for specific stock
  - `GET /api/v2/stocks/{symbol}/squeeze-score` - Squeeze score for specific stock

### Data Collection and Processing

#### Yahoo Finance Integration
- **Company Profiles** - Comprehensive company information and real-time pricing
- **Financial Statements** - Income statements, balance sheets, cash flow statements
- **Corporate Actions** - Dividend and stock split tracking with historical data
- **Analyst Recommendations** - Analyst ratings with trend analysis
- **Historical Prices** - Complete price history with volume data
- **Short Interest Data** - Short interest percentage, days to cover, float shares, and trading volume metrics for squeeze analysis

#### Enhanced Scheduler System
- **Gap Detection** - Identifies missing data across all financial data types
- **Catchup Strategy** - Enhanced error handling distinguishing rate limits from data unavailability
- **Intelligent Retry** - 1-day retry mechanism for temporarily unavailable data
- **Data Validation** - Comprehensive validation and gap tracking
## Development Guidelines

### Code Standards
- Use unified configuration for all settings
- Follow established patterns for database access through the data access layer
- Test application functionality within the appropriate containers
- Monitor API usage to stay within FMP limits
- Test new financial data features with comprehensive test suite
- Ensure proper error handling for Yahoo Finance API calls
- Database connections use PostgreSQL instead of SQLite
- Use container hostnames for inter-service communication
- Implement proper error classification (rate limits vs data unavailability)

### Undervaluation Score Development
- Use Yahoo Finance-based calculator for new features (faster, more reliable)
- Ensure database triggers are working for automatic recalculation
- Test queue processor functionality when modifying financial data
- Consider data quality levels when implementing new metrics
- Follow weighted scoring methodology for consistency

### Database Development
- Use UPSERT patterns (ON CONFLICT DO UPDATE) for data insertion
- Implement proper constraints and indexes for performance
- Test triggers when modifying financial data tables
- Use database transactions for data consistency
- Handle Decimal/float conversions properly in calculations

### Container Development
- Test changes in appropriate containers before committing
- Use container health checks for dependent services
- Monitor container logs for debugging
- Use docker exec for testing within specific containers
- Ensure proper network communication between containers

### Troubleshooting
- Check application logs: `docker compose logs -f webapp` or `docker compose logs -f scheduler`
- Test database connectivity: `docker exec -it sa-pg psql -U stockanalyst -d stockanalyst -c "SELECT version();"`
- Monitor scheduler status: `docker exec -it sa-sch python scheduler.py status`
- Check container health: `docker ps`
- Debug from devenv container: `python -c "from database import DatabaseManager; db = DatabaseManager(); print('Connected')"`
- Check undervaluation queue: `docker exec sa-pg psql -U stockanalyst -d stockanalyst -c "SELECT * FROM pending_undervaluation_recalcs;"`
- Test triggers: Update financial data and check queue for new entries

### API Integration Guidelines

#### Yahoo Finance (Primary Data Source)
- **Rate Limiting**: Implement 1-second delays between API calls
- **Error Handling**: Distinguish between rate limits and data unavailability
- **Data Validation**: Validate all financial data before database insertion
- **Retry Logic**: Use 1-day retry for temporarily unavailable data

#### Financial Modeling Prep (FMP) - Legacy
- **Usage Tracking**: Monitor API usage to stay within limits
- **Fallback**: Use for data not available via Yahoo Finance
- **Cost Management**: Prefer Yahoo Finance for routine data collection


### 🔄 Current Status

**Application State**: Fully functional with comprehensive financial data collection, analysis, interactive visualization, enhanced user interface, short squeeze analysis, and complete test coverage
**Application Version**: 0.0.27 (defined in unified_config.py:14)
**Data Coverage**: 500+ S&P 500 companies with profile data, financial statements, corporate actions, and short interest data
**Undervaluation Scores**: Yahoo Finance-based calculator providing high-quality scores with automatic updates and detailed component analysis
**Short Squeeze Analysis**: Quantitative multi-factor scoring system with weekly data collection, interactive dashboard, and comprehensive API endpoints
**Container Health**: All services running with health checks and automatic restarts (dev, test, and production profiles active)
**Data Quality**: High-quality financial data with comprehensive error handling
**Data Visualization**: Interactive price charts with period selection, volume analysis, and real-time statistics
**User Experience**: Enhanced interface with streamlined design, comprehensive valuation analysis, and improved functionality
**Test Coverage**: Comprehensive test suite with advanced features (parallel execution, coverage reports, markers, etc.)

### 📋 Testing and Validation

**IMPORTANT: Use test containers for all testing to avoid affecting development data**

```bash
# Test scheduler status (use test containers)
docker exec -it sa-test-sch python scheduler.py status

# Check gap tracking (test database)
docker exec -it sa-test-pg psql -U stockanalyst -d stockanalyst_test -c "SELECT * FROM data_gaps LIMIT 10;"

# Monitor scheduler logs (test scheduler)
docker compose logs -f test-scheduler

# Test web application (test webapp)
docker exec -it sa-test-web python webapp_launcher.py --mode development

# Check undervaluation scores (test database)
docker exec sa-test-pg psql -U stockanalyst -d stockanalyst_test -c "SELECT COUNT(*) FROM undervaluation_scores WHERE undervaluation_score IS NOT NULL;"

# Test automatic recalculation (test database)
docker exec sa-test-pg psql -U stockanalyst -d stockanalyst_test -c "SELECT * FROM pending_undervaluation_recalcs;"

# Run undervaluation calculator (test webapp)
docker exec sa-test-web python yfinance_undervaluation_calculator.py

# Process recalculation queue (test webapp)
docker exec sa-test-web python undervaluation_queue_processor.py

# Run comprehensive API tests (test webapp)
docker exec sa-test-web python tests/test_api_routes_extended.py

# Run API integration tests (test webapp)
docker exec sa-test-web python tests/test_api_integration.py

# Test all API endpoints functionality (test webapp)
docker exec sa-test-web python tests/test_api_debug.py

# Enhanced data collection for missing valuation data (test webapp)
docker exec sa-test-web python enhanced_data_collector.py

# Check enhanced data collection status (test webapp)
docker exec sa-test-web python check_enhanced_data_status.py

# Run batch collection for remaining companies (test webapp)
docker exec sa-test-web python run_enhanced_collection.py

# Check for fake/test data contamination (test webapp)
docker exec sa-test-web python check_fake_data.py

# Short Squeeze Analysis Testing and Validation (test webapp)
docker exec sa-test-web python short_squeeze_analyzer.py

# Run short squeeze comprehensive test suite (test webapp)
docker exec sa-test-web python tests/test_short_squeeze_comprehensive.py

# Test individual short squeeze components (test webapp)
docker exec sa-test-web python -m pytest tests/test_short_squeeze_analyzer.py -v
docker exec sa-test-web python -m pytest tests/test_api_routes_short_squeeze.py -v

# Performance testing for short squeeze analysis (test webapp)
docker exec sa-test-web python -m pytest tests/test_short_squeeze_performance.py -v -s
```



---

This development guide should be kept up-to-date as the application evolves. When adding new features or making architectural changes, please update the relevant sections of this document.

*Last Updated: 2025-07-13*
*Status: All major features complete including short squeeze analysis, undervaluation system with automatic recalculation active, interactive price charts implemented, enhanced user interface with comprehensive valuation analysis completed, comprehensive API test coverage implemented. Documentation updated to reflect actual container architecture using Dockerfile.main with multi-stage builds, current app version 0.0.27, short squeeze quantitative analysis system, and externally managed development environment.*
