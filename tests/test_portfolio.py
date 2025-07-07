import pytest
import sqlite3
import os
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from portfolio import PortfolioManager
from database import DatabaseManager

@pytest.fixture
def temp_db():
    # Create a temporary database file for testing
    import tempfile
    temp_db_file = tempfile.NamedTemporaryFile(delete=False)
    db_path = temp_db_file.name
    temp_db_file.close()
    
    # Set up a real SQLite connection and create necessary tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create necessary tables for portfolio manager
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
            shares REAL NOT NULL,
            price_per_share REAL NOT NULL,
            transaction_date DATE NOT NULL,
            fees REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            shares REAL NOT NULL,
            purchase_price REAL NOT NULL,
            purchase_date DATE NOT NULL,
            purchase_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, symbol)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_profiles (
            symbol TEXT UNIQUE NOT NULL,
            companyname TEXT,
            price REAL,
            sector TEXT,
            mktcap INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS undervaluation_scores (
            symbol TEXT UNIQUE NOT NULL,
            undervaluation_score REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sp500_constituents (
            symbol TEXT UNIQUE NOT NULL,
            name TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Clean up temp database
    try:
        os.unlink(db_path)
    except OSError:
        pass

@pytest.fixture
def portfolio_manager(temp_db):
    # Use the temporary database path
    manager = PortfolioManager(db_path=temp_db)
    return manager

@pytest.fixture
def setup_stock_data(temp_db):
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO company_profiles (symbol, companyname, price, sector, mktcap) VALUES (?, ?, ?, ?, ?)",
                   ('AAPL', 'Apple Inc.', 170.0, 'Technology', 2800000000000))
    cursor.execute("INSERT INTO company_profiles (symbol, companyname, price, sector, mktcap) VALUES (?, ?, ?, ?, ?)",
                   ('MSFT', 'Microsoft Corp.', 400.0, 'Technology', 3000000000000))
    cursor.execute("INSERT INTO undervaluation_scores (symbol, undervaluation_score) VALUES (?, ?)",
                   ('AAPL', 75.5))
    cursor.execute("INSERT INTO sp500_constituents (symbol, name) VALUES (?, ?)",
                   ('AAPL', 'Apple Inc.'))
    cursor.execute("INSERT INTO sp500_constituents (symbol, name) VALUES (?, ?)",
                   ('MSFT', 'Microsoft Corp.'))
    conn.commit()
    conn.close()

def test_add_transaction_buy(portfolio_manager, setup_stock_data):
    user_id = 1
    symbol = "AAPL"
    shares = 10.0
    price_per_share = 150.0
    transaction_date = "2023-01-01"
    fees = 5.0
    notes = "Initial buy"

    result = portfolio_manager.add_transaction(user_id, symbol, "BUY", shares, price_per_share, transaction_date, fees, notes)
    assert result['success']
    assert "transaction_id" in result

    conn = sqlite3.connect(portfolio_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portfolio_transactions WHERE user_id = ? AND symbol = ?", (user_id, symbol))
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT shares, purchase_price FROM user_portfolios WHERE user_id = ? AND symbol = ?", (user_id, symbol))
    holding = cursor.fetchone()
    assert holding[0] == 10.0
    assert holding[1] == 150.0
    conn.close()

def test_add_transaction_sell(portfolio_manager, setup_stock_data):
    user_id = 1
    symbol = "AAPL"
    # First, buy some shares
    portfolio_manager.add_transaction(user_id, symbol, "BUY", 20.0, 150.0, "2023-01-01")

    # Then, sell some shares
    result = portfolio_manager.add_transaction(user_id, symbol, "SELL", 5.0, 160.0, "2023-01-05")
    assert result['success']

    conn = sqlite3.connect(portfolio_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT shares FROM user_portfolios WHERE user_id = ? AND symbol = ?", (user_id, symbol))
    holding = cursor.fetchone()
    assert holding[0] == 15.0 # 20 - 5 = 15
    conn.close()

def test_add_transaction_sell_all(portfolio_manager, setup_stock_data):
    user_id = 1
    symbol = "AAPL"
    portfolio_manager.add_transaction(user_id, symbol, "BUY", 10.0, 150.0, "2023-01-01")
    result = portfolio_manager.add_transaction(user_id, symbol, "SELL", 10.0, 160.0, "2023-01-05")
    assert result['success']

    conn = sqlite3.connect(portfolio_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT shares FROM user_portfolios WHERE user_id = ? AND symbol = ?", (user_id, symbol))
    holding = cursor.fetchone()
    assert holding is None # Should be removed from holdings
    conn.close()

def test_add_transaction_invalid_type(portfolio_manager):
    user_id = 1
    symbol = "AAPL"
    result = portfolio_manager.add_transaction(user_id, symbol, "INVALID", 10.0, 150.0, "2023-01-01")
    assert not result['success']
    assert "Transaction type must be BUY or SELL" in result['error']

def test_get_user_portfolio(portfolio_manager, setup_stock_data):
    user_id = 1
    portfolio_manager.add_transaction(user_id, "AAPL", "BUY", 10.0, 150.0, "2023-01-01")
    portfolio_manager.add_transaction(user_id, "MSFT", "BUY", 5.0, 300.0, "2023-01-02")

    portfolio = portfolio_manager.get_user_portfolio(user_id)
    assert len(portfolio['holdings']) == 2
    assert portfolio['summary']['total_holdings'] == 2

    aapl_holding = next((h for h in portfolio['holdings'] if h['symbol'] == 'AAPL'), None)
    assert aapl_holding is not None
    assert aapl_holding['shares'] == 10.0
    assert aapl_holding['purchase_price'] == 150.0
    assert aapl_holding['current_price'] == 170.0 # From mock company_profiles
    assert aapl_holding['cost_basis'] == 1500.0
    assert aapl_holding['current_value'] == 1700.0
    assert aapl_holding['gain_loss'] == 200.0
    assert aapl_holding['gain_loss_pct'] == pytest.approx(13.33333)

    assert portfolio['summary']['total_value'] == pytest.approx(10*170 + 5*400) # AAPL + MSFT current values

def test_get_user_transactions(portfolio_manager, setup_stock_data):
    user_id = 1
    portfolio_manager.add_transaction(user_id, "AAPL", "BUY", 10.0, 150.0, "2023-01-01")
    portfolio_manager.add_transaction(user_id, "MSFT", "BUY", 5.0, 300.0, "2023-01-02")
    portfolio_manager.add_transaction(user_id, "AAPL", "SELL", 2.0, 160.0, "2023-01-03")

    transactions_all = portfolio_manager.get_user_transactions(user_id)
    assert len(transactions_all) == 3
    assert transactions_all[0]['symbol'] == 'AAPL' # Ordered by date DESC
    assert transactions_all[0]['transaction_type'] == 'SELL'

    transactions_aapl = portfolio_manager.get_user_transactions(user_id, symbol="AAPL")
    assert len(transactions_aapl) == 2
    assert all(t['symbol'] == 'AAPL' for t in transactions_aapl)

    transactions_limit = portfolio_manager.get_user_transactions(user_id, limit=1)
    assert len(transactions_limit) == 1

def test_get_portfolio_performance(portfolio_manager, setup_stock_data):
    user_id = 1
    portfolio_manager.add_transaction(user_id, "AAPL", "BUY", 10.0, 150.0, "2023-01-01")
    portfolio_manager.add_transaction(user_id, "MSFT", "BUY", 5.0, 300.0, "2023-01-02")
    portfolio_manager.add_transaction(user_id, "AAPL", "SELL", 2.0, 160.0, "2023-01-03")

    performance = portfolio_manager.get_portfolio_performance(user_id)
    assert performance['total_holdings'] == 2
    assert performance['total_value'] > 0
    assert performance['total_gain_loss'] > 0
    assert performance['best_performer'] is not None
    assert performance['worst_performer'] is not None
    assert 'Technology' in performance['sector_allocation']
    assert performance['sector_allocation']['Technology']['count'] == 2

def test_delete_transaction(portfolio_manager, setup_stock_data):
    user_id = 1
    portfolio_manager.add_transaction(user_id, "AAPL", "BUY", 10.0, 150.0, "2023-01-01")
    portfolio_manager.add_transaction(user_id, "MSFT", "BUY", 5.0, 300.0, "2023-01-02")

    conn = sqlite3.connect(portfolio_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM portfolio_transactions WHERE user_id = ? AND symbol = ?", (user_id, "AAPL"))
    transaction_id_to_delete = cursor.fetchone()[0]
    conn.close()

    result = portfolio_manager.delete_transaction(user_id, transaction_id_to_delete)
    assert result['success']

    conn = sqlite3.connect(portfolio_manager.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portfolio_transactions WHERE id = ?", (transaction_id_to_delete,))
    assert cursor.fetchone()[0] == 0

    # Verify holdings are updated
    cursor.execute("SELECT COUNT(*) FROM user_portfolios WHERE user_id = ? AND symbol = ?", (user_id, "AAPL"))
    assert cursor.fetchone()[0] == 0 # AAPL holding should be gone
    conn.close()

def test_delete_transaction_invalid_id(portfolio_manager):
    user_id = 1
    result = portfolio_manager.delete_transaction(user_id, 9999)
    assert not result['success']
    assert "Transaction not found" in result['error']
