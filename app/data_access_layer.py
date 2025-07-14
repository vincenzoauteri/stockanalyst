#!/usr/bin/env python3
"""
Data Access Layer for Stock Analyst Web Application
Handles all database queries and data retrieval operations
"""

from typing import Dict, List, Optional
from database import DatabaseManager
from sqlalchemy import text
import logging
from cache_utils import cached_function, get_config
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class StockDataService:
    """
    Service layer for accessing stock data from the database
    Separates database logic from web application routes
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def get_all_stocks_with_scores(self, 
                                   sector: Optional[str] = None,
                                   min_score: Optional[float] = None,
                                   max_score: Optional[float] = None,
                                   sort_by: str = 'symbol',
                                   sort_order: str = 'asc',
                                   limit: Optional[int] = None,
                                   offset: Optional[int] = None) -> List[Dict]:
        """
        Get all S&P 500 stocks with their profiles and undervaluation scores
        
        Args:
            sector: Filter by sector (optional)
            min_score: Minimum undervaluation score (optional)
            max_score: Maximum undervaluation score (optional)
            sort_by: Field to sort by (symbol, score, price, market_cap, sector)
            sort_order: Sort order (asc, desc)
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            
        Returns:
            List of dictionaries containing stock information
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Build dynamic WHERE clause
                where_conditions = []
                params = {}
                
                if sector:
                    where_conditions.append("s.sector = :sector")
                    params['sector'] = sector
                
                if min_score is not None:
                    where_conditions.append("u.undervaluation_score >= :min_score")
                    params['min_score'] = min_score
                
                if max_score is not None:
                    where_conditions.append("u.undervaluation_score <= :max_score")
                    params['max_score'] = max_score
                
                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                
                # Build ORDER BY clause
                sort_column_map = {
                    'symbol': 's.symbol',
                    'name': 's.name',
                    'sector': 's.sector',
                    'price': 'p.price',
                    'market_cap': 'p.mktcap',
                    'score': 'u.undervaluation_score'
                }
                
                sort_column = sort_column_map.get(sort_by, 's.symbol')
                sort_direction = 'DESC' if sort_order.upper() == 'DESC' else 'ASC'
                
                # For numeric columns, handle nulls appropriately
                if sort_by in ['score', 'price', 'market_cap']:
                    if sort_order.upper() == 'DESC':
                        order_clause = f"ORDER BY {sort_column} DESC NULLS LAST"
                    else:
                        order_clause = f"ORDER BY {sort_column} ASC NULLS LAST"
                else:
                    order_clause = f"ORDER BY {sort_column} {sort_direction}"
                
                # Build LIMIT/OFFSET clause
                limit_clause = ""
                if limit is not None:
                    limit_clause = f"LIMIT {limit}"
                    if offset is not None:
                        limit_clause += f" OFFSET {offset}"
                
                query = text(f"""
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
                        CASE WHEN p.symbol IS NOT NULL THEN 1 ELSE 0 END as has_profile
                    FROM sp500_constituents s
                    LEFT JOIN (
                        SELECT symbol, companyname, price, mktcap, 
                               CASE WHEN volavg > 0 THEN mktcap / volavg ELSE NULL END as pe_ratio
                        FROM company_profiles
                    ) p ON s.symbol = p.symbol
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    {where_clause}
                    {order_clause}
                    {limit_clause}
                """)
                
                result = conn.execute(query, params)
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
    
    def get_stocks_count(self, 
                        sector: Optional[str] = None,
                        min_score: Optional[float] = None,
                        max_score: Optional[float] = None) -> int:
        """
        Get total count of stocks matching the filters
        
        Args:
            sector: Filter by sector (optional)
            min_score: Minimum undervaluation score (optional)
            max_score: Maximum undervaluation score (optional)
            
        Returns:
            Total count of stocks matching filters
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Build dynamic WHERE clause
                where_conditions = []
                params = {}
                
                if sector:
                    where_conditions.append("s.sector = :sector")
                    params['sector'] = sector
                
                if min_score is not None:
                    where_conditions.append("u.undervaluation_score >= :min_score")
                    params['min_score'] = min_score
                
                if max_score is not None:
                    where_conditions.append("u.undervaluation_score <= :max_score")
                    params['max_score'] = max_score
                
                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                
                query = text(f"""
                    SELECT COUNT(*) as total_count
                    FROM sp500_constituents s
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    {where_clause}
                """)
                
                result = conn.execute(query, params)
                count = result.fetchone()
                return count.total_count if count else 0
            
        except Exception as e:
            logger.error(f"Error getting stocks count: {e}")
            return 0
    
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
    
    @cached_function(timeout=get_config().CACHE_TIMEOUTS['stock_basic_info'], key_prefix='stock_basic_info')
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
    
    @cached_function(timeout=get_config().CACHE_TIMEOUTS['company_profile'], key_prefix='company_profile')
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
    
    @cached_function(timeout=get_config().CACHE_TIMEOUTS['undervaluation_score'], key_prefix='undervaluation_score')
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
    
    @cached_function(timeout=get_config().CACHE_TIMEOUTS['sector_analysis'], key_prefix='sector_analysis')
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
                        UPPER(s.symbol) LIKE UPPER(:search_pattern) OR 
                        UPPER(s.name) LIKE UPPER(:search_pattern) OR
                        UPPER(s.sector) LIKE UPPER(:search_pattern)
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
    
    def get_comprehensive_stock_data(self, symbol: str) -> Dict:
        """
        Get comprehensive stock data in a single optimized query
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary containing all stock data needed for detail page
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Main comprehensive query
                main_query = text("""
                    SELECT 
                        -- Basic info
                        s.symbol, s.name, s.sector, s.sub_sector, s.headquarters_location,
                        
                        -- Company profile
                        p.price, p.mktcap, p.beta, p.volavg, p.lastdiv, p.range, p.changes,
                        p.companyname, p.currency, p.exchange, p.industry, p.website, 
                        p.description, p.ceo, p.country, p.fulltimeemployees, p.phone,
                        p.address, p.city, p.state, p.zip, p.dcf, p.image, p.ipodate,
                        CASE WHEN p.volavg > 0 THEN p.mktcap / p.volavg ELSE NULL END as pe_ratio,
                        
                        -- Undervaluation scores
                        u.undervaluation_score, u.valuation_score, u.quality_score,
                        u.strength_score, u.risk_score, u.data_quality,
                        
                        -- Profile timestamp
                        p.updated_at as profile_updated_at
                        
                    FROM sp500_constituents s
                    LEFT JOIN company_profiles p ON s.symbol = p.symbol
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    WHERE s.symbol = :symbol
                """)
                
                result = conn.execute(main_query, {"symbol": symbol})
                main_data = result.fetchone()
                
                if not main_data:
                    return {}
                
                # Convert main data to dict
                stock_data = {
                    'basic_info': {
                        'symbol': main_data.symbol,
                        'name': main_data.name,
                        'sector': main_data.sector,
                        'sub_sector': main_data.sub_sector,
                        'headquarters': main_data.headquarters_location
                    }
                }
                
                # Add profile data if available
                if main_data.price is not None:
                    stock_data['profile'] = {
                        'symbol': main_data.symbol,
                        'price': main_data.price,
                        'mktcap': main_data.mktcap,
                        'beta': main_data.beta,
                        'volavg': main_data.volavg,
                        'lastdiv': main_data.lastdiv,
                        'range': main_data.range,
                        'changes': main_data.changes,
                        'companyname': main_data.companyname,
                        'currency': main_data.currency,
                        'exchange': main_data.exchange,
                        'industry': main_data.industry,
                        'website': main_data.website,
                        'description': main_data.description,
                        'ceo': main_data.ceo,
                        'country': main_data.country,
                        'fulltimeemployees': main_data.fulltimeemployees,
                        'phone': main_data.phone,
                        'address': main_data.address,
                        'city': main_data.city,
                        'state': main_data.state,
                        'zip': main_data.zip,
                        'dcf': main_data.dcf,
                        'image': main_data.image,
                        'ipodate': main_data.ipodate,
                        'pe_ratio': main_data.pe_ratio,
                        'updated_at': main_data.profile_updated_at.isoformat() if main_data.profile_updated_at else None
                    }
                
                # Add undervaluation scores if available
                if main_data.undervaluation_score is not None:
                    stock_data['undervaluation'] = {
                        'symbol': main_data.symbol,
                        'undervaluation_score': main_data.undervaluation_score,
                        'valuation_score': main_data.valuation_score,
                        'quality_score': main_data.quality_score,
                        'strength_score': main_data.strength_score,
                        'risk_score': main_data.risk_score,
                        'data_quality': main_data.data_quality,
                        'updated_at': None  # No updated_at column in undervaluation_scores table
                    }
                
                # Get recent price history (last 252 trading days)
                price_query = text("""
                    SELECT date, open, high, low, close, adjclose, volume
                    FROM historical_prices
                    WHERE symbol = :symbol
                    ORDER BY date DESC
                    LIMIT 252
                """)
                
                price_result = conn.execute(price_query, {"symbol": symbol})
                price_history = price_result.fetchall()
                
                if price_history:
                    stock_data['price_history'] = []
                    for price in price_history:
                        stock_data['price_history'].append({
                            'date': price.date.isoformat(),
                            'open': price.open,
                            'high': price.high,
                            'low': price.low,
                            'close': price.close,
                            'adjclose': price.adjclose,
                            'volume': price.volume
                        })
                
                # Get data availability status (gaps marked as unavailable)
                gap_query = text("""
                    SELECT gap_type, status, next_retry 
                    FROM data_gaps 
                    WHERE symbol = :symbol 
                    AND status = 'data_unavailable'
                """)
                
                gap_result = conn.execute(gap_query, {"symbol": symbol})
                unavailable_gaps = gap_result.fetchall()
                
                if unavailable_gaps:
                    stock_data['data_availability'] = {}
                    for gap in unavailable_gaps:
                        gap_type = gap.gap_type
                        retry_time = gap.next_retry
                        stock_data['data_availability'][gap_type] = {
                            'status': 'data_unavailable',
                            'next_retry': retry_time.isoformat() if retry_time else None,
                            'message': 'Data Unavailable'
                        }
                
                return stock_data
                
        except Exception as e:
            logger.error(f"Error getting comprehensive stock data for {symbol}: {e}")
            return {}
    
    def get_stock_comparison(self, symbols: List[str]) -> List[Dict]:
        """
        Get comparison data for multiple stocks
        
        Args:
            symbols: List of stock symbols to compare
            
        Returns:
            List of dictionaries containing comparison data for each stock
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Build query for multiple symbols
                placeholders = ', '.join(f':symbol_{i}' for i in range(len(symbols)))
                params = {f'symbol_{i}': symbol for i, symbol in enumerate(symbols)}
                
                query = text(f"""
                    SELECT 
                        -- Basic info
                        s.symbol, s.name as company_name, s.sector, s.headquarters_location,
                        
                        -- Company profile
                        p.price, p.mktcap as market_cap, p.beta, p.industry,
                        p.companyname, p.currency, p.exchange, p.description,
                        p.ceo, p.country, p.fulltimeemployees,
                        
                        -- Enhanced metrics
                        p.book_value, p.peg_ratio, p.forward_pe, p.return_on_equity,
                        p.return_on_assets, p.operating_cashflow, p.free_cashflow,
                        p.enterprise_value, p.debt_to_equity_ratio,
                        
                        -- Undervaluation scores
                        u.undervaluation_score, u.valuation_score, u.quality_score,
                        u.strength_score, u.risk_score, u.data_quality,
                        
                        -- Latest financial data
                        i.total_revenue, i.net_income, i.basic_eps, i.diluted_eps,
                        i.shares_outstanding,
                        b.total_assets, b.total_equity, b.total_debt,
                        cf.operating_cash_flow, cf.free_cash_flow
                        
                    FROM sp500_constituents s
                    LEFT JOIN company_profiles p ON s.symbol = p.symbol
                    LEFT JOIN undervaluation_scores u ON s.symbol = u.symbol
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, total_revenue, net_income, 
                               basic_eps, diluted_eps, shares_outstanding
                        FROM income_statements
                        ORDER BY symbol, period_ending DESC
                    ) i ON s.symbol = i.symbol
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, total_assets, total_equity, total_debt
                        FROM balance_sheets
                        ORDER BY symbol, period_ending DESC
                    ) b ON s.symbol = b.symbol
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, operating_cash_flow, free_cash_flow
                        FROM cash_flow_statements
                        ORDER BY symbol, period_ending DESC
                    ) cf ON s.symbol = cf.symbol
                    WHERE s.symbol IN ({placeholders})
                    ORDER BY s.symbol
                """)
                
                result = conn.execute(query, params)
                rows = result.fetchall()
                
                comparison_data = []
                for row in rows:
                    # Calculate additional ratios
                    pe_ratio = None
                    pb_ratio = None
                    ps_ratio = None
                    roe = None
                    roa = None
                    
                    if row.price and row.diluted_eps and row.diluted_eps > 0:
                        pe_ratio = row.price / row.diluted_eps
                    
                    if row.price and row.book_value and row.book_value > 0:
                        pb_ratio = row.price / row.book_value
                    elif row.market_cap and row.total_equity and row.total_equity > 0:
                        pb_ratio = row.market_cap / row.total_equity
                    
                    if row.market_cap and row.total_revenue and row.total_revenue > 0:
                        ps_ratio = row.market_cap / row.total_revenue
                    
                    # Use enhanced ROE/ROA if available, otherwise calculate
                    if row.return_on_equity:
                        roe = row.return_on_equity
                    elif row.net_income and row.total_equity and row.total_equity > 0:
                        roe = row.net_income / row.total_equity
                    
                    if row.return_on_assets:
                        roa = row.return_on_assets
                    elif row.net_income and row.total_assets and row.total_assets > 0:
                        roa = row.net_income / row.total_assets
                    
                    stock_data = {
                        'symbol': row.symbol,
                        'company_name': row.company_name,
                        'sector': row.sector,
                        'industry': row.industry,
                        'headquarters': row.headquarters_location,
                        'price': row.price,
                        'market_cap': row.market_cap,
                        'currency': row.currency,
                        'exchange': row.exchange,
                        'description': row.description,
                        'ceo': row.ceo,
                        'country': row.country,
                        'employees': row.fulltimeemployees,
                        'beta': row.beta,
                        'book_value': row.book_value,
                        'peg_ratio': row.peg_ratio,
                        'forward_pe': row.forward_pe,
                        'enterprise_value': row.enterprise_value,
                        'debt_to_equity_ratio': row.debt_to_equity_ratio,
                        'undervaluation_score': row.undervaluation_score,
                        'valuation_score': row.valuation_score,
                        'quality_score': row.quality_score,
                        'strength_score': row.strength_score,
                        'risk_score': row.risk_score,
                        'data_quality': row.data_quality,
                        'revenue': row.total_revenue,
                        'net_income': row.net_income,
                        'eps': row.diluted_eps or row.basic_eps,
                        'shares_outstanding': row.shares_outstanding,
                        'total_assets': row.total_assets,
                        'total_equity': row.total_equity,
                        'total_debt': row.total_debt,
                        'operating_cash_flow': row.operating_cash_flow or row.operating_cashflow,
                        'free_cash_flow': row.free_cash_flow or row.free_cashflow,
                        'pe_ratio': pe_ratio,
                        'pb_ratio': pb_ratio,
                        'ps_ratio': ps_ratio,
                        'roe': roe,
                        'roa': roa
                    }
                    
                    comparison_data.append(stock_data)
                
                return comparison_data
                
        except Exception as e:
            logger.error(f"Error getting stock comparison data: {e}")
            return []

    def calculate_beta(self, symbol: str, market_symbol: str = 'SPY') -> Optional[float]:
        """
        Calculate the beta of a stock relative to a market index.

        Args:
            symbol: The stock symbol.
            market_symbol: The market index symbol (default: 'SPY').

        Returns:
            The calculated beta value, or None if calculation is not possible.
        """
        try:
            config = get_config()
            period_years = config.VALUATION_CONFIG['beta_calculation_period_years']
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_years * 365)

            # Get historical data
            stock_prices = self.get_historical_prices(symbol, start_date, end_date)
            market_prices = self.get_historical_prices(market_symbol, start_date, end_date)

            if len(stock_prices) < 2 or len(market_prices) < 2:
                logger.warning(f"Not enough historical data to calculate beta for {symbol}")
                return None

            # Create pandas DataFrames
            stock_df = pd.DataFrame(stock_prices).set_index('date')['close']
            market_df = pd.DataFrame(market_prices).set_index('date')['close']

            # Align data by date and calculate daily returns
            df = pd.concat([stock_df, market_df], axis=1, keys=[symbol, market_symbol]).dropna()
            returns = df.pct_change().dropna()

            if len(returns) < 2:
                logger.warning(f"Not enough overlapping data to calculate beta for {symbol}")
                return None

            # Calculate covariance and variance
            covariance = returns.cov().iloc[0, 1]
            market_variance = returns[market_symbol].var()

            if market_variance == 0:
                return None

            beta = covariance / market_variance
            return float(beta)

        except Exception as e:
            logger.error(f"Error calculating beta for {symbol}: {e}")
            return None
    
    # Short Squeeze Data Access Methods
    
    def get_short_interest_data(self, symbol: str) -> Optional[Dict]:
        """
        Get the latest short interest data for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with short interest data or None if not found
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT symbol, report_date, short_interest, float_shares, 
                           short_ratio, short_percent_of_float, average_daily_volume,
                           created_at, updated_at
                    FROM short_interest_data 
                    WHERE symbol = :symbol 
                    ORDER BY report_date DESC 
                    LIMIT 1
                """)
                result = conn.execute(query, {"symbol": symbol})
                data = result.fetchone()
                
                if not data:
                    return None
                
                # Convert to dict and format dates
                short_data = dict(data._mapping)
                for key, value in short_data.items():
                    if hasattr(value, 'isoformat'):
                        short_data[key] = value.isoformat()
                
                return short_data
                
        except Exception as e:
            logger.error(f"Error getting short interest data for {symbol}: {e}")
            return None
    
    def get_short_squeeze_score(self, symbol: str) -> Optional[Dict]:
        """
        Get the latest short squeeze score for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with squeeze score data or None if not found
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT symbol, squeeze_score, si_score, dtc_score, float_score,
                           momentum_score, data_quality, raw_metrics,
                           calculated_at, created_at, updated_at
                    FROM short_squeeze_scores 
                    WHERE symbol = :symbol 
                    ORDER BY calculated_at DESC 
                    LIMIT 1
                """)
                result = conn.execute(query, {"symbol": symbol})
                data = result.fetchone()
                
                if not data:
                    return None
                
                # Convert to dict and format dates
                squeeze_data = dict(data._mapping)
                for key, value in squeeze_data.items():
                    if hasattr(value, 'isoformat'):
                        squeeze_data[key] = value.isoformat()
                
                return squeeze_data
                
        except Exception as e:
            logger.error(f"Error getting short squeeze score for {symbol}: {e}")
            return None
    
    def get_short_squeeze_rankings(self, 
                                   limit: int = 50,
                                   order_by: str = 'squeeze_score',
                                   min_score: Optional[float] = None,
                                   min_data_quality: Optional[str] = None) -> List[Dict]:
        """
        Get top short squeeze candidates ranked by various metrics
        
        Args:
            limit: Maximum number of results to return
            order_by: Field to order by (squeeze_score, si_score, dtc_score, float_score, momentum_score)
            min_score: Minimum squeeze score filter
            min_data_quality: Minimum data quality filter (high, medium, low)
            
        Returns:
            List of dictionaries containing ranked squeeze candidates
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Build dynamic WHERE clause
                where_conditions = []
                params = {"limit": limit}
                
                if min_score is not None:
                    where_conditions.append("ss.squeeze_score >= :min_score")
                    params['min_score'] = min_score
                
                if min_data_quality:
                    quality_order = {'high': 3, 'medium': 2, 'low': 1}
                    if min_data_quality in quality_order:
                        where_conditions.append("""
                            CASE 
                                WHEN ss.data_quality = 'high' THEN 3
                                WHEN ss.data_quality = 'medium' THEN 2
                                WHEN ss.data_quality = 'low' THEN 1
                                ELSE 0
                            END >= :min_quality_level
                        """)
                        params['min_quality_level'] = quality_order[min_data_quality]
                
                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                
                # Validate order_by column
                valid_columns = ['squeeze_score', 'si_score', 'dtc_score', 'float_score', 'momentum_score']
                if order_by not in valid_columns:
                    order_by = 'squeeze_score'
                
                query = text(f"""
                    SELECT 
                        ss.symbol,
                        sp.name as company_name,
                        sp.sector,
                        cp.price,
                        cp.mktcap as market_cap,
                        ss.squeeze_score,
                        ss.si_score,
                        ss.dtc_score,
                        ss.float_score,
                        ss.momentum_score,
                        ss.data_quality,
                        ss.calculated_at,
                        si.short_percent_of_float,
                        si.short_ratio,
                        si.float_shares,
                        si.report_date
                    FROM short_squeeze_scores ss
                    LEFT JOIN sp500_constituents sp ON ss.symbol = sp.symbol
                    LEFT JOIN company_profiles cp ON ss.symbol = cp.symbol
                    LEFT JOIN short_interest_data si ON ss.symbol = si.symbol
                    {where_clause}
                    ORDER BY ss.{order_by} DESC NULLS LAST
                    LIMIT :limit
                """)
                
                result = conn.execute(query, params)
                rankings = result.fetchall()
                
                # Convert to list of dictionaries
                results = []
                for rank in rankings:
                    rank_data = dict(rank._mapping)
                    # Format dates
                    for key, value in rank_data.items():
                        if hasattr(value, 'isoformat'):
                            rank_data[key] = value.isoformat()
                    results.append(rank_data)
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting short squeeze rankings: {e}")
            return []
    
    def get_all_short_interest_data(self, limit: int = 100) -> List[Dict]:
        """
        Get recent short interest data across all symbols
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing short interest data
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        si.symbol,
                        sp.name as company_name,
                        si.report_date,
                        si.short_interest,
                        si.float_shares,
                        si.short_ratio,
                        si.short_percent_of_float,
                        si.average_daily_volume,
                        si.created_at
                    FROM short_interest_data si
                    LEFT JOIN sp500_constituents sp ON si.symbol = sp.symbol
                    ORDER BY si.report_date DESC, si.short_percent_of_float DESC NULLS LAST
                    LIMIT :limit
                """)
                result = conn.execute(query, {"limit": limit})
                data = result.fetchall()
                
                # Convert to list of dictionaries
                results = []
                for row in data:
                    row_data = dict(row._mapping)
                    # Format dates
                    for key, value in row_data.items():
                        if hasattr(value, 'isoformat'):
                            row_data[key] = value.isoformat()
                    results.append(row_data)
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting all short interest data: {e}")
            return []
    
    def get_short_squeeze_summary_stats(self) -> Dict:
        """
        Get summary statistics for short squeeze data
        
        Returns:
            Dictionary containing summary statistics
        """
        try:
            with self.db_manager.engine.connect() as conn:
                query = text("""
                    SELECT 
                        COUNT(ss.symbol) as total_scores,
                        COUNT(CASE WHEN ss.data_quality = 'high' THEN 1 END) as high_quality_scores,
                        COUNT(CASE WHEN ss.data_quality = 'medium' THEN 1 END) as medium_quality_scores,
                        COUNT(CASE WHEN ss.data_quality = 'low' THEN 1 END) as low_quality_scores,
                        AVG(ss.squeeze_score) as avg_squeeze_score,
                        MAX(ss.squeeze_score) as max_squeeze_score,
                        COUNT(CASE WHEN ss.squeeze_score >= 70 THEN 1 END) as high_risk_count,
                        COUNT(CASE WHEN ss.squeeze_score >= 50 AND ss.squeeze_score < 70 THEN 1 END) as medium_risk_count,
                        COUNT(CASE WHEN ss.squeeze_score < 50 THEN 1 END) as low_risk_count,
                        COUNT(si.symbol) as total_short_interest_records,
                        AVG(si.short_percent_of_float) as avg_short_percent,
                        MAX(si.short_percent_of_float) as max_short_percent
                    FROM short_squeeze_scores ss
                    FULL OUTER JOIN short_interest_data si ON ss.symbol = si.symbol
                """)
                result = conn.execute(query)
                stats = result.fetchone()
                
                if not stats:
                    return {}
                
                return {
                    'total_scores': stats.total_scores or 0,
                    'high_quality_scores': stats.high_quality_scores or 0,
                    'medium_quality_scores': stats.medium_quality_scores or 0,
                    'low_quality_scores': stats.low_quality_scores or 0,
                    'avg_squeeze_score': round(stats.avg_squeeze_score, 2) if stats.avg_squeeze_score else 0,
                    'max_squeeze_score': round(stats.max_squeeze_score, 2) if stats.max_squeeze_score else 0,
                    'high_risk_count': stats.high_risk_count or 0,
                    'medium_risk_count': stats.medium_risk_count or 0,
                    'low_risk_count': stats.low_risk_count or 0,
                    'total_short_interest_records': stats.total_short_interest_records or 0,
                    'avg_short_percent': round(stats.avg_short_percent, 2) if stats.avg_short_percent else 0,
                    'max_short_percent': round(stats.max_short_percent, 2) if stats.max_short_percent else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting short squeeze summary stats: {e}")
            return {}
    
    def get_comprehensive_short_squeeze_data(self, symbol: str) -> Dict:
        """
        Get comprehensive short squeeze data for a single symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary containing all short squeeze related data
        """
        try:
            result = {
                'symbol': symbol,
                'short_interest': self.get_short_interest_data(symbol),
                'squeeze_score': self.get_short_squeeze_score(symbol),
                'basic_info': self.get_stock_basic_info(symbol),
                'profile': self.get_stock_company_profile(symbol)
            }
            
            # Add availability flags
            result['data_availability'] = {
                'has_short_interest': result['short_interest'] is not None,
                'has_squeeze_score': result['squeeze_score'] is not None,
                'has_basic_info': result['basic_info'] is not None,
                'has_profile': result['profile'] is not None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting comprehensive short squeeze data for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}