#!/usr/bin/env python3
"""
Yahoo Finance API Client - Fallback Data Source
Provides basic financial data when FMP API quota is exceeded
Uses yfinance library for free access to Yahoo Finance data
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import yfinance as yf
import requests

logger = logging.getLogger(__name__)

class YahooFinanceClient:
    """
    Yahoo Finance client for basic financial data, using the yfinance library.
    """
    
    def __init__(self):
        self.request_delay = 0.5  # 500ms delay between requests
        self._availability_cache = None
        self._availability_cache_time = None
        self._cache_duration = 300  # 5 minutes cache

    def _get_ticker(self, symbol: str) -> Optional[yf.Ticker]:
        """
        Get a yfinance Ticker object. Let yfinance handle the session.
        """
        try:
            return yf.Ticker(symbol)
        except Exception as e:
            logger.error(f"Failed to create yfinance Ticker for {symbol}: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get basic quote data for a symbol using yfinance.
        """
        logger.info(f"Getting Yahoo Finance quote for {symbol}")
        ticker = self._get_ticker(symbol)
        if not ticker:
            return None

        try:
            # .info can be slow, fetch it once
            info = ticker.info
            if not info:
                logger.warning(f"No yfinance .info data found for {symbol}")
                return None

            # Build standardized response similar to FMP format
            result = {
                'symbol': symbol,
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'price_to_book': info.get('priceToBook'),
                'price_to_sales': info.get('priceToSalesTrailing12Months'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'revenue_growth': info.get('revenueGrowth'),
                'profit_margins': info.get('profitMargins'),
                'gross_margins': info.get('grossMargins'),
                'free_cash_flow': info.get('freeCashflow'),
                'volume': info.get('regularMarketVolume'),
                'avg_volume': info.get('averageVolume'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'dividend_yield': info.get('dividendYield'),
                'source': 'yahoo_finance',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully retrieved Yahoo Finance data for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing Yahoo Finance data for {symbol} using yfinance: {e}")
            return None
    
    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """
        Get basic company profile information using yfinance.
        """
        logger.info(f"Getting Yahoo Finance company profile for {symbol}")
        ticker = self._get_ticker(symbol)
        if not ticker:
            return None

        try:
            info = ticker.info
            if not info:
                logger.warning(f"No yfinance .info data for company profile of {symbol}")
                return None

            # Build profile similar to FMP format
            result = {
                'symbol': symbol,
                'companyname': info.get('longName') or info.get('shortName'),
                'industry': info.get('industry'),
                'sector': info.get('sector'),
                'website': info.get('website'),
                'description': info.get('longBusinessSummary'),
                'country': info.get('country'),
                'city': info.get('city'),
                'state': info.get('state'),
                'fulltimeemployees': info.get('fullTimeEmployees'),
                'phone': info.get('phone'),
                'address': info.get('address1'),
                'zip': info.get('zip'),
                'currency': info.get('currency'),
                'exchange': info.get('exchange'),
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'mktcap': info.get('marketCap')
            }
            
            logger.info(f"Successfully retrieved Yahoo Finance profile for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing Yahoo Finance profile for {symbol} using yfinance: {e}")
            return None
    
    def get_fundamentals_summary(self, symbol: str) -> Optional[Dict]:
        """
        Get fundamentals data for undervaluation analysis using yfinance.
        """
        quote_data = self.get_quote(symbol)
        
        if not quote_data:
            return None
        
        # The get_quote method already fetches all the necessary data from .info
        fundamentals = {
            'symbol': symbol,
            'pe_ratio': quote_data.get('pe_ratio'),
            'price_to_book': quote_data.get('price_to_book'),
            'price_to_sales': quote_data.get('price_to_sales'),
            'roe': quote_data.get('roe'),
            'roa': quote_data.get('roa'),
            'debt_to_equity': quote_data.get('debt_to_equity'),
            'current_ratio': quote_data.get('current_ratio'),
            'revenue_growth': quote_data.get('revenue_growth'),
            'profit_margins': quote_data.get('profit_margins'),
            'gross_margins': quote_data.get('gross_margins'),
            'free_cash_flow': quote_data.get('free_cash_flow'),
            'market_cap': quote_data.get('market_cap'),
            'beta': quote_data.get('beta'),
            'source': 'yahoo_finance',
            'timestamp': datetime.now().isoformat()
        }
        
        return fundamentals
    
    def get_historical_prices(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Get historical price data using yfinance.
        """
        logger.info(f"Getting Yahoo Finance historical data for {symbol} for period {period}")
        ticker = self._get_ticker(symbol)
        if not ticker:
            return None

        try:
            hist = ticker.history(period=period, interval="1d")
            
            if hist.empty:
                logger.warning(f"No historical data found for {symbol} for period {period}")
                return None

            # Reset index to make 'Date' a column
            hist = hist.reset_index()
            
            # Rename columns to match the previous format
            hist.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)

            # Convert 'date' to date object if it's a datetime object
            if pd.api.types.is_datetime64_any_dtype(hist['date']):
                hist['date'] = hist['date'].dt.date

            # Select only the required columns
            df = hist[['date', 'open', 'high', 'low', 'close', 'volume']]
            
            # Clean up null values
            df = df.dropna()
            
            logger.info(f"Retrieved {len(df)} historical records for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing Yahoo Finance historical data for {symbol} using yfinance: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if Yahoo Finance API is available by fetching data for a reliable symbol.
        Uses caching to avoid repeated API calls.
        """
        current_time = time.time()
        
        # Check if we have a cached result that's still valid
        if (self._availability_cache is not None and 
            self._availability_cache_time is not None and
            current_time - self._availability_cache_time < self._cache_duration):
            return self._availability_cache
        
        # Perform availability check
        try:
            test_data = self.get_quote('AAPL')
            result = test_data is not None and test_data.get('price') is not None
            
            # Cache the result
            self._availability_cache = result
            self._availability_cache_time = current_time
            
            return result
        except Exception as e:
            logger.error(f"Yahoo Finance availability check failed: {e}")
            # Cache the failure for a shorter duration
            self._availability_cache = False
            self._availability_cache_time = current_time
            return False
    
    def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get quotes for multiple symbols.
        yfinance can be slow for many individual requests. We'll iterate and add delays.
        A more advanced implementation could use yf.download for prices, but get_quote provides more detail.
        """
        logger.info(f"Getting Yahoo Finance batch quotes for {len(symbols)} symbols")
        
        results = {}
        
        for i, symbol in enumerate(symbols):
            logger.debug(f"Fetching batch quote {i+1}/{len(symbols)}: {symbol}")
            quote = self.get_quote(symbol)
            if quote:
                results[symbol] = quote
            
            # Space out requests to avoid being rate-limited
            time.sleep(self.request_delay)
        
        logger.info(f"Retrieved {len(results)} quotes out of {len(symbols)} requested")
        return results

    def get_corporate_actions(self, symbol: str) -> Optional[Dict]:
        """
        Get corporate actions (dividends and stock splits) for a symbol using yfinance.
        """
        logger.info(f"Getting corporate actions for {symbol}")
        ticker = self._get_ticker(symbol)
        if not ticker:
            return None

        try:
            # Get dividends
            dividends = ticker.dividends
            dividend_data = []
            if not dividends.empty:
                for date, amount in dividends.items():
                    dividend_data.append({
                        'action_type': 'dividend',
                        'action_date': date.strftime('%Y-%m-%d'),
                        'amount': float(amount),
                        'split_ratio': None
                    })

            # Get stock splits
            splits = ticker.splits
            split_data = []
            if not splits.empty:
                for date, ratio in splits.items():
                    split_data.append({
                        'action_type': 'split',
                        'action_date': date.strftime('%Y-%m-%d'),
                        'amount': None,
                        'split_ratio': float(ratio)
                    })

            # Combine all actions
            all_actions = dividend_data + split_data
            
            result = {
                'symbol': symbol,
                'actions': all_actions,
                'dividends_count': len(dividend_data),
                'splits_count': len(split_data),
                'total_actions': len(all_actions),
                'source': 'yahoo_finance',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Retrieved {len(all_actions)} corporate actions for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting corporate actions for {symbol}: {e}")
            return None

    def get_financial_statements(self, symbol: str) -> Optional[Dict]:
        """
        Get financial statements (income, balance sheet, cash flow) for a symbol using yfinance.
        """
        logger.info(f"Getting financial statements for {symbol}")
        ticker = self._get_ticker(symbol)
        if not ticker:
            return None

        try:
            result = {
                'symbol': symbol,
                'income_statements': [],
                'balance_sheets': [],
                'cash_flow_statements': [],
                'source': 'yahoo_finance',
                'timestamp': datetime.now().isoformat()
            }

            # Get income statements
            income_stmt = ticker.income_stmt
            if not income_stmt.empty:
                for period in income_stmt.columns:
                    period_data = {
                        'period_ending': period.strftime('%Y-%m-%d'),
                        'period_type': 'annual',
                        'total_revenue': income_stmt.loc['Total Revenue', period] if 'Total Revenue' in income_stmt.index else None,
                        'cost_of_revenue': income_stmt.loc['Cost Of Revenue', period] if 'Cost Of Revenue' in income_stmt.index else None,
                        'gross_profit': income_stmt.loc['Gross Profit', period] if 'Gross Profit' in income_stmt.index else None,
                        'operating_income': income_stmt.loc['Operating Income', period] if 'Operating Income' in income_stmt.index else None,
                        'ebit': income_stmt.loc['EBIT', period] if 'EBIT' in income_stmt.index else None,
                        'ebitda': income_stmt.loc['EBITDA', period] if 'EBITDA' in income_stmt.index else None,
                        'net_income': income_stmt.loc['Net Income', period] if 'Net Income' in income_stmt.index else None,
                        'basic_eps': income_stmt.loc['Basic EPS', period] if 'Basic EPS' in income_stmt.index else None,
                        'diluted_eps': income_stmt.loc['Diluted EPS', period] if 'Diluted EPS' in income_stmt.index else None,
                        'shares_outstanding': income_stmt.loc['Ordinary Shares Number', period] if 'Ordinary Shares Number' in income_stmt.index else None,
                        'tax_provision': income_stmt.loc['Tax Provision', period] if 'Tax Provision' in income_stmt.index else None,
                        'interest_expense': income_stmt.loc['Interest Expense', period] if 'Interest Expense' in income_stmt.index else None,
                        'research_development': income_stmt.loc['Research And Development', period] if 'Research And Development' in income_stmt.index else None,
                        'selling_general_administrative': income_stmt.loc['Selling General And Administrative', period] if 'Selling General And Administrative' in income_stmt.index else None
                    }
                    # Convert numpy values to Python types
                    for key, value in period_data.items():
                        if value is not None and hasattr(value, 'item'):
                            period_data[key] = float(value.item()) if not pd.isna(value) else None
                    result['income_statements'].append(period_data)

            # Get balance sheets
            balance_sheet = ticker.balance_sheet
            if not balance_sheet.empty:
                for period in balance_sheet.columns:
                    period_data = {
                        'period_ending': period.strftime('%Y-%m-%d'),
                        'period_type': 'annual',
                        'total_assets': balance_sheet.loc['Total Assets', period] if 'Total Assets' in balance_sheet.index else None,
                        'total_liabilities': balance_sheet.loc['Total Liabilities Net Minority Interest', period] if 'Total Liabilities Net Minority Interest' in balance_sheet.index else None,
                        'total_equity': balance_sheet.loc['Total Equity Gross Minority Interest', period] if 'Total Equity Gross Minority Interest' in balance_sheet.index else None,
                        'current_assets': balance_sheet.loc['Current Assets', period] if 'Current Assets' in balance_sheet.index else None,
                        'current_liabilities': balance_sheet.loc['Current Liabilities', period] if 'Current Liabilities' in balance_sheet.index else None,
                        'cash_and_equivalents': balance_sheet.loc['Cash And Cash Equivalents', period] if 'Cash And Cash Equivalents' in balance_sheet.index else None,
                        'accounts_receivable': balance_sheet.loc['Accounts Receivable', period] if 'Accounts Receivable' in balance_sheet.index else None,
                        'inventory': balance_sheet.loc['Inventory', period] if 'Inventory' in balance_sheet.index else None,
                        'property_plant_equipment': balance_sheet.loc['Net PPE', period] if 'Net PPE' in balance_sheet.index else None,
                        'total_debt': balance_sheet.loc['Total Debt', period] if 'Total Debt' in balance_sheet.index else None,
                        'long_term_debt': balance_sheet.loc['Long Term Debt', period] if 'Long Term Debt' in balance_sheet.index else None,
                        'retained_earnings': balance_sheet.loc['Retained Earnings', period] if 'Retained Earnings' in balance_sheet.index else None,
                        'working_capital': balance_sheet.loc['Working Capital', period] if 'Working Capital' in balance_sheet.index else None,
                        'shares_outstanding': balance_sheet.loc['Ordinary Shares Number', period] if 'Ordinary Shares Number' in balance_sheet.index else None
                    }
                    # Convert numpy values to Python types
                    for key, value in period_data.items():
                        if value is not None and hasattr(value, 'item'):
                            period_data[key] = float(value.item()) if not pd.isna(value) else None
                    result['balance_sheets'].append(period_data)

            # Get cash flow statements
            cash_flow = ticker.cash_flow
            if not cash_flow.empty:
                for period in cash_flow.columns:
                    period_data = {
                        'period_ending': period.strftime('%Y-%m-%d'),
                        'period_type': 'annual',
                        'operating_cash_flow': cash_flow.loc['Operating Cash Flow', period] if 'Operating Cash Flow' in cash_flow.index else None,
                        'investing_cash_flow': cash_flow.loc['Investing Cash Flow', period] if 'Investing Cash Flow' in cash_flow.index else None,
                        'financing_cash_flow': cash_flow.loc['Financing Cash Flow', period] if 'Financing Cash Flow' in cash_flow.index else None,
                        'net_change_in_cash': cash_flow.loc['Changes In Cash', period] if 'Changes In Cash' in cash_flow.index else None,
                        'free_cash_flow': cash_flow.loc['Free Cash Flow', period] if 'Free Cash Flow' in cash_flow.index else None,
                        'capital_expenditures': cash_flow.loc['Capital Expenditure', period] if 'Capital Expenditure' in cash_flow.index else None,
                        'dividend_payments': cash_flow.loc['Cash Dividends Paid', period] if 'Cash Dividends Paid' in cash_flow.index else None,
                        'share_repurchases': cash_flow.loc['Repurchase Of Capital Stock', period] if 'Repurchase Of Capital Stock' in cash_flow.index else None,
                        'depreciation_amortization': cash_flow.loc['Depreciation And Amortization', period] if 'Depreciation And Amortization' in cash_flow.index else None
                    }
                    # Convert numpy values to Python types
                    for key, value in period_data.items():
                        if value is not None and hasattr(value, 'item'):
                            period_data[key] = float(value.item()) if not pd.isna(value) else None
                    result['cash_flow_statements'].append(period_data)

            logger.info(f"Retrieved financial statements for {symbol}: {len(result['income_statements'])} income, {len(result['balance_sheets'])} balance, {len(result['cash_flow_statements'])} cash flow")
            return result
            
        except Exception as e:
            logger.error(f"Error getting financial statements for {symbol}: {e}")
            return None

    def get_analyst_recommendations(self, symbol: str) -> Optional[Dict]:
        """
        Get analyst recommendations for a symbol using yfinance.
        """
        logger.info(f"Getting analyst recommendations for {symbol}")
        ticker = self._get_ticker(symbol)
        if not ticker:
            return None

        try:
            recommendations = ticker.recommendations_summary
            if recommendations is None or recommendations.empty:
                logger.warning(f"No analyst recommendations found for {symbol}")
                return None

            recommendations_data = []
            for _, row in recommendations.iterrows():
                total_analysts = (row.get('strongBuy', 0) + row.get('buy', 0) + 
                                row.get('hold', 0) + row.get('sell', 0) + 
                                row.get('strongSell', 0))
                
                rec_data = {
                    'period': row.get('period', ''),
                    'strong_buy': int(row.get('strongBuy', 0)),
                    'buy': int(row.get('buy', 0)),
                    'hold': int(row.get('hold', 0)),
                    'sell': int(row.get('sell', 0)),
                    'strong_sell': int(row.get('strongSell', 0)),
                    'total_analysts': int(total_analysts)
                }
                recommendations_data.append(rec_data)

            result = {
                'symbol': symbol,
                'recommendations': recommendations_data,
                'total_periods': len(recommendations_data),
                'source': 'yahoo_finance',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Retrieved {len(recommendations_data)} analyst recommendation periods for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting analyst recommendations for {symbol}: {e}")
            return None
