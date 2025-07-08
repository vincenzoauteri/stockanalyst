# Functional Improvements Audit and To-Do List

This document outlines the findings of a functional audit of the Stock Analyst application. It provides a to-do list of recommended enhancements and new features to improve its capabilities and user experience.

## High-Impact Improvements

### 1. Enhance Portfolio Performance Analysis
- **Issue**: The current portfolio management is excellent for tracking holdings and transactions but lacks historical performance analysis. Users can see their current gain/loss but cannot track performance over time or against a benchmark.
- **Files**: `portfolio.py`, `templates/portfolio.html`
- **Recommendation**:
    - [ ] **Time-Weighted Return (TWR)**: Implement a method to calculate the Time-Weighted Return for the user's portfolio. This is the industry standard for measuring investment performance, as it eliminates the distorting effects of cash inflows/outflows.
    - [ ] **Benchmark Comparison**: Allow users to compare their portfolio's performance against a major index like the S&P 500 (SPY). This requires fetching historical data for the benchmark and plotting it alongside the user's portfolio value over time.
    - [ ] **Performance Chart**: Add a new chart to the portfolio page that visualizes the portfolio's value and performance over various timeframes (e.g., 1M, 6M, 1Y, All-time).

### 2. Implement Advanced User Alerts
- **Issue**: The application is passive; users must actively check for changes. Proactive alerts would significantly increase user engagement and the tool's utility.
- **Files**: `scheduler.py`, `auth.py`
- **Recommendation**:
    - [ ] **Price Alerts**: Allow users to set price targets (upper and lower bounds) for stocks in their watchlist or portfolio.
    - [ ] **Notification System**: Create a notification system. This could start with in-app notifications and be extended to email. This requires adding a user preference for notifications and a background job (in `scheduler.py`) to check for triggered alerts.
    - [ ] **Event Alerts**: Create alerts for significant events, such as an upcoming earnings announcement, ex-dividend date, or a major change in analyst recommendations for a stock in a user's portfolio/watchlist.

### 3. Add Stock Comparison Tools
- **Issue**: The application is designed for analyzing stocks in isolation. A key part of investment analysis is comparing potential investments.
- **Files**: `app.py`, `api_routes.py`
- **Recommendation**:
    - [ ] **Comparison Page**: Create a new page where users can select 2-5 stocks and see their key metrics, financial ratios, and historical price performance displayed side-by-side in a table.
    - [ ] **Comparison API Endpoint**: Add a new API endpoint (e.g., `/api/v2/compare?symbols=AAPL,MSFT,GOOGL`) that returns a consolidated JSON object for the requested symbols, making the frontend implementation straightforward.

## Medium-Impact Improvements

### 4. Enhance the Undervaluation Model
- **Issue**: The undervaluation score is a powerful feature, but its calculation is a black box to the end-user. Increasing transparency and customizability would build trust and provide more utility.
- **Files**: `yfinance_undervaluation_calculator.py`, `templates/stock_detail.html`
- **Recommendation**:
    - [ ] **Detailed Score Breakdown**: On the "Valuation" tab, show not just the component scores (Valuation, Quality, etc.) but the actual metrics that contributed to them (e.g., "P/E Ratio: 15.2 (Score: 75/100), Sector Avg: 22.5").
    - [ ] **User-Weighted Scoring**: For advanced users, allow them to customize the weights of the scoring components (e.g., "I care more about Quality (40%) than Valuation (30%)"). The results could be saved to their user profile.

### 5. Integrate Financial News
- **Issue**: The stock detail page lacks qualitative context, such as recent news, which is crucial for making informed investment decisions.
- **Files**: `stock_detail.html`, `yahoo_finance_client.py` (or a new news API client)
- **Recommendation**:
    - [ ] **News API**: Integrate a free or freemium news API (e.g., MarketAux, NewsAPI.io with proper attribution) to fetch recent news articles for a given stock symbol.
    - [ ] **News Tab**: Add a "News" tab to the stock detail page to display headlines, sources, and publication dates, with links to the full articles.

### 6. Add Basic Technical Analysis Indicators
- **Issue**: The price chart is good for visualization but lacks common technical analysis tools that many investors use.
- **Files**: `stock_detail.html` (JavaScript), `api_routes.py`
- **Recommendation**:
    - [ ] **Moving Averages**: Add options to overlay simple moving averages (SMA) and exponential moving averages (EMA) on the price chart (e.g., 50-day, 200-day).
    - [ ] **RSI Indicator**: Add a separate panel below the price chart to display the Relative Strength Index (RSI).
    - [ ] These calculations can be done on the frontend (in JavaScript) or on the backend.

## Low-Impact (Quality of Life) Improvements

### 7. Improve Filtering and Searching
- **Issue**: The main list of stocks is long and can only be sorted by a few columns. Interactive filtering would make it much easier to discover investment ideas.
- **Files**: `index.html`, `api_routes.py`
- **Recommendation**:
    - [ ] **Interactive Filters**: Add controls to the `index.html` page to allow users to dynamically filter the stock list by sector, market cap range, and undervaluation score range without a full page reload (using JavaScript and the existing API).

### 8. Expand Data Export Capabilities
- **Issue**: Data export is limited to portfolio transactions.
- **Files**: `app.py`
- **Recommendation**:
    - [ ] Add a "Download as CSV" button to the main stock list page.
    - [ ] Allow users to export their watchlist to CSV.
