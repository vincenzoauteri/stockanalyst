#!/usr/bin/env python3
"""
Portfolio Management System for Stock Analyst Application
Handles user portfolios, transactions, and performance calculations
"""

from datetime import datetime, date
from typing import Dict, List
from sqlalchemy import text
from database import DatabaseManager
from logging_config import get_logger, log_function_call

logger = get_logger(__name__)

class PortfolioManager:
    """Manages user portfolios and transactions"""
    
    def __init__(self):
        """Initialize portfolio manager"""
        self.db_manager = DatabaseManager()
        logger.info("Initializing PortfolioManager with centralized DatabaseManager")
    
    @log_function_call
    def add_transaction(self, user_id: int, symbol: str, transaction_type: str, 
                       shares: float, price_per_share: float, transaction_date: str,
                       fees: float = 0.0, notes: str = None) -> dict:
        """Add a portfolio transaction"""
        logger.info(f"Adding {transaction_type} transaction for user {user_id}: {shares} shares of {symbol} at ${price_per_share}")
        
        # Validate inputs
        if transaction_type not in ['BUY', 'SELL']:
            return {'success': False, 'error': 'Transaction type must be BUY or SELL'}
        
        if shares <= 0:
            return {'success': False, 'error': 'Shares must be greater than 0'}
        
        if price_per_share <= 0:
            return {'success': False, 'error': 'Price per share must be greater than 0'}
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Add transaction record - PostgreSQL only (containerized environment)
                result = conn.execute(text('''
                    INSERT INTO portfolio_transactions 
                    (user_id, symbol, transaction_type, shares, price_per_share, transaction_date, fees, notes)
                    VALUES (:user_id, :symbol, :transaction_type, :shares, :price_per_share, :transaction_date, :fees, :notes)
                    RETURNING id
                '''), {'user_id': user_id, 'symbol': symbol.upper(), 'transaction_type': transaction_type, 
                      'shares': shares, 'price_per_share': price_per_share, 'transaction_date': transaction_date, 
                      'fees': fees, 'notes': notes})
                transaction_id = result.fetchone()[0]
                
                # Update portfolio holdings
                self._update_portfolio_holdings(conn, user_id, symbol.upper())
                
                conn.commit()
                
                logger.info(f"Transaction {transaction_id} added successfully")
                return {'success': True, 'transaction_id': transaction_id}
                
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return {'success': False, 'error': 'Failed to add transaction'}
    
    @log_function_call
    def _update_portfolio_holdings(self, conn, user_id: int, symbol: str):
        """Update portfolio holdings based on transactions"""
        logger.debug(f"Updating portfolio holdings for user {user_id}, symbol {symbol}")
        
        # Calculate current holdings from transactions
        result = conn.execute(text('''
            SELECT 
                SUM(CASE WHEN transaction_type = 'BUY' THEN shares ELSE -shares END) as net_shares,
                SUM(CASE WHEN transaction_type = 'BUY' THEN shares * price_per_share ELSE -shares * price_per_share END) as net_cost
            FROM portfolio_transactions 
            WHERE user_id = :user_id AND symbol = :symbol
        '''), {'user_id': user_id, 'symbol': symbol})
        
        row = result.fetchone()
        net_shares, net_cost = row[0] or 0, row[1] or 0
        
        if net_shares > 0:
            # Calculate average cost basis
            avg_price = net_cost / net_shares
            
            # Get the latest purchase date for this holding
            result = conn.execute(text('''
                SELECT transaction_date FROM portfolio_transactions 
                WHERE user_id = :user_id AND symbol = :symbol AND transaction_type = 'BUY'
                ORDER BY transaction_date DESC LIMIT 1
            '''), {'user_id': user_id, 'symbol': symbol})
            
            latest_purchase = result.fetchone()
            purchase_date = latest_purchase[0] if latest_purchase else date.today().isoformat()
            
            # Insert or update portfolio holding - PostgreSQL only (containerized environment)
            conn.execute(text('''
                INSERT INTO user_portfolios 
                (user_id, symbol, shares, purchase_price, purchase_date, updated_at)
                VALUES (:user_id, :symbol, :shares, :purchase_price, :purchase_date, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, symbol) DO UPDATE SET
                shares = EXCLUDED.shares, purchase_price = EXCLUDED.purchase_price,
                purchase_date = EXCLUDED.purchase_date, updated_at = CURRENT_TIMESTAMP
            '''), {'user_id': user_id, 'symbol': symbol, 'shares': net_shares, 
                  'purchase_price': avg_price, 'purchase_date': purchase_date})
            
            logger.debug(f"Updated holding: {net_shares} shares at avg price ${avg_price:.2f}")
        else:
            # Remove from portfolio if no shares remaining
            conn.execute(text('''
                DELETE FROM user_portfolios WHERE user_id = :user_id AND symbol = :symbol
            '''), {'user_id': user_id, 'symbol': symbol})
            
            logger.debug(f"Removed {symbol} from portfolio (no shares remaining)")
    
    @log_function_call
    def get_user_portfolio(self, user_id: int) -> List[Dict]:
        """Get user's complete portfolio with current values"""
        logger.debug(f"Retrieving portfolio for user {user_id}")
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Get portfolio holdings with current stock data
                result = conn.execute(text('''
                SELECT 
                    up.symbol, up.shares, up.purchase_price, up.purchase_date,
                    cp.companyname, cp.price as current_price, cp.sector,
                    us.undervaluation_score,
                    sc.name
                FROM user_portfolios up
                LEFT JOIN company_profiles cp ON up.symbol = cp.symbol
                LEFT JOIN undervaluation_scores us ON up.symbol = us.symbol
                LEFT JOIN sp500_constituents sc ON up.symbol = sc.symbol
                WHERE up.user_id = :user_id
                ORDER BY up.updated_at DESC
                '''), {'user_id': user_id})
                
                portfolio_data = result.fetchall()
            
            portfolio = []
            total_value = 0
            total_cost = 0
            
            for row in portfolio_data:
                symbol, shares, purchase_price, purchase_date, company_name, current_price, sector, undervaluation_score, name = row
                
                cost_basis = shares * purchase_price
                current_value = shares * (current_price or purchase_price)
                gain_loss = current_value - cost_basis
                gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0
                
                stock = {
                    'symbol': symbol,
                    'shares': shares,
                    'purchase_price': purchase_price,
                    'purchase_date': purchase_date if isinstance(purchase_date, date) else (datetime.fromisoformat(purchase_date).date() if purchase_date else None),
                    'company_name': company_name or name,
                    'current_price': current_price or purchase_price,
                    'sector': sector,
                    'undervaluation_score': undervaluation_score,
                    'cost_basis': cost_basis,
                    'current_value': current_value,
                    'gain_loss': gain_loss,
                    'gain_loss_pct': gain_loss_pct
                }
                
                portfolio.append(stock)
                total_value += current_value
                total_cost += cost_basis
            
            # Calculate portfolio totals
            total_gain_loss = total_value - total_cost
            total_gain_loss_pct = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
            
            logger.debug(f"Retrieved portfolio with {len(portfolio)} holdings, total value: ${total_value:.2f}")
            
            return {
                'holdings': portfolio,
                'summary': {
                    'total_holdings': len(portfolio),
                    'total_value': total_value,
                    'total_cost': total_cost,
                    'total_gain_loss': total_gain_loss,
                    'total_gain_loss_pct': total_gain_loss_pct
                }
            }
            
        except Exception as e:
            logger.error(f"Error retrieving portfolio for user {user_id}: {e}")
            return {'holdings': [], 'summary': {}}
    
    @log_function_call
    def get_user_transactions(self, user_id: int, symbol: str = None, limit: int = None) -> List[Dict]:
        """Get user's transaction history"""
        logger.debug(f"Retrieving transactions for user {user_id}, symbol: {symbol}, limit: {limit}")
        
        try:
            with self.db_manager.engine.connect() as conn:
                query = '''
                    SELECT 
                        id, symbol, transaction_type, shares, price_per_share, 
                        transaction_date, fees, notes, created_at
                    FROM portfolio_transactions 
                    WHERE user_id = :user_id
                '''
                params = {'user_id': user_id}
                
                if symbol:
                    query += ' AND symbol = :symbol'
                    params['symbol'] = symbol.upper()
                
                query += ' ORDER BY transaction_date DESC, created_at DESC'
                
                if limit:
                    query += f' LIMIT {limit}'
                
                result = conn.execute(text(query), params)
                transactions_data = result.fetchall()
            
            transactions = []
            for row in transactions_data:
                transaction = {
                    'id': row[0],
                    'symbol': row[1],
                    'transaction_type': row[2],
                    'shares': row[3],
                    'price_per_share': row[4],
                    'transaction_date': row[5] if isinstance(row[5], date) else (datetime.fromisoformat(row[5]).date() if row[5] else None),
                    'fees': row[6] or 0,
                    'notes': row[7],
                    'created_at': row[8] if isinstance(row[8], datetime) else (datetime.fromisoformat(row[8]) if row[8] else None),
                    'total_amount': row[3] * row[4] + (row[6] or 0)
                }
                transactions.append(transaction)
            
            logger.debug(f"Retrieved {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error retrieving transactions for user {user_id}: {e}")
            return []
    
    @log_function_call
    def get_portfolio_performance(self, user_id: int) -> Dict:
        """Get detailed portfolio performance metrics"""
        logger.debug(f"Calculating portfolio performance for user {user_id}")
        
        try:
            portfolio_data = self.get_user_portfolio(user_id)
            holdings = portfolio_data['holdings']
            summary = portfolio_data['summary']
            
            if not holdings:
                return {'error': 'No holdings found'}
            
            # Calculate additional metrics
            performance = {
                'total_holdings': summary['total_holdings'],
                'total_value': summary['total_value'],
                'total_cost': summary['total_cost'],
                'total_gain_loss': summary['total_gain_loss'],
                'total_gain_loss_pct': summary['total_gain_loss_pct'],
                'best_performer': None,
                'worst_performer': None,
                'sector_allocation': {},
                'largest_holding': None
            }
            
            # Find best and worst performers
            best_gain_pct = float('-inf')
            worst_gain_pct = float('inf')
            largest_value = 0
            
            for holding in holdings:
                gain_pct = holding['gain_loss_pct']
                
                if gain_pct > best_gain_pct:
                    best_gain_pct = gain_pct
                    performance['best_performer'] = holding
                
                if gain_pct < worst_gain_pct:
                    worst_gain_pct = gain_pct
                    performance['worst_performer'] = holding
                
                if holding['current_value'] > largest_value:
                    largest_value = holding['current_value']
                    performance['largest_holding'] = holding
                
                # Sector allocation
                sector = holding['sector'] or 'Other'
                if sector not in performance['sector_allocation']:
                    performance['sector_allocation'][sector] = {'value': 0, 'count': 0}
                performance['sector_allocation'][sector]['value'] += holding['current_value']
                performance['sector_allocation'][sector]['count'] += 1
            
            # Calculate sector percentages
            for sector_data in performance['sector_allocation'].values():
                sector_data['percentage'] = (sector_data['value'] / summary['total_value'] * 100) if summary['total_value'] > 0 else 0
            
            logger.debug("Portfolio performance calculated successfully")
            return performance
            
        except Exception as e:
            logger.error(f"Error calculating portfolio performance for user {user_id}: {e}")
            return {'error': 'Failed to calculate performance'}
    
    @log_function_call
    def delete_transaction(self, user_id: int, transaction_id: int) -> dict:
        """Delete a transaction and update portfolio holdings"""
        logger.info(f"Deleting transaction {transaction_id} for user {user_id}")
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Get transaction details before deletion
                result = conn.execute(text('''
                    SELECT symbol FROM portfolio_transactions 
                    WHERE id = :transaction_id AND user_id = :user_id
                '''), {'transaction_id': transaction_id, 'user_id': user_id})
                
                transaction_data = result.fetchone()
                if not transaction_data:
                    return {'success': False, 'error': 'Transaction not found'}
                
                symbol = transaction_data[0]
                
                # Delete transaction
                result = conn.execute(text('''
                    DELETE FROM portfolio_transactions WHERE id = :transaction_id AND user_id = :user_id
                '''), {'transaction_id': transaction_id, 'user_id': user_id})
                
                if result.rowcount == 0:
                    return {'success': False, 'error': 'Transaction not found or access denied'}
                
                # Update portfolio holdings
                self._update_portfolio_holdings(conn, user_id, symbol)
                
                conn.commit()
            
            logger.info(f"Transaction {transaction_id} deleted successfully")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error deleting transaction {transaction_id}: {e}")
            return {'success': False, 'error': 'Failed to delete transaction'}