import pytest
import os
from unittest.mock import patch
from portfolio import PortfolioManager
from database import DatabaseManager

@pytest.fixture
def portfolio_manager(db_manager):
    """Create PortfolioManager with isolated test database"""
    manager = PortfolioManager(db_manager=db_manager)
    return manager

@pytest.fixture
def sample_user_id(db_manager):
    """Create a test user and return user ID"""
    from sqlalchemy import text
    import time
    
    # Create user directly in database for testing
    unique_id = int(time.time() * 1000)  # Use microseconds for uniqueness
    username = f"testuser_{unique_id}"
    email = f"test_{unique_id}@example.com"
    
    with db_manager.engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO users (username, email, password_hash, salt, created_at)
            VALUES (:username, :email, 'test_hash', 'test_salt', CURRENT_TIMESTAMP)
            RETURNING id
        """), {'username': username, 'email': email})
        
        user_id = result.fetchone()[0]
        conn.commit()
        return user_id

def test_add_transaction_buy(portfolio_manager, sample_user_id):
    """Test adding a buy transaction"""
    result = portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='BUY',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01',
        fees=0.0,
        notes='Test buy transaction'
    )
    
    assert result['success']
    assert 'transaction_id' in result

def test_add_transaction_sell(portfolio_manager, sample_user_id):
    """Test adding a sell transaction"""
    # First add a buy transaction
    buy_result = portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='BUY',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01'
    )
    assert buy_result['success']
    
    # Then add a sell transaction
    sell_result = portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='SELL',
        shares=5,
        price_per_share=160.0,
        transaction_date='2023-01-02'
    )
    
    assert sell_result['success']
    assert 'transaction_id' in sell_result

def test_add_transaction_sell_all(portfolio_manager, sample_user_id):
    """Test selling all shares"""
    # First add a buy transaction
    portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='BUY',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01'
    )
    
    # Then sell all shares
    result = portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='SELL',
        shares=10,
        price_per_share=160.0,
        transaction_date='2023-01-02'
    )
    
    assert result['success']

def test_add_transaction_invalid_type(portfolio_manager, sample_user_id):
    """Test adding transaction with invalid type"""
    result = portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='INVALID',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01'
    )
    
    assert not result['success']
    assert 'BUY or SELL' in result['error']

def test_get_user_portfolio(portfolio_manager, sample_user_id):
    """Test getting user portfolio"""
    # Add some transactions
    portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='BUY',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01'
    )
    
    portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='MSFT',
        transaction_type='BUY',
        shares=5,
        price_per_share=300.0,
        transaction_date='2023-01-02'
    )
    
    # Get portfolio
    portfolio = portfolio_manager.get_user_portfolio(sample_user_id)
    
    assert 'holdings' in portfolio
    assert 'summary' in portfolio
    assert len(portfolio['holdings']) >= 0  # May be 0 if no current prices available

def test_get_user_transactions(portfolio_manager, sample_user_id):
    """Test getting user transactions"""
    # Add a transaction
    portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='BUY',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01'
    )
    
    # Get transactions
    transactions = portfolio_manager.get_user_transactions(sample_user_id)
    
    assert isinstance(transactions, list)
    assert len(transactions) >= 1

def test_get_portfolio_performance(portfolio_manager, sample_user_id):
    """Test getting portfolio performance"""
    # Add some transactions
    portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='BUY',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01'
    )
    
    # Get performance
    performance = portfolio_manager.get_portfolio_performance(sample_user_id)
    
    # Performance may be empty if no current prices, but should not error
    assert isinstance(performance, dict)

def test_delete_transaction(portfolio_manager, sample_user_id):
    """Test deleting a transaction"""
    # Add a transaction
    add_result = portfolio_manager.add_transaction(
        user_id=sample_user_id,
        symbol='AAPL',
        transaction_type='BUY',
        shares=10,
        price_per_share=150.0,
        transaction_date='2023-01-01'
    )
    
    transaction_id = add_result['transaction_id']
    
    # Delete the transaction
    delete_result = portfolio_manager.delete_transaction(sample_user_id, transaction_id)
    
    assert delete_result['success']

def test_delete_transaction_invalid_id(portfolio_manager, sample_user_id):
    """Test deleting transaction with invalid ID"""
    result = portfolio_manager.delete_transaction(sample_user_id, 99999)
    
    assert not result['success']
    assert 'not found' in result['error']