#!/usr/bin/env python3
"""
Test script to explore yfinance data structure for:
1. Corporate actions (dividends, splits, etc.)
2. Financial statements (income, balance sheet, cash flow)
3. Analyst recommendations
"""

import yfinance as yf

def test_corporate_actions(symbol="AAPL"):
    """Test corporate actions data from yfinance"""
    print(f"\n=== CORPORATE ACTIONS FOR {symbol} ===")
    
    ticker = yf.Ticker(symbol)
    
    # Test dividends
    print("\n--- DIVIDENDS ---")
    try:
        dividends = ticker.dividends
        if not dividends.empty:
            print(f"Dividends data shape: {dividends.shape}")
            print("Recent dividends:")
            print(dividends.tail())
            print(f"Sample dividend record: {dividends.iloc[-1] if len(dividends) > 0 else 'No data'}")
        else:
            print("No dividend data available")
    except Exception as e:
        print(f"Error getting dividends: {e}")
    
    # Test stock splits
    print("\n--- STOCK SPLITS ---")
    try:
        splits = ticker.splits
        if not splits.empty:
            print(f"Splits data shape: {splits.shape}")
            print("Recent splits:")
            print(splits.tail())
        else:
            print("No stock splits data available")
    except Exception as e:
        print(f"Error getting splits: {e}")
    
    # Test actions (combined)
    print("\n--- COMBINED ACTIONS ---")
    try:
        actions = ticker.actions
        if not actions.empty:
            print(f"Actions data shape: {actions.shape}")
            print("Recent actions:")
            print(actions.tail())
        else:
            print("No actions data available")
    except Exception as e:
        print(f"Error getting actions: {e}")

def test_financial_statements(symbol="AAPL"):
    """Test financial statements data from yfinance"""
    print(f"\n=== FINANCIAL STATEMENTS FOR {symbol} ===")
    
    ticker = yf.Ticker(symbol)
    
    # Test income statement
    print("\n--- INCOME STATEMENT ---")
    try:
        income_stmt = ticker.income_stmt
        if not income_stmt.empty:
            print(f"Income statement shape: {income_stmt.shape}")
            print("Available periods:")
            print(income_stmt.columns.tolist())
            print("Sample metrics:")
            print(income_stmt.head(10))
        else:
            print("No income statement data available")
    except Exception as e:
        print(f"Error getting income statement: {e}")
    
    # Test balance sheet
    print("\n--- BALANCE SHEET ---")
    try:
        balance_sheet = ticker.balance_sheet
        if not balance_sheet.empty:
            print(f"Balance sheet shape: {balance_sheet.shape}")
            print("Available periods:")
            print(balance_sheet.columns.tolist())
            print("Sample metrics:")
            print(balance_sheet.head(10))
        else:
            print("No balance sheet data available")
    except Exception as e:
        print(f"Error getting balance sheet: {e}")
    
    # Test cash flow
    print("\n--- CASH FLOW ---")
    try:
        cash_flow = ticker.cash_flow
        if not cash_flow.empty:
            print(f"Cash flow shape: {cash_flow.shape}")
            print("Available periods:")
            print(cash_flow.columns.tolist())
            print("Sample metrics:")
            print(cash_flow.head(10))
        else:
            print("No cash flow data available")
    except Exception as e:
        print(f"Error getting cash flow: {e}")

def test_analyst_recommendations(symbol="AAPL"):
    """Test analyst recommendations data from yfinance"""
    print(f"\n=== ANALYST RECOMMENDATIONS FOR {symbol} ===")
    
    ticker = yf.Ticker(symbol)
    
    # Test recommendations
    print("\n--- RECOMMENDATIONS ---")
    try:
        recommendations = ticker.recommendations
        if recommendations is not None and not recommendations.empty:
            print(f"Recommendations shape: {recommendations.shape}")
            print("Columns:")
            print(recommendations.columns.tolist())
            print("Recent recommendations:")
            print(recommendations.tail())
        else:
            print("No recommendations data available")
    except Exception as e:
        print(f"Error getting recommendations: {e}")
    
    # Test recommendation summary
    print("\n--- RECOMMENDATION SUMMARY ---")
    try:
        rec_summary = ticker.recommendations_summary
        if rec_summary is not None and not rec_summary.empty:
            print(f"Recommendations summary shape: {rec_summary.shape}")
            print("Columns:")
            print(rec_summary.columns.tolist())
            print("Summary data:")
            print(rec_summary)
        else:
            print("No recommendations summary data available")
    except Exception as e:
        print(f"Error getting recommendations summary: {e}")

def test_additional_data(symbol="AAPL"):
    """Test additional data that might be useful"""
    print(f"\n=== ADDITIONAL DATA FOR {symbol} ===")
    
    ticker = yf.Ticker(symbol)
    
    # Test earnings
    print("\n--- EARNINGS ---")
    try:
        earnings = ticker.earnings
        if earnings is not None and not earnings.empty:
            print(f"Earnings shape: {earnings.shape}")
            print("Earnings data:")
            print(earnings)
        else:
            print("No earnings data available")
    except Exception as e:
        print(f"Error getting earnings: {e}")
    
    # Test quarterly earnings
    print("\n--- QUARTERLY EARNINGS ---")
    try:
        quarterly_earnings = ticker.quarterly_earnings
        if quarterly_earnings is not None and not quarterly_earnings.empty:
            print(f"Quarterly earnings shape: {quarterly_earnings.shape}")
            print("Quarterly earnings data:")
            print(quarterly_earnings.tail())
        else:
            print("No quarterly earnings data available")
    except Exception as e:
        print(f"Error getting quarterly earnings: {e}")

def main():
    """Main test function"""
    print("Testing yfinance data structure for new features...")
    
    # Test with Apple (AAPL) as a well-known stock
    symbol = "AAPL"
    
    test_corporate_actions(symbol)
    test_financial_statements(symbol)
    test_analyst_recommendations(symbol)
    test_additional_data(symbol)
    
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()