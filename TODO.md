# Project TODO List

This file tracks tasks, improvements, and new features for the Stock Analyst application.

## ❗️ Fixes

- [x] **Inconsistent Database Access:** Refactor `auth.py` and `portfolio.py` to use `DatabaseManager` and `StockDataService` instead of direct SQLite connections. This will centralize database logic and support PostgreSQL seamlessly. SQLite code should be removed. ✅ **COMPLETED** - Refactored both AuthenticationManager and PortfolioManager to use centralized DatabaseManager, removed SQLite-specific code.
- [x] **Hardcoded Market Holidays:** In `gap_detector.py`, move the `market_holidays_2024` list to `unified_config.py` to make it configurable and easier to update annually. Update it to 2025. ✅ **COMPLETED** - Added MARKET_HOLIDAYS_2025 to unified_config.py with helper method, updated GapDetector to use centralized config.
- [x] **Default Secret Key:** In `app.py`, add a check to ensure the `SECRET_KEY` is not the default value in a production environment and log a warning if it is. ✅ **COMPLETED** - Added security warning for default secret keys in production environment.
- [x] **Fix `datetime.date` iteration error in `gap_detector.py`:** The `CLAUDE.md` file mentions a known issue with `datetime.date` iteration. Investigate and fix this bug. ✅ **COMPLETED** - Fixed by adding proper type checking before using 'in' operator on date objects.
- [x] **Remove placeholder** The `export_transactions` route in `app.py` has a placeholder for PDF export. Remove it. ✅ **COMPLETED** - Replaced placeholder with proper handling that redirects unsupported formats to CSV.

##  улуч Improvements

- [x] **Consolidate Configuration:** Deprecate and remove `config.py` and `enhanced_config.py`. Ensure all parts of the application use `unified_config.py` for a single source of truth for configuration. ✅ **COMPLETED** - Removed legacy config files and consolidated all configuration to unified_config.py.
- [x] **Refactor Service Getters:** In `api_routes.py` and `app.py`, the `get_*` functions for services are duplicated. Refactor this to a common utility or use Flask's application context to manage service instances. ✅ **COMPLETED** - Created centralized service registry pattern in services.py to eliminate duplicate service getters.
- [x] **Improve Error Handling:** In `api_routes.py` and other places with generic `except Exception`, replace them with more specific exception handling to provide better error responses and logging. ✅ **COMPLETED** - Replaced generic exception handlers with specific exception types across application.
- [ ] **Expand Test Coverage:**
    - [ ] Write unit tests for `fmp_client.py` and `yahoo_finance_client.py`, mocking external API calls.
    - [ ] Write tests for both undervaluation calculators (`undervaluation_analyzer.py` and `yfinance_undervaluation_calculator.py`).
    - [ ] Add tests for the `scheduler.py` logic, mocking time and external dependencies.
    - [ ] Increase test coverage for `api_routes.py` to include all endpoints and edge cases.
- [x] **Code Cleanup:**
    - [x] Remove unused imports and variables across the project. ✅ **COMPLETED** - Removed unused imports across all project files.
    - [ ] Ensure consistent formatting and style.
- [x] **Logging:** Enhance logging to provide more context, especially for background tasks in the scheduler and data fetching processes. ✅ **COMPLETED** - Added structured background task logging with performance metrics and detailed context.

## ✨ New Features

- [ ] **Enhance Frontend Visualizations:**
    - [ ] Add trend charts for financial statement data (e.g., revenue, net income over time).
    - [ ] Implement comparative analysis charts to compare key metrics of multiple stocks.
    - [ ] Add candlestick charts and technical indicators to the stock detail page.
- [ ] **Real-time Data Refresh:** Add a mechanism (e.g., using WebSockets or polling) to refresh data on the frontend without requiring a full page reload.
- [ ] **News Section:** Add a news section to the stock detail page, fetching recent news articles related to the company.
- [ ] **Sector-Specific Undervaluation Models:** Enhance the undervaluation calculator to use different weighting models based on the stock's sector, as valuation metrics can vary significantly between sectors.
- [ ] **User Notifications:** Implement a notification system (e.g., email or in-app) for significant price movements in a user's watchlist or portfolio.
- [ ] **Persistent Scheduler Jobs:** As mentioned in `CLAUDE.md`, consider using a persistent job store for the scheduler (e.g., Redis or a database table) to ensure job persistence across restarts.
