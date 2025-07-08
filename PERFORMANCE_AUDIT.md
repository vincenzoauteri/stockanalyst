# Performance and Responsiveness Audit

This document outlines the findings of a performance audit of the Stock Analyst application, focusing on backend processing, database queries, and frontend rendering. It provides a to-do list of recommended improvements to increase responsiveness and reduce loading times.

## High-Impact Improvements

### 1. Optimize Database Queries and Schema
- **Issue**: Several key database queries are inefficient. The schema is missing critical indexes, and some operations load large amounts of data into memory for processing that should be handled by the database.
- **Files**: `data_access_layer.py`, `database.py`, `api_routes.py`
- **Recommendation**:
    - [ ] **Add Indexes**: Add explicit indexes to all foreign key columns and frequently queried columns. Key candidates include:
        - `undervaluation_scores(symbol)`
        - `historical_prices(symbol, date)`
        - `income_statements(symbol, period_ending)`
        - `balance_sheets(symbol, period_ending)`
        - `cash_flow_statements(symbol, period_ending)`
    - [ ] **Push Filtering/Sorting to Database**: Rewrite the `get_all_stocks_with_scores` function (and its usage in `api_routes.py`) to accept filter and sort parameters. The filtering (`WHERE` clause), sorting (`ORDER BY`), and pagination (`LIMIT`/`OFFSET`) should be performed directly in the SQL query, not in Python. This will dramatically reduce memory usage and improve response time for the main API endpoint.
    - [ ] **Consolidate Queries**: On the `stock_detail` page, multiple separate database calls are made to fetch different pieces of data for a single stock. Combine these into a single, comprehensive query that uses `JOIN`s to retrieve all necessary information at once.

### 2. Implement API-Side Pagination and Server-Side Rendering
- **Issue**: The main page (`index.html`) renders the entire list of 500+ stocks at once, resulting in a large initial HTML payload and a sluggish client-side experience.
- **Files**: `templates/index.html`, `api_routes.py`, `app.py`
- **Recommendation**:
    - [ ] **Paginate the API**: Modify the `/api/v2/stocks` endpoint to support pagination (e.g., using `page` and `per_page` query parameters that translate to `LIMIT` and `OFFSET` in the SQL query).
    - [ ] **Server-Side Pagination**: Implement pagination on the main page. Instead of loading all stocks, load only the first page (e.g., 50 stocks). Provide pagination controls at the bottom of the table to navigate to subsequent pages.
    - [ ] **"Infinite Scroll" (Optional)**: For a more modern user experience, replace traditional pagination with an "infinite scroll" or a "Load More" button that fetches and appends the next page of results via JavaScript without a full page reload.

## Medium-Impact Improvements

### 3. Introduce a Caching Layer
- **Issue**: The application repeatedly queries the database for the same, mostly static, data (e.g., company profiles, historical scores). This creates unnecessary database load.
- **Files**: `data_access_layer.py`, `services.py`
- **Recommendation**:
    - [ ] **Implement a Cache**: Introduce a caching layer using a tool like **Redis** or an in-memory cache like `Flask-Caching`.
    - [ ] **Cache Hot-Spots**: Apply caching to functions in the `StockDataService` that are called frequently and return data that does not change often. Good candidates include:
        - `get_stock_company_profile(symbol)`
        - `get_stock_undervaluation_score(symbol)`
        - `get_sector_analysis()`
    - [ ] **Cache Invalidation**: Implement a cache invalidation strategy. For example, the cache for a stock's data should be cleared whenever the background scheduler updates its information.

### 4. Optimize Frontend Asset Delivery
- **Issue**: Frontend assets (CSS, JavaScript) are not bundled or minified, leading to more HTTP requests and larger file sizes than necessary.
- **Files**: `templates/base.html`, `static/` directory
- **Recommendation**:
    - [ ] **Use a Frontend Build Tool**: Integrate a simple frontend build tool (like `esbuild` or `Vite`) or a Flask-specific extension (like `Flask-Assets`).
    - [ ] **Bundle and Minify**: Configure the tool to bundle all CSS files into one and all JavaScript files into another, and then minify both to reduce their size.
    - [ ] **Update Templates**: Modify `base.html` to link to the newly generated bundled and minified assets instead of the individual source files.

## Low-Impact Improvements

### 5. Optimize Undervaluation Calculation
- **Issue**: The `calculate_all_scores` function in `yfinance_undervaluation_calculator.py` processes symbols one by one. This can be slow.
- **Files**: `yfinance_undervaluation_calculator.py`
- **Recommendation**:
    - [ ] **Batch Processing**: Instead of fetching and processing one symbol at a time, rewrite the logic to fetch data for all symbols in a single, large query. Perform the ratio calculations using vectorized operations in `pandas`, which is significantly faster than row-by-row iteration.
    - [ ] **Parallel Processing**: For multi-core machines, consider using Python's `multiprocessing` module to calculate scores for different batches of stocks in parallel.

### 6. Use a Faster JSON Library
- **Issue**: Python's built-in `json` module is not the fastest implementation available.
- **Files**: `api_routes.py`, `app.py`
- **Recommendation**:
    - [ ] **Install `orjson`**: Install a faster JSON library, such as `orjson`.
    - [ ] **Configure Flask**: Set `orjson` as the default JSON provider for the Flask application. This can provide a small but noticeable speedup for all API endpoints with no other code changes required.
      ```python
      # In app.py
      from flask.json.provider import JSONProvider
      import orjson

      class OrjsonProvider(JSONProvider):
          def dumps(self, obj, **kwargs):
              return orjson.dumps(obj).decode('utf-8')
          def loads(self, s, **kwargs):
              return orjson.loads(s)

      app.json = OrjsonProvider(app)
      ```
