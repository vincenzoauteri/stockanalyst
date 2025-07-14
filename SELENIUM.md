# Selenium Frontend Testing Plan

This document outlines a comprehensive plan for implementing frontend tests using Selenium. The goal is to ensure the application's user interface is reliable, functional, and free of regressions.

## Test Environment

*   **Framework:** Pytest with `pytest-selenium`
*   **Browser Driver:** Selenium WebDriver for Chrome, running in a dedicated Docker container.
*   **Test Runner:** Pytest, executed from within the `test-webapp` Docker container.
*   **Base URL:** `http://test-webapp:5000`

## General Principles

1.  **Use Page Object Model (POM):** For more complex pages, consider implementing the Page Object Model to make tests more readable and maintainable.
2.  **Explicit Waits:** Use `WebDriverWait` and `expected_conditions` to handle dynamic content and avoid race conditions. Do not use `time.sleep()`.
3.  **Descriptive Test Names:** Test function names should clearly describe what they are testing.
4.  **Fixtures for Setup:** Use pytest fixtures (like the `authenticated_user` fixture) to set up necessary preconditions, such as logging in a user.
5.  **Assertions:** Each test should have clear and specific assertions to validate the expected outcome.

---

## Test Suite Breakdown

### 1. Authentication

**File:** `app/tests/test_auth_flow.py`

| Test Case | Objective | Steps | Expected Result |
| --- | --- | --- | --- |
| `test_login_with_invalid_credentials` | Ensure login fails with incorrect password. | 1. Navigate to `/login`.<br>2. Enter a valid username and an invalid password.<br>3. Submit the form. | An error message "Invalid credentials" is displayed. The user remains on the `/login` page. |
| `test_logout_flow` | Verify that a logged-in user can successfully log out. | 1. Log in as a test user.<br>2. Click the "Logout" button.<br>3. Navigate back to a protected page like `/portfolio`. | The user is redirected to the `/login` page. A "You have been logged out" message appears. |
| `test_access_protected_page_when_logged_out` | Ensure unauthenticated users cannot access protected pages. | 1. Navigate directly to `/portfolio`. | The user is redirected to the `/login` page. |

### 2. Main Page (Stock List)

**File:** `app/tests/test_main_page.py`

| Test Case | Objective | Steps | Expected Result |
| --- | --- | --- | --- |
| `test_stock_list_loads` | Verify that the main page loads and displays a list of stocks. | 1. Navigate to `/`.<br>2. Wait for the stock table to be present. | The table contains multiple rows (`<tr>`), each representing a stock. |
| `test_pagination_links` | Test the functionality of the pagination controls. | 1. Navigate to `/`.<br>2. Click the "Next" pagination link.<br>3. Click the "Previous" pagination link. | The URL updates with `?page=2`. The content of the stock table changes. After clicking "Previous", the URL returns to the base or `?page=1`. |
| `test_sector_filter` | Ensure the sector filter correctly updates the stock list. | 1. Navigate to `/`.<br>2. Select "Technology" from the sector dropdown.<br>3. Submit the filter form. | The stock table updates to show only stocks from the "Technology" sector. The URL contains `?sector=Technology`. |

### 3. Stock Detail Page

**File:** `app/tests/test_stock_detail_page.py`

| Test Case | Objective | Steps | Expected Result |
| --- | --- | --- | --- |
| `test_stock_detail_page_loads` | Verify that a stock's detail page loads with correct data. | 1. Navigate to `/stock/AAPL`. | The page title contains "AAPL". The company name "Apple Inc." is visible. |
| `test_price_chart_loads` | Ensure the Chart.js price chart is rendered. | 1. Navigate to `/stock/AAPL`.<br>2. Wait for the canvas element for the price chart to be present. | The `<canvas>` element for the chart exists and is visible. |

### 4. Short Squeeze Analysis Page

**File:** `app/tests/test_short_squeeze_page.py`

| Test Case | Objective | Steps | Expected Result |
| --- | --- | --- | --- |
| `test_short_squeeze_page_loads` | Verify the short squeeze analysis page loads and displays data. | 1. Navigate to `/squeeze`.<br>2. Wait for the rankings table to be present. | The table contains multiple rows of stocks with squeeze scores. |
| `test_sort_by_days_to_cover` | Test the sorting functionality of the rankings table. | 1. Navigate to `/squeeze`.<br>2. Select "Days to Cover" from the "Sort By" dropdown.<br>3. Submit the filter form. | The URL updates with `?order_by=dtc_score`. The data in the table is re-ordered. |
| `test_min_score_filter` | Ensure the minimum score filter works correctly. | 1. Navigate to `/squeeze`.<br>2. Enter `70` into the "Min Score" input.<br>3. Submit the filter form. | All stocks in the resulting table have a "Squeeze Score" of 70 or higher. |

### 5. Portfolio Management

**File:** `app/tests/test_portfolio_page.py`

| Test Case | Objective | Steps | Expected Result |
| --- | --- | --- | --- |
| `test_add_transaction` | Test adding a new transaction to the portfolio. | 1. Log in as a test user.<br>2. Navigate to `/portfolio`.<br>3. Fill out the "Add Transaction" form (e.g., BUY, AAPL, 10 shares).<br>4. Submit the form. | A success message appears. The new transaction is visible in the "Recent Transactions" list. The portfolio holdings are updated. |
| `test_delete_transaction` | Verify that a transaction can be deleted. | 1. Add a transaction for a test stock.<br>2. Navigate to the transactions page for that stock.<br>3. Click the "Delete" button for the transaction.<br>4. Confirm the action. | The transaction is removed from the list. The portfolio holdings are updated accordingly. |

### 6. Watchlist Management

**File:** `app/tests/test_watchlist_page.py`

| Test Case | Objective | Steps | Expected Result |
| --- | --- | --- | --- |
| `test_add_to_watchlist` | Test adding a stock to the user's watchlist. | 1. Log in as a test user.<br>2. Navigate to `/watchlist`.<br>3. Enter a valid symbol (e.g., MSFT) in the "Add to Watchlist" form.<br>4. Submit the form. | A success message appears. "MSFT" is now present in the watchlist table. |
| `test_remove_from_watchlist` | Ensure a stock can be removed from the watchlist. | 1. Add "MSFT" to the watchlist.<br>2. Click the "Remove" button for "MSFT". | "MSFT" is removed from the watchlist table. |
