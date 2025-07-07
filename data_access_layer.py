#!/usr/bin/env python3
"""
Data Access Layer for Stock Analyst Web Application
Handles all database queries and data retrieval operations
"""

from typing import Dict, List, Optional, Tuple
from database import DatabaseManager
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class StockDataService:
    """
    Service layer for accessing stock data from the database
    Separates database logic from web application routes
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def get_all_stocks_with_scores(self) -> List[Dict]:
        """
        Get all S&P 500 stocks with their profiles and undervaluation scores
        
        Returns:
            List of dictionaries containing stock information
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        s.symbol,
                        s.name as company_name,
                        s.sector,
                        s.sub_sector,
                        s.headquarters_location,
                        p.price,
                        p.mktcap,
                        p.pe_ratio,
                        u.undervaluation_score,
                        u.data_quality,
                        CASE WHEN p.symbol IS NOT NULL THEN 1 ELSE 0 END as has_profile,
                        CASE WHEN u.undervaluation_score IS NULL THEN 1 ELSE 0 END as score_null_order
                    FROM sp500_constituents s
                    LEFT JOIN (
                        SELECT symbol, companyname, price, mktcap, 
                               CASE WHEN volavg > 0 THEN mktcap / volavg ELSE NULL END as pe_ratio
                        FROM company_profiles
                    ) p ON s.symbol = p.symbol
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    ORDER BY 
                        score_null_order,
                        u.undervaluation_score DESC NULLS LAST,
                        s.symbol
                """)
                result = conn.execute(query)
                stocks = result.fetchall()
            
            # Convert to list of dictionaries
            stocks_list = []
            for stock in stocks:
                stocks_list.append({
                    'symbol': stock.symbol,
                    'company_name': stock.company_name,
                    'sector': stock.sector,
                    'sub_sector': stock.sub_sector,
                    'headquarters_location': stock.headquarters_location,
                    'price': stock.price,
                    'market_cap': stock.mktcap,
                    'undervaluation_score': stock.undervaluation_score,
                    'data_quality': stock.data_quality,
                    'has_profile': stock.has_profile
                })
            
            return stocks_list
            
        except Exception as e:
            logger.error(f"Error getting stocks with scores: {e}")
            return []
    
    def get_stock_summary_stats(self, stocks_list: List[Dict]) -> Dict:
        """
        Calculate summary statistics for stock data
        
        Args:
            stocks_list: List of stock dictionaries
            
        Returns:
            Dictionary containing summary statistics
        """
        total_stocks = len(stocks_list)
        stocks_with_profiles = sum(1 for s in stocks_list if s['has_profile'])
        sectors = set(s['sector'] for s in stocks_list if s['sector'])
        
        return {
            'total_stocks': total_stocks,
            'stocks_with_profiles': stocks_with_profiles,
            'unique_sectors': len(sectors),
            'sectors': sorted(list(sectors))
        }
    
    def get_stock_basic_info(self, symbol: str) -> Optional[Dict]:
        """
        Get basic S&P 500 information for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with basic stock info or None if not found
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT symbol, name, sector, sub_sector, headquarters_location
                    FROM sp500_constituents 
                    WHERE symbol = :symbol
                """)
                result = conn.execute(query, {"symbol": symbol})
                sp500_info = result.fetchone()
                
                if not sp500_info:
                    return None
                
                return {
                    'symbol': sp500_info.symbol,
                    'name': sp500_info.name,
                    'sector': sp500_info.sector,
                    'sub_sector': sp500_info.sub_sector,
                    'headquarters': sp500_info.headquarters_location
                }
                
        except Exception as e:
            logger.error(f"Error getting basic info for {symbol}: {e}")
            return None
    
    def get_stock_company_profile(self, symbol: str) -> Optional[Dict]:
        """
        Get company profile for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with company profile or None if not found
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT * FROM company_profiles WHERE symbol = :symbol
                """)
                result = conn.execute(query, {"symbol": symbol})
                profile = result.fetchone()
                
                if not profile:
                    return None
                
                # Convert to dict and ensure dates are strings
                profile_dict = dict(profile._mapping)
                # Convert any date/datetime fields to strings
                for key, value in profile_dict.items():
                    if hasattr(value, 'isoformat'):  # Check if it's a date/datetime object
                        profile_dict[key] = value.isoformat()
                return profile_dict
                
        except Exception as e:
            logger.error(f"Error getting company profile for {symbol}: {e}")
            return None
    
    def get_stock_undervaluation_score(self, symbol: str) -> Optional[Dict]:
        """
        Get undervaluation score for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with undervaluation scores or None if not found
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT * FROM undervaluation_scores WHERE symbol = :symbol
                """)
                result = conn.execute(query, {"symbol": symbol})
                score = result.fetchone()
                
                if not score:
                    return None
                
                # Convert to dict and ensure dates are strings
                score_dict = dict(score._mapping)
                # Convert any date/datetime fields to strings
                for key, value in score_dict.items():
                    if hasattr(value, 'isoformat'):  # Check if it's a date/datetime object
                        score_dict[key] = value.isoformat()
                return score_dict
                
        except Exception as e:
            logger.error(f"Error getting undervaluation score for {symbol}: {e}")
            return None
    
    def get_stock_historical_prices(self, symbol: str, limit: int = 252) -> List[Dict]:
        """
        Get historical price data for a stock
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing price data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT date, open, high, low, close, volume
                    FROM historical_prices 
                    WHERE symbol = :symbol
                    ORDER BY date DESC
                    LIMIT :limit
                """)
                result = conn.execute(query, {"symbol": symbol, "limit": limit})
                prices = result.fetchall()
                
                # Convert to dict and ensure dates are strings
                result_list = []
                for price in prices:
                    price_dict = dict(price._mapping)
                    # Convert date to string if it exists
                    if 'date' in price_dict and price_dict['date']:
                        price_dict['date'] = str(price_dict['date'])
                    result_list.append(price_dict)
                return result_list
                
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol}: {e}")
            return []
    
    def get_historical_prices(self, symbol: str, start_date, end_date) -> List[Dict]:
        """
        Get historical price data for a stock within a date range
        
        Args:
            symbol: Stock symbol
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            List of dictionaries containing price data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT date, open, high, low, close, volume
                    FROM historical_prices 
                    WHERE symbol = :symbol
                    AND date >= :start_date
                    AND date <= :end_date
                    ORDER BY date ASC
                """)
                result = conn.execute(query, {
                    "symbol": symbol, 
                    "start_date": start_date,
                    "end_date": end_date
                })
                prices = result.fetchall()
                
                # Convert to dict and ensure dates are datetime objects for proper ordering
                result_list = []
                for price in prices:
                    price_dict = dict(price._mapping)
                    result_list.append(price_dict)
                return result_list
                
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol} from {start_date} to {end_date}: {e}")
            return []
    
    def get_stocks_by_sector(self, sector: str) -> List[Dict]:
        """
        Get all stocks in a specific sector with their undervaluation scores
        
        Args:
            sector: Sector name
            
        Returns:
            List of dictionaries containing stock information for the sector
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        s.symbol,
                        s.name,
                        s.sector,
                        p.price,
                        p.mktcap,
                        u.undervaluation_score,
                        u.valuation_score,
                        u.quality_score,
                        u.strength_score,
                        u.risk_score,
                        u.data_quality
                    FROM sp500_constituents s
                    LEFT JOIN company_profiles p ON s.symbol = p.symbol
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    WHERE s.sector = :sector
                    ORDER BY u.undervaluation_score DESC NULLS LAST
                """)
                result = conn.execute(query, {"sector": sector})
                stocks = result.fetchall()
                
                return [dict(stock._mapping) for stock in stocks]
                
        except Exception as e:
            logger.error(f"Error getting stocks for sector {sector}: {e}")
            return []
    
    def get_sector_analysis(self) -> List[Dict]:
        """
        Get sector-level analysis with aggregated undervaluation scores
        
        Returns:
            List of dictionaries containing sector analysis
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        s.sector,
                        COUNT(s.symbol) as total_stocks,
                        COUNT(u.symbol) as stocks_with_scores,
                        AVG(u.undervaluation_score) as avg_undervaluation_score,
                        AVG(u.valuation_score) as avg_valuation_score,
                        AVG(u.quality_score) as avg_quality_score,
                        AVG(u.strength_score) as avg_strength_score,
                        AVG(p.price) as avg_price,
                        AVG(p.mktcap) as avg_market_cap
                    FROM sp500_constituents s
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    LEFT JOIN company_profiles p ON s.symbol = p.symbol
                    GROUP BY s.sector
                    HAVING s.sector IS NOT NULL
                    ORDER BY avg_undervaluation_score DESC NULLS LAST
                """)
                result = conn.execute(query)
                sectors = result.fetchall()
                
                return [dict(sector._mapping) for sector in sectors]
                
        except Exception as e:
            logger.error(f"Error getting sector analysis: {e}")
            return []
    
    def search_stocks(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for stocks by symbol or company name
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing matching stocks
        """
        try:
            with self.db_manager.engine.connect() as conn:
                search_query = text("""
                    SELECT 
                        s.symbol,
                        s.name,
                        s.sector,
                        p.price,
                        p.mktcap,
                        u.undervaluation_score
                    FROM sp500_constituents s
                    LEFT JOIN company_profiles p ON s.symbol = p.symbol
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    WHERE 
                        UPPER(s.symbol) LIKE UPPER(:query) OR 
                        UPPER(s.name) LIKE UPPER(:search_pattern)
                    ORDER BY 
                        CASE WHEN UPPER(s.symbol) = UPPER(:query) THEN 1 ELSE 2 END,
                        u.undervaluation_score DESC NULLS LAST
                    LIMIT :limit
                """)
                result = conn.execute(search_query, {
                    "query": query,
                    "search_pattern": f"%{query}%",
                    "limit": limit
                })
                stocks = result.fetchall()
                
                return [dict(stock._mapping) for stock in stocks]
                
        except Exception as e:
            logger.error(f"Error searching stocks with query '{query}': {e}")
            return []
    
    def save_historical_prices(self, symbol: str, df):
        """
        Save historical prices data for a symbol
        
        Args:
            symbol: Stock symbol
            df: DataFrame containing historical prices
        """
        try:
            self.db_manager.insert_historical_prices(symbol, df)
            logger.info(f"Successfully saved historical prices for {symbol}")
        except Exception as e:
            logger.error(f"Error saving historical prices for {symbol}: {e}")
            raise
    
    def save_company_profile(self, profile_data: dict):
        """
        Save company profile data for a symbol
        
        Args:
            profile_data: Dictionary containing company profile information
        """
        try:
            symbol = profile_data.get('symbol', 'unknown')
            self.db_manager.insert_company_profile(profile_data)
            logger.info(f"Successfully saved company profile for {symbol}")
        except Exception as e:
            symbol = profile_data.get('symbol', 'unknown') if profile_data else 'unknown'
            logger.error(f"Error saving company profile for {symbol}: {e}")
            raise

    def get_corporate_actions(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Get corporate actions (dividends and stock splits) for a specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing corporate actions data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        action_type,
                        action_date,
                        amount,
                        split_ratio,
                        created_at
                    FROM corporate_actions 
                    WHERE symbol = :symbol
                    ORDER BY action_date DESC
                    LIMIT :limit
                """)
                result = conn.execute(query, {"symbol": symbol, "limit": limit})
                actions = result.fetchall()
                
                return [dict(action._mapping) for action in actions]
                
        except Exception as e:
            logger.error(f"Error getting corporate actions for {symbol}: {e}")
            return []

    def get_all_corporate_actions(self, limit: int = 100) -> List[Dict]:
        """
        Get recent corporate actions across all symbols
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing corporate actions data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        symbol,
                        action_type,
                        action_date,
                        amount,
                        split_ratio,
                        created_at
                    FROM corporate_actions 
                    ORDER BY action_date DESC
                    LIMIT :limit
                """)
                result = conn.execute(query, {"limit": limit})
                actions = result.fetchall()
                
                return [dict(action._mapping) for action in actions]
                
        except Exception as e:
            logger.error(f"Error getting all corporate actions: {e}")
            return []

    def get_all_analyst_recommendations(self, limit: int = 100) -> List[Dict]:
        """
        Get recent analyst recommendations across all symbols
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing analyst recommendations data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        symbol,
                        period,
                        strong_buy,
                        buy,
                        hold,
                        sell,
                        strong_sell,
                        total_analysts,
                        created_at,
                        updated_at
                    FROM analyst_recommendations 
                    ORDER BY updated_at DESC
                    LIMIT :limit
                """)
                result = conn.execute(query, {"limit": limit})
                recommendations = result.fetchall()
                
                return [dict(rec._mapping) for rec in recommendations]
                
        except Exception as e:
            logger.error(f"Error getting all analyst recommendations: {e}")
            return []

    def get_income_statements(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        Get income statements for a specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of periods to return
            
        Returns:
            List of dictionaries containing income statement data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        period_ending,
                        period_type,
                        total_revenue,
                        cost_of_revenue,
                        gross_profit,
                        operating_income,
                        ebit,
                        ebitda,
                        net_income,
                        basic_eps,
                        diluted_eps,
                        shares_outstanding,
                        tax_provision,
                        interest_expense,
                        research_development,
                        selling_general_administrative,
                        updated_at
                    FROM income_statements 
                    WHERE symbol = :symbol
                    ORDER BY period_ending DESC
                    LIMIT :limit
                """)
                result = conn.execute(query, {"symbol": symbol, "limit": limit})
                statements = result.fetchall()
                
                return [dict(statement._mapping) for statement in statements]
                
        except Exception as e:
            logger.error(f"Error getting income statements for {symbol}: {e}")
            return []

    def get_balance_sheets(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        Get balance sheets for a specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of periods to return
            
        Returns:
            List of dictionaries containing balance sheet data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        period_ending,
                        period_type,
                        total_assets,
                        total_liabilities,
                        total_equity,
                        current_assets,
                        current_liabilities,
                        cash_and_equivalents,
                        accounts_receivable,
                        inventory,
                        property_plant_equipment,
                        total_debt,
                        long_term_debt,
                        retained_earnings,
                        working_capital,
                        shares_outstanding,
                        updated_at
                    FROM balance_sheets 
                    WHERE symbol = :symbol
                    ORDER BY period_ending DESC
                    LIMIT :limit
                """)
                result = conn.execute(query, {"symbol": symbol, "limit": limit})
                statements = result.fetchall()
                
                return [dict(statement._mapping) for statement in statements]
                
        except Exception as e:
            logger.error(f"Error getting balance sheets for {symbol}: {e}")
            return []

    def get_cash_flow_statements(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        Get cash flow statements for a specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of periods to return
            
        Returns:
            List of dictionaries containing cash flow statement data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        period_ending,
                        period_type,
                        operating_cash_flow,
                        investing_cash_flow,
                        financing_cash_flow,
                        net_change_in_cash,
                        free_cash_flow,
                        capital_expenditures,
                        dividend_payments,
                        share_repurchases,
                        depreciation_amortization,
                        updated_at
                    FROM cash_flow_statements 
                    WHERE symbol = :symbol
                    ORDER BY period_ending DESC
                    LIMIT :limit
                """)
                result = conn.execute(query, {"symbol": symbol, "limit": limit})
                statements = result.fetchall()
                
                return [dict(statement._mapping) for statement in statements]
                
        except Exception as e:
            logger.error(f"Error getting cash flow statements for {symbol}: {e}")
            return []

    def get_analyst_recommendations(self, symbol: str) -> List[Dict]:
        """
        Get analyst recommendations for a specific symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of dictionaries containing analyst recommendations data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        period,
                        strong_buy,
                        buy,
                        hold,
                        sell,
                        strong_sell,
                        total_analysts,
                        updated_at
                    FROM analyst_recommendations 
                    WHERE symbol = :symbol
                    ORDER BY 
                        CASE 
                            WHEN period = '0m' THEN 0
                            WHEN period = '-1m' THEN 1
                            WHEN period = '-2m' THEN 2
                            WHEN period = '-3m' THEN 3
                            ELSE 999
                        END
                """)
                result = conn.execute(query, {"symbol": symbol})
                recommendations = result.fetchall()
                
                return [dict(rec._mapping) for rec in recommendations]
                
        except Exception as e:
            logger.error(f"Error getting analyst recommendations for {symbol}: {e}")
            return []

    def get_financial_summary(self, symbol: str) -> Dict:
        """
        Get comprehensive financial summary for a symbol including all new data types
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary containing all financial data for the symbol
        """
        try:
            summary = {
                'symbol': symbol,
                'corporate_actions': self.get_corporate_actions(symbol, limit=20),
                'income_statements': self.get_income_statements(symbol, limit=5),
                'balance_sheets': self.get_balance_sheets(symbol, limit=5),
                'cash_flow_statements': self.get_cash_flow_statements(symbol, limit=5),
                'analyst_recommendations': self.get_analyst_recommendations(symbol),
                'historical_prices': self.get_stock_historical_prices(symbol, limit=30)
            }
            
            # Add metadata
            summary['data_availability'] = {
                'has_corporate_actions': len(summary['corporate_actions']) > 0,
                'has_income_statements': len(summary['income_statements']) > 0,
                'has_balance_sheets': len(summary['balance_sheets']) > 0,
                'has_cash_flow_statements': len(summary['cash_flow_statements']) > 0,
                'has_analyst_recommendations': len(summary['analyst_recommendations']) > 0,
                'has_historical_prices': len(summary['historical_prices']) > 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting financial summary for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}

    def get_data_availability_status(self, symbol: str) -> Dict:
        """
        Get data availability status for a symbol including gaps marked as unavailable
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary containing data availability status for each data type
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT gap_type, status, next_retry 
                    FROM data_gaps 
                    WHERE symbol = :symbol 
                    AND status = 'data_unavailable'
                """)
                result = conn.execute(query, {"symbol": symbol})
                unavailable_gaps = result.fetchall()
                
                status = {}
                for gap in unavailable_gaps:
                    gap_type = gap.gap_type
                    retry_time = gap.next_retry
                    status[gap_type] = {
                        'status': 'data_unavailable',
                        'next_retry': retry_time.isoformat() if retry_time else None,
                        'message': 'Data Unavailable'
                    }
                
                return status
                
        except Exception as e:
            logger.error(f"Error getting data availability status for {symbol}: {e}")
            return {}