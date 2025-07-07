# Stock Analyst Application - Comprehensive Development Guide

This comprehensive guide provides complete instructions for developers working with the Stock Analyst application, consolidating all project documentation and development guidelines.

## IMPORTANT!!!

When working on this application:

1. **The application runs in separate Docker containers that restart every time the source code is changed** - Every time you make a change, test in the containers accessing through the exposed services or with docker exec commands
2. **First make a plan** of what you plan to modify and ask for confirmation
3. **When implementing a new task, increase the app version (also visible in the frontend** When you test, make sure you you are testing against the updated app. 
4. **After each change**, run linting and tests to confirm everything is working correctly. Perform regression tests on database, frontend, backend, and API calls
5. **If the change does not work, do not keep trying new things.** Log the part that fails extensively and try to debug from the logs
6. **Git commit after each successful change** Keep commit messages short.
7. **Be professional** Be thorough and careful in uour analysis. Don't use emoji or exclamation marks, keep a professional, detached tome.

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
   - Built from: `Dockerfile.webapp`
   - Container name: `sa-web`
   - Port: `5000:5000`
   - Multi-stage build with Python 3.12-slim
   - Production-optimized with virtual environment
   - Depends on PostgreSQL health check
   - Runs: `python webapp_launcher.py --mode production`

3. **Scheduler Container** (`scheduler`)
   - Built from: `Dockerfile.scheduler`
   - Container name: `sa-sch`
   - Background task processing and data updates
   - Depends on PostgreSQL health check
   - Runs: `python scheduler.py run-internal`

4. **Development Environment Container** (`devenv`)
   - Built from: `Dockerfile.devenv`
   - Container name: `devenv`
   - Development tools: Claude Code, Gemini CLI, Git, Docker client
   - Docker socket access for container management
   - Current directory mounted at `/app`
   - You are currently running in this container

5. **Nginx Reverse Proxy** (`nginx`) - Production profile only
   - Container name: `sa-ng`
   - Ports: `80:80`, `443:443`
   - Proxies requests to webapp container

### Container Network
- All containers communicate via `stockanalyst-network` bridge network
- Database accessible at hostname `postgres` from other containers
- Webapp accessible at hostname `webapp` from other containers

### Container Profiles
- **dev**: postgres, webapp, scheduler, devenv
- **production**: postgres, webapp, scheduler, nginx

## Development Commands

### Container Management
```bash
# Start development environment
docker compose --profile dev up -d

# Start production environment  
docker compose --profile production up -d

# Stop all containers
docker compose down

# View container logs
docker compose logs -f [service_name]

# Access development container shell (you are here)
docker exec -it devenv bash

# Access webapp container
docker exec -it sa-web bash

# Access scheduler container
docker exec -it sa-sch bash

# Access database container
docker exec -it sa-pg psql -U stockanalyst -d stockanalyst
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

# Application Startup
./startup.sh                                  # Start both scheduler and web application
python scheduler.py start                     # Start scheduler service
python scheduler.py status                    # Check scheduler status
python scheduler.py stop                      # Stop scheduler service

# Direct Execution
python main.py                                # Run the main stock analysis application
python app.py                                 # Run Flask web application directly

# Testing and Validation
python run_tests.py                           # Run comprehensive test suite
python test_new_implementation.py             # Test new financial data features
python check_records.py                      # Check database record integrity
python gap_detector.py                       # Detect missing data gaps

# Data Management
python data_fetcher.py                       # Fetch and update stock data
python daily_updater.py                     # Run daily data updates manually

# Undervaluation Queue Processing
python undervaluation_queue_processor.py    # Process automatic recalculation queue

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

**Configuration Management (config.py, enhanced_config.py, unified_config.py)** - Multiple configuration layers for different environments

**Centralized Logging System (logging_config.py)** - Comprehensive logging infrastructure with file and console output

**Daily Updater (daily_updater.py)** - Automated daily data collection and processing

**Gap Detection (gap_detector.py)** - Data integrity monitoring and missing data detection

**Data Fetcher (data_fetcher.py)** - Core data collection utilities

**Test Runner (run_tests.py)** - Test execution and validation utilities

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

#### System Tables
- **data_gaps** - Gap tracking with retry mechanisms for data unavailability handling
- **undervaluation_recalc_queue** - Queue for automatic undervaluation score recalculation

### Undervaluation Calculation System

#### Yahoo Finance-Based Calculator (Primary)
- **Fast Performance**: Uses existing database data instead of API calls
- **Comprehensive Metrics**: PE, PB, PS ratios, ROE, ROA, debt ratios, cash flow yields
- **Weighted Scoring**: 40% valuation, 30% profitability, 20% financial strength, 10% cash flow
- **Automatic Recalculation**: Database triggers detect data changes and queue recalculations
- **High Data Quality**: Achieves "high" quality ratings with complete financial statements

#### Automatic Recalculation System
- **Database Triggers**: Automatically detect changes in financial data
- **Queue Processing**: Background processor handles recalculation requests
- **Real-Time Updates**: Scores update automatically when underlying data changes
- **Efficient Processing**: Batch processing with configurable intervals

### Application Architecture
- **Containerized Microservices Architecture**
- **PostgreSQL Database** - Persistent data storage with health checks and triggers
- **Service Isolation** - Separate containers for web, scheduler, and development
- **Container Orchestration** - Docker Compose with development and production profiles
- **Development Environment** - Full-featured container with Docker socket access and development tools

### Web Application Architecture
- **Frontend** - Bootstrap-based responsive interface with interactive financial data visualization
- **Backend** - Flask API with data access layer and comprehensive financial data endpoints
- **Authentication** - Secure user management with session handling
- **Portfolio Management** - Investment tracking and transaction management
- **Data Visualization** - Chart.js integration for interactive price charts and volume analysis

### Data Collection and Processing

#### Yahoo Finance Integration
- **Company Profiles** - Comprehensive company information and real-time pricing
- **Financial Statements** - Income statements, balance sheets, cash flow statements
- **Corporate Actions** - Dividend and stock split tracking with historical data
- **Analyst Recommendations** - Analyst ratings with trend analysis
- **Historical Prices** - Complete price history with volume data

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

## Current Implementation Status

### ✅ Completed Features

#### Core Application (Phase 1)
- ✅ Stock data collection and storage
- ✅ Basic undervaluation analysis system
- ✅ Web interface with stock listings
- ✅ S&P 500 stock database

#### Advanced Features (Phase 2)
- ✅ User authentication and session management
- ✅ Portfolio tracking and transaction management
- ✅ Comprehensive unit and integration tests
- ✅ API refactoring and centralized request handling
- ✅ Interactive charts and enhanced web interface
- ✅ Swagger/OpenAPI documentation
- ✅ Detailed logging infrastructure

#### Financial Data & Infrastructure (Phase 3)
- ✅ Corporate Actions tracking (dividends, stock splits)
- ✅ Financial Statements (income, balance sheet, cash flow)
- ✅ Analyst Recommendations tracking
- ✅ PostgreSQL database migration
- ✅ Docker containerization with health checks
- ✅ Enhanced scheduler with gap detection
- ✅ Catchup strategy with data unavailability handling

#### Advanced Analytics (Phase 4)
- ✅ Yahoo Finance-based undervaluation calculator
- ✅ Automatic recalculation system with database triggers
- ✅ Queue-based processing for score updates
- ✅ High-quality financial ratio calculations
- ✅ Real-time score updates when data changes

#### Interactive Data Visualization (Phase 5)
- ✅ Historical price chart visualization with Chart.js
- ✅ Interactive period selection (1M, 3M, 6M, 1Y, 2Y, 5Y)
- ✅ Chart type options (line and area charts)
- ✅ Volume analysis charts
- ✅ Real-time price statistics and calculations
- ✅ API endpoints for chart data with date range filtering

#### Enhanced User Interface (Phase 6)
- ✅ Application version display (v0.0.1) in frontend header
- ✅ Streamlined stock listing interface with removed redundant metrics
- ✅ Fixed undervaluation calculation functionality with proper API integration
- ✅ Comprehensive Valuation tab for stock detail pages
- ✅ Detailed valuation scoring system with component breakdowns
- ✅ Visual progress indicators for undervaluation score components
- ✅ Color-coded interpretation system for investment guidance
- ✅ Detailed methodology explanations with proper disclaimers

### 🔄 Current Status

**Application State**: Fully functional with comprehensive financial data collection, analysis, interactive visualization, and enhanced user interface
**Data Coverage**: 500+ S&P 500 companies with profile data, financial statements, and corporate actions
**Undervaluation Scores**: Yahoo Finance-based calculator providing high-quality scores with automatic updates and detailed component analysis
**Container Health**: All services running with health checks and automatic restarts
**Data Quality**: High-quality financial data with comprehensive error handling
**Data Visualization**: Interactive price charts with period selection, volume analysis, and real-time statistics
**User Experience**: Enhanced interface with streamlined design, comprehensive valuation analysis, and improved functionality

### 📋 Validation Commands

```bash
# Test scheduler status
docker exec -it sa-sch python scheduler.py status

# Check gap tracking
docker exec -it sa-pg psql -U stockanalyst -d stockanalyst -c "SELECT * FROM data_gaps LIMIT 10;"

# Monitor scheduler logs
docker compose logs -f scheduler

# Test web application
docker exec -it sa-web python webapp_launcher.py --mode development

# Check undervaluation scores
docker exec sa-pg psql -U stockanalyst -d stockanalyst -c "SELECT COUNT(*) FROM undervaluation_scores WHERE undervaluation_score IS NOT NULL;"

# Test automatic recalculation
docker exec sa-pg psql -U stockanalyst -d stockanalyst -c "SELECT * FROM pending_undervaluation_recalcs;"

# Run undervaluation calculator
docker exec sa-web python yfinance_undervaluation_calculator.py

# Process recalculation queue
docker exec sa-web python undervaluation_queue_processor.py
```

## Known Issues and Solutions

### Resolved Issues ✅
- [x] Gap detection missing new data types → Enhanced gap detector
- [x] Template syntax errors → Fixed format_currency filter usage
- [x] Missing analyst recommendations route → Added general route
- [x] Docker containers missing system tools → Added procps, net-tools, lsof
- [x] Flask application restart/reload → **FIXED** - stop.sh script now works properly
- [x] Gap detection artificial limits → **FIXED** - Removed 50-item limits, now shows full scope
- [x] Scheduler not running catchup → **FIXED** - Implemented startup catchup execution
- [x] Rate limiting not working → **FIXED** - 3-consecutive-error detection with 1-hour pause
- [x] Catchup strategy enhancement → **COMPLETED** - Data unavailability handling implemented
- [x] Profile data gap handling → **FIXED** - Added missing profile_data gap type to scheduler
- [x] Database constraint errors → **FIXED** - Implemented proper UPSERT logic for all data types
- [x] Slow undervaluation calculations → **SOLVED** - Created fast Yahoo Finance-based calculator
- [x] Calculate Undervaluation button error → **FIXED** - Corrected API endpoint and JSON response parsing
- [x] Missing valuation analysis interface → **COMPLETED** - Added comprehensive Valuation tab with component scores
- [x] Redundant UI elements → **RESOLVED** - Streamlined interface with appropriate information density

### Outstanding Issues ⚠️
- [ ] Price data gap detection error → Minor issue: `datetime.date` iteration error in gap_detector.py

### Future Enhancements 🔮
- [ ] Add financial statement trend charts and ratio visualizations
- [ ] Implement data export functionality (CSV/Excel export)
- [ ] Add real-time data refresh capabilities for charts
- [ ] Enhance error handling for missing financial data with more granular status messages
- [ ] Add email or push notifications for significant price movements
- [ ] Implement more sophisticated sector-specific undervaluation models
- [ ] Add news section to stock detail pages
- [ ] Implement persistent job store for scheduler (Redis/database)
- [ ] Add candlestick charts and technical indicators
- [ ] Implement comparative analysis charts between stocks

---

This development guide should be kept up-to-date as the application evolves. When adding new features or making architectural changes, please update the relevant sections of this document.

*Last Updated: 2025-07-07*
*Status: All major features complete, undervaluation system with automatic recalculation active, interactive price charts implemented, enhanced user interface with comprehensive valuation analysis completed*
