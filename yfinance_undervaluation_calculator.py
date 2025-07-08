#!/usr/bin/env python3
"""
Yahoo Finance-based Undervaluation Calculator
Calculates undervaluation scores using data already collected from Yahoo Finance
"""

from typing import Dict, List, Optional
from database import DatabaseManager
from sqlalchemy import text
from logging_config import get_logger
import pandas as pd
import numpy as np
from unified_config import get_config

logger = get_logger(__name__)

class YFinanceUndervaluationCalculator:
    """
    Calculate undervaluation scores using Yahoo Finance data already in the database.
    This is much faster than the FMP-based calculator and uses our existing data.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def get_financial_data(self, symbol: str) -> Dict:
        """Get comprehensive financial data for a symbol from our database"""
        try:
            with self.db.engine.connect() as conn:
                # Get company profile data including enhanced metrics
                profile_data = conn.execute(text("""
                    SELECT symbol, companyname, price, mktcap, sector, industry, beta,
                           shares_outstanding, book_value, peg_ratio, forward_pe, 
                           return_on_equity, return_on_assets, operating_cashflow, free_cashflow
                    FROM company_profiles 
                    WHERE symbol = :symbol
                """), {'symbol': symbol}).fetchone()
                
                if not profile_data:
                    return {}
                
                # Get latest income statement data
                income_data = conn.execute(text("""
                    SELECT total_revenue, net_income, basic_eps, diluted_eps, shares_outstanding
                    FROM income_statements 
                    WHERE symbol = :symbol 
                    ORDER BY period_ending DESC 
                    LIMIT 1
                """), {'symbol': symbol}).fetchone()
                
                # Get latest balance sheet data
                balance_data = conn.execute(text("""
                    SELECT total_assets, total_equity, total_debt, current_assets, current_liabilities
                    FROM balance_sheets 
                    WHERE symbol = :symbol 
                    ORDER BY period_ending DESC 
                    LIMIT 1
                """), {'symbol': symbol}).fetchone()
                
                # Get latest cash flow data
                cashflow_data = conn.execute(text("""
                    SELECT operating_cash_flow, free_cash_flow
                    FROM cash_flow_statements 
                    WHERE symbol = :symbol 
                    ORDER BY period_ending DESC 
                    LIMIT 1
                """), {'symbol': symbol}).fetchone()
                
                # Combine all data including enhanced metrics
                result = {
                    'symbol': profile_data.symbol,
                    'company_name': profile_data.companyname,
                    'price': profile_data.price,
                    'market_cap': profile_data.mktcap,
                    'sector': profile_data.sector,
                    'industry': profile_data.industry,
                    'beta': profile_data.beta,
                    'book_value': profile_data.book_value,
                    'peg_ratio': profile_data.peg_ratio,
                    'forward_pe': profile_data.forward_pe,
                    'return_on_equity': profile_data.return_on_equity,
                    'return_on_assets': profile_data.return_on_assets
                }
                
                # Add enhanced shares_outstanding if available (prioritize profile data)
                if profile_data.shares_outstanding:
                    result['shares_outstanding'] = profile_data.shares_outstanding
                
                # Add enhanced cash flow data if available (prioritize profile data)
                if profile_data.operating_cashflow:
                    result['operating_cash_flow'] = profile_data.operating_cashflow
                if profile_data.free_cashflow:
                    result['free_cash_flow'] = profile_data.free_cashflow
                
                if income_data:
                    result.update({
                        'revenue': income_data.total_revenue,
                        'net_income': income_data.net_income,
                        'eps': income_data.diluted_eps or income_data.basic_eps,
                        'shares_outstanding': income_data.shares_outstanding
                    })
                
                if balance_data:
                    result.update({
                        'total_assets': balance_data.total_assets,
                        'total_equity': balance_data.total_equity,
                        'total_debt': balance_data.total_debt,
                        'current_assets': balance_data.current_assets,
                        'current_liabilities': balance_data.current_liabilities
                    })
                
                if cashflow_data:
                    result.update({
                        'operating_cash_flow': cashflow_data.operating_cash_flow,
                        'free_cash_flow': cashflow_data.free_cash_flow
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting financial data for {symbol}: {e}")
            return {}

    def get_historical_growth_rates(self, symbol: str, years: int = 3) -> Dict:
        """Get historical growth rates for revenue and net income."""
        try:
            with self.db.engine.connect() as conn:
                # Get the last `years + 1` years of annual data
                income_data = conn.execute(text(f"""
                    SELECT period_ending, total_revenue, net_income
                    FROM income_statements
                    WHERE symbol = :symbol AND period_type = 'annual'
                    ORDER BY period_ending DESC
                    LIMIT {years + 1}
                """), {'symbol': symbol}).fetchall()

                if len(income_data) < 2:
                    return {}

                df = pd.DataFrame(income_data)
                df = df.sort_values('period_ending').reset_index(drop=True)

                growth_rates = {}

                # Calculate Revenue Growth (CAGR)
                start_revenue = df['total_revenue'].iloc[0]
                end_revenue = df['total_revenue'].iloc[-1]
                num_periods = len(df) - 1

                if start_revenue and start_revenue > 0 and end_revenue:
                    cagr_revenue = (end_revenue / start_revenue) ** (1 / num_periods) - 1
                    growth_rates['revenue_growth_3y'] = cagr_revenue

                # Calculate Earnings Growth (CAGR)
                start_income = df['net_income'].iloc[0]
                end_income = df['net_income'].iloc[-1]

                if start_income and start_income > 0 and end_income and end_income > 0:
                    cagr_income = (end_income / start_income) ** (1 / num_periods) - 1
                    growth_rates['earnings_growth_3y'] = cagr_income
                
                return growth_rates

        except Exception as e:
            logger.error(f"Error calculating growth rates for {symbol}: {e}")
            return {}

    def calculate_ddm_value(self, symbol: str, beta: float, risk_free_rate: float, equity_risk_premium: float) -> Optional[float]:
        """Calculate intrinsic value using the Dividend Discount Model (DDM)."""
        try:
            with self.db.engine.connect() as conn:
                # Get the most recent dividend payment
                dividend_data = conn.execute(text("""
                    SELECT action_date, amount
                    FROM corporate_actions
                    WHERE symbol = :symbol AND action_type = 'dividend' AND amount > 0
                    ORDER BY action_date DESC
                    LIMIT 1
                """), {'symbol': symbol}).fetchone()

                if not dividend_data:
                    return None

                d0 = float(dividend_data.amount)

                # Get historical dividends to calculate growth rate
                historical_dividends = conn.execute(text("""
                    SELECT action_date, amount
                    FROM corporate_actions
                    WHERE symbol = :symbol AND action_type = 'dividend' AND amount > 0
                    ORDER BY action_date DESC
                    LIMIT 5
                """), {'symbol': symbol}).fetchall()

                if len(historical_dividends) < 2:
                    g = 0.025 # Assume a conservative 2.5% growth rate
                else:
                    # Simple growth rate calculation
                    df = pd.DataFrame(historical_dividends)
                    df = df.sort_values('action_date').reset_index(drop=True)
                    df['growth'] = df['amount'].pct_change(fill_method=None)
                    g = df['growth'].mean()
                    if pd.isna(g) or g <= 0:
                        g = 0.025 # Fallback to conservative growth rate

                # Calculate cost of equity (r)
                r = risk_free_rate + beta * equity_risk_premium

                if r <= g:
                    return None # Avoid negative or zero denominator

                # Calculate D1
                d1 = d0 * (1 + g)

                # Calculate DDM value
                intrinsic_value = d1 / (r - g)
                return intrinsic_value

        except Exception as e:
            logger.error(f"Error calculating DDM for {symbol}: {e}")
            return None

    def calculate_dcf_value(self, symbol: str, risk_free_rate: float, equity_risk_premium: float) -> Optional[float]:
        """Calculate intrinsic value using a Discounted Cash Flow (DCF) model."""
        try:
            with self.db.engine.connect() as conn:
                # 1. Get Data
                profile = conn.execute(text("SELECT beta, mktcap FROM company_profiles WHERE symbol = :symbol"), {'symbol': symbol}).fetchone()
                if not profile or not profile.beta:
                    return None

                beta = float(profile.beta)
                market_cap = float(profile.mktcap)

                balance_sheet = conn.execute(text("SELECT total_debt, total_equity FROM balance_sheets WHERE symbol = :symbol ORDER BY period_ending DESC LIMIT 1"), {'symbol': symbol}).fetchone()
                if not balance_sheet:
                    return None
                
                total_debt = float(balance_sheet.total_debt)
                total_equity = float(balance_sheet.total_equity)

                income_statement = conn.execute(text("SELECT interest_expense, tax_provision, net_income FROM income_statements WHERE symbol = :symbol ORDER BY period_ending DESC LIMIT 1"), {'symbol': symbol}).fetchone()
                if not income_statement:
                    return None

                interest_expense = float(income_statement.interest_expense) if income_statement.interest_expense else 0
                tax_provision = float(income_statement.tax_provision) if income_statement.tax_provision else 0
                net_income = float(income_statement.net_income) if income_statement.net_income else 0
                
                # 2. Calculate WACC
                cost_of_equity = risk_free_rate + beta * equity_risk_premium
                cost_of_debt = interest_expense / total_debt if total_debt > 0 else 0.05 # Estimate if not available
                tax_rate = tax_provision / (net_income + tax_provision) if (net_income + tax_provision) > 0 else 0.21 # Estimate if not available
                
                wacc = self._calculate_wacc(market_cap, total_debt, cost_of_equity, cost_of_debt, tax_rate)
                if not wacc:
                    return None

                # 3. Project FCFF
                # For simplicity, we'll use historical FCF growth. A more advanced model would project drivers.
                historical_fcf = conn.execute(text("SELECT free_cash_flow FROM cash_flow_statements WHERE symbol = :symbol AND period_type = 'annual' ORDER BY period_ending DESC LIMIT 5"), {'symbol': symbol}).fetchall()
                if len(historical_fcf) < 2:
                    return None

                fcf_df = pd.DataFrame(historical_fcf)
                fcf_df['growth'] = fcf_df['free_cash_flow'].pct_change(fill_method=None)
                fcf_growth_rate = fcf_df['growth'].mean()
                if pd.isna(fcf_growth_rate) or fcf_growth_rate <= 0:
                    fcf_growth_rate = 0.03 # Conservative growth

                last_fcf = float(historical_fcf[0].free_cash_flow)
                projected_fcf = [last_fcf * (1 + fcf_growth_rate) ** i for i in range(1, 6)]

                # 4. Calculate Terminal Value
                perpetual_growth_rate = 0.025
                terminal_value = (projected_fcf[-1] * (1 + perpetual_growth_rate)) / (wacc - perpetual_growth_rate)

                # 5. Discount Cash Flows
                dcf_values = [fcf / (1 + wacc) ** (i + 1) for i, fcf in enumerate(projected_fcf)]
                present_terminal_value = terminal_value / (1 + wacc) ** 5
                
                enterprise_value = sum(dcf_values) + present_terminal_value

                # 6. Calculate Equity Value
                equity_value = enterprise_value - total_debt
                
                shares_outstanding = conn.execute(text("SELECT shares_outstanding FROM income_statements WHERE symbol = :symbol ORDER BY period_ending DESC LIMIT 1"), {'symbol': symbol}).fetchone()
                if not shares_outstanding or not shares_outstanding.shares_outstanding:
                    return None

                intrinsic_value_per_share = equity_value / float(shares_outstanding.shares_outstanding)
                return intrinsic_value_per_share

        except Exception as e:
            logger.error(f"Error calculating DCF for {symbol}: {e}")
            return None

    def _calculate_wacc(self, market_cap, total_debt, cost_of_equity, cost_of_debt, tax_rate):
        """Helper function to calculate WACC."""
        v = market_cap + total_debt
        if v == 0: return None
        
        wacc = (market_cap / v) * cost_of_equity + (total_debt / v) * cost_of_debt * (1 - tax_rate)
        return wacc
    
    def calculate_financial_ratios(self, data: Dict) -> Dict:
        """Calculate key financial ratios from the available data"""
        ratios = {}
        
        try:
            # Convert all numeric values to float to avoid Decimal issues
            for key, value in data.items():
                if value is not None and hasattr(value, '__float__'):
                    data[key] = float(value)
            
            # Price-to-Earnings ratio
            if data.get('price') and data.get('eps') and data.get('eps') > 0:
                ratios['pe_ratio'] = data['price'] / data['eps']
            
            # Price-to-Book ratio (use enhanced book_value if available)
            if data.get('price') and data.get('book_value') and data.get('book_value') > 0:
                ratios['pb_ratio'] = data['price'] / data['book_value']
            elif data.get('market_cap') and data.get('total_equity') and data.get('total_equity') > 0:
                ratios['pb_ratio'] = data['market_cap'] / data['total_equity']
            
            # Price-to-Sales ratio
            if data.get('market_cap') and data.get('revenue') and data.get('revenue') > 0:
                ratios['ps_ratio'] = data['market_cap'] / data['revenue']
            
            # Return on Equity (use enhanced data if available)
            if data.get('return_on_equity'):
                ratios['roe'] = data['return_on_equity']
            elif data.get('net_income') and data.get('total_equity') and data.get('total_equity') > 0:
                ratios['roe'] = data['net_income'] / data['total_equity']
            
            # Return on Assets (use enhanced data if available)
            if data.get('return_on_assets'):
                ratios['roa'] = data['return_on_assets']
            elif data.get('net_income') and data.get('total_assets') and data.get('total_assets') > 0:
                ratios['roa'] = data['net_income'] / data['total_assets']
            
            # Debt-to-Equity ratio
            if data.get('total_debt') and data.get('total_equity') and data.get('total_equity') > 0:
                ratios['debt_to_equity'] = data['total_debt'] / data['total_equity']
            
            # Current ratio
            if data.get('current_assets') and data.get('current_liabilities') and data.get('current_liabilities') > 0:
                ratios['current_ratio'] = data['current_assets'] / data['current_liabilities']
            
            # Free Cash Flow Yield
            if data.get('free_cash_flow') and data.get('market_cap') and data.get('market_cap') > 0:
                ratios['fcf_yield'] = data['free_cash_flow'] / data['market_cap']

            # PEG Ratio (use enhanced data if available)
            if data.get('peg_ratio'):
                ratios['peg_ratio'] = data['peg_ratio']
            elif ratios.get('pe_ratio') and data.get('earnings_growth_3y') and data.get('earnings_growth_3y') > 0:
                ratios['peg_ratio'] = ratios['pe_ratio'] / (data['earnings_growth_3y'] * 100)
            
            # Forward PE Ratio
            if data.get('forward_pe'):
                ratios['forward_pe'] = data['forward_pe']
            
        except Exception as e:
            logger.error(f"Error calculating ratios for {data.get('symbol', 'unknown')}: {e}")
        
        return ratios
    
    def get_sector_averages(self, sector: str) -> Dict:
        """Calculate sector averages for comparison"""
        try:
            with self.db.engine.connect() as conn:
                sector_data = conn.execute(text("""
                    SELECT 
                        AVG(CASE WHEN i.diluted_eps > 0 THEN cp.price / i.diluted_eps END) as avg_pe,
                        AVG(CASE WHEN b.total_equity > 0 THEN cp.mktcap / b.total_equity END) as avg_pb,
                        AVG(CASE WHEN i.total_revenue > 0 THEN cp.mktcap / i.total_revenue END) as avg_ps,
                        AVG(CASE WHEN b.total_equity > 0 THEN i.net_income / b.total_equity END) as avg_roe,
                        AVG(CASE WHEN b.total_assets > 0 THEN i.net_income / b.total_assets END) as avg_roa,
                        COUNT(*) as company_count
                    FROM company_profiles cp
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, total_revenue, net_income, diluted_eps, basic_eps
                        FROM income_statements 
                        ORDER BY symbol, period_ending DESC
                    ) i ON cp.symbol = i.symbol
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, total_assets, total_equity
                        FROM balance_sheets 
                        ORDER BY symbol, period_ending DESC
                    ) b ON cp.symbol = b.symbol
                    WHERE cp.sector = :sector
                    AND cp.price IS NOT NULL AND cp.mktcap IS NOT NULL
                """), {'sector': sector}).fetchone()
                
                if sector_data and sector_data.company_count > 0:
                    return {
                        'avg_pe': sector_data.avg_pe or 20.0,
                        'avg_pb': sector_data.avg_pb or 3.0,
                        'avg_ps': sector_data.avg_ps or 2.0,
                        'avg_roe': sector_data.avg_roe or 0.10,
                        'avg_roa': sector_data.avg_roa or 0.05,
                        'company_count': sector_data.company_count
                    }
                
        except Exception as e:
            logger.error(f"Error getting sector averages for {sector}: {e}")
        
        # Return default values if no sector data
        return {
            'avg_pe': 20.0,
            'avg_pb': 3.0,
            'avg_ps': 2.0,
            'avg_roe': 0.10,
            'avg_roa': 0.05,
            'company_count': 0
        }
    
    def calculate_relative_score(self, symbol: str) -> Optional[Dict]:
        """Calculate undervaluation score for a single symbol"""
        try:
            # Get financial data
            data = self.get_financial_data(symbol)
            if not data or not data.get('price') or not data.get('market_cap'):
                logger.warning(f"Insufficient data for {symbol}")
                return None

            # Get growth rates
            growth_rates = self.get_historical_growth_rates(symbol)
            data.update(growth_rates)
            
            # Calculate ratios
            ratios = self.calculate_financial_ratios(data)
            if not ratios:
                logger.warning(f"Could not calculate ratios for {symbol}")
                return None
            
            # Get sector averages (for future use)
            sector_avg = self.get_sector_averages(data.get('sector', 'Unknown'))
            
            # Calculate individual scores (0-100 scale)
            scores = {}
            
            # Value Score (lower ratios = higher score, compared to sector average)
            if 'pe_ratio' in ratios and ratios['pe_ratio'] > 0:
                pe_score = max(0, min(100, 100 * (sector_avg['avg_pe'] / ratios['pe_ratio'])))
                scores['pe_score'] = pe_score
            
            if 'pb_ratio' in ratios and ratios['pb_ratio'] > 0:
                pb_score = max(0, min(100, 100 * (sector_avg['avg_pb'] / ratios['pb_ratio'])))
                scores['pb_score'] = pb_score
            
            if 'ps_ratio' in ratios and ratios['ps_ratio'] > 0:
                ps_score = max(0, min(100, 100 * (sector_avg['avg_ps'] / ratios['ps_ratio'])))
                scores['ps_score'] = ps_score

            if 'peg_ratio' in ratios and ratios['peg_ratio'] > 0:
                # PEG ratio score, ideal is 1.0
                peg = ratios['peg_ratio']
                if peg <= 1.0:
                    peg_score = 100
                else:
                    peg_score = max(0, 100 - (peg - 1.0) * 50)
                scores['peg_score'] = peg_score
            
            # Quality Score (higher profitability = higher score)
            if 'roe' in ratios:
                roe_score = max(0, min(100, (ratios['roe'] / sector_avg['avg_roe']) * 100))
                scores['roe_score'] = roe_score
            
            if 'roa' in ratios:
                roa_score = max(0, min(100, (ratios['roa'] / sector_avg['avg_roa']) * 100))
                scores['roa_score'] = roa_score
            
            # Financial Strength Score
            if 'current_ratio' in ratios:
                # Optimal current ratio around 1.5-2.5
                cr = ratios['current_ratio']
                if 1.5 <= cr <= 2.5:
                    cr_score = 100
                elif cr < 1.0:
                    cr_score = 0
                elif cr < 1.5:
                    cr_score = 50 + (cr - 1.0) * 100
                else:
                    cr_score = max(0, 100 - (cr - 2.5) * 20)
                scores['current_ratio_score'] = cr_score
            
            if 'debt_to_equity' in ratios:
                # Lower debt-to-equity is better
                de_score = max(0, min(100, 100 * (1 - ratios['debt_to_equity'] / 2)))  # 0-200% range
                scores['debt_equity_score'] = de_score
            
            # Cash Flow Score
            if 'fcf_yield' in ratios:
                fcf_score = max(0, min(100, ratios['fcf_yield'] * 1000))  # 10% FCF yield = 100 score
                scores['fcf_score'] = fcf_score
            
            # Calculate weighted final score
            value_scores = [scores.get('pe_score'), scores.get('pb_score'), scores.get('ps_score'), scores.get('peg_score')]
            quality_scores = [scores.get('roe_score'), scores.get('roa_score')]
            strength_scores = [scores.get('current_ratio_score'), scores.get('debt_equity_score')]
            cash_scores = [scores.get('fcf_score')]
            
            # Filter out None values and calculate averages
            value_avg = sum(s for s in value_scores if s is not None) / len([s for s in value_scores if s is not None]) if any(s is not None for s in value_scores) else 0
            quality_avg = sum(s for s in quality_scores if s is not None) / len([s for s in quality_scores if s is not None]) if any(s is not None for s in quality_scores) else 0
            strength_avg = sum(s for s in strength_scores if s is not None) / len([s for s in strength_scores if s is not None]) if any(s is not None for s in strength_scores) else 0
            cash_avg = sum(s for s in cash_scores if s is not None) / len([s for s in cash_scores if s is not None]) if any(s is not None for s in cash_scores) else 0
            
            # Weight the components
            final_score = (
                value_avg * 0.4 +      # 40% valuation
                quality_avg * 0.3 +    # 30% quality/profitability  
                strength_avg * 0.2 +   # 20% financial strength
                cash_avg * 0.1         # 10% cash flow
            )
            
            # Determine data quality
            data_points = len([s for s in scores.values() if s is not None])
            if data_points >= 6:
                data_quality = 'high'
            elif data_points >= 3:
                data_quality = 'medium'
            else:
                data_quality = 'low'
            
            result = {
                'symbol': symbol,
                'undervaluation_score': round(final_score, 1),
                'valuation_score': round(value_avg, 1),
                'quality_score': round(quality_avg, 1),
                'strength_score': round(strength_avg, 1),
                'risk_score': round(100 - strength_avg, 1),  # Inverse of strength
                'data_quality': data_quality,
                'sector': data.get('sector'),
                'price': data.get('price'),
                'market_cap': data.get('market_cap'),
                'ratios': ratios,
                'individual_scores': scores
            }
            
            logger.info(f"Calculated undervaluation score for {symbol}: {final_score:.1f} ({data_quality} quality)")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating undervaluation score for {symbol}: {e}")
            return None

    def get_valuation_scorecard(self, symbol: str) -> Optional[Dict]:
        """
        Calculate a comprehensive valuation scorecard for a symbol.
        """
        try:
            # Get config for valuation parameters
            config = get_config()
            risk_free_rate = config.VALUATION_CONFIG['risk_free_rate']
            equity_risk_premium = config.VALUATION_CONFIG['equity_risk_premium']

            # 1. Calculate Relative Score
            relative_score_data = self.calculate_relative_score(symbol)
            if not relative_score_data:
                return None

            # 2. Calculate DDM Value
            beta = relative_score_data.get('ratios', {}).get('beta') # Assuming beta is in ratios
            if not beta:
                with self.db.engine.connect() as conn:
                    profile = conn.execute(text("SELECT beta FROM company_profiles WHERE symbol = :symbol"), {'symbol': symbol}).fetchone()
                    if profile and profile.beta:
                        beta = float(profile.beta)

            ddm_value = None
            if beta:
                ddm_value = self.calculate_ddm_value(symbol, beta, risk_free_rate, equity_risk_premium)

            # 3. Calculate DCF Value
            dcf_value = self.calculate_dcf_value(symbol, risk_free_rate, equity_risk_premium)

            # 4. Synthesize Results
            final_intrinsic_value = None
            weights = {'dcf': 0.5, 'ddm': 0.2, 'relative': 0.3}
            values = []
            if dcf_value:
                values.append(dcf_value * weights['dcf'])
            if ddm_value:
                values.append(ddm_value * weights['ddm'])
            
            # For relative value, we need to estimate a value from the score.
            # This is a simplification. A better approach would be to use peer multiples.
            if relative_score_data.get('undervaluation_score'):
                # This is a rough estimation and should be improved.
                # For now, we assume the score reflects a % discount/premium to the current price.
                relative_value = relative_score_data['price'] * (1 + (relative_score_data['undervaluation_score'] - 50) / 100)
                values.append(relative_value * weights['relative'])

            if values:
                final_intrinsic_value = sum(values) / sum(weights[k] for k, v in {'dcf': dcf_value, 'ddm': ddm_value, 'relative': relative_value}.items() if v is not None)

            # Combine all data
            scorecard = {
                **relative_score_data,
                'dcf_value': dcf_value,
                'ddm_value': ddm_value,
                'final_intrinsic_value': final_intrinsic_value,
            }
            
            return scorecard

        except Exception as e:
            logger.error(f"Error creating valuation scorecard for {symbol}: {e}")
            return None
    
    def save_undervaluation_score(self, score_data: Dict):
        """Save undervaluation score to database"""
        try:
            with self.db.engine.connect() as conn:
                # First, try to update existing record
                result = conn.execute(text("""
                    UPDATE undervaluation_scores 
                    SET sector = :sector,
                        undervaluation_score = :undervaluation_score,
                        valuation_score = :valuation_score,
                        quality_score = :quality_score,
                        strength_score = :strength_score,
                        risk_score = :risk_score,
                        data_quality = :data_quality,
                        price = :price,
                        mktcap = :mktcap,
                        updated_at = CURRENT_TIMESTAMP,
                        dcf_value = :dcf_value,
                        ddm_value = :ddm_value,
                        final_intrinsic_value = :final_intrinsic_value
                    WHERE symbol = :symbol
                """), {
                    'symbol': score_data['symbol'],
                    'sector': score_data['sector'],
                    'undervaluation_score': score_data['undervaluation_score'],
                    'valuation_score': score_data['valuation_score'],
                    'quality_score': score_data['quality_score'],
                    'strength_score': score_data['strength_score'],
                    'risk_score': score_data['risk_score'],
                    'data_quality': score_data['data_quality'],
                    'price': score_data['price'],
                    'mktcap': score_data['market_cap'],
                    'dcf_value': self._convert_numpy_types(score_data.get('dcf_value')),
                    'ddm_value': self._convert_numpy_types(score_data.get('ddm_value')),
                    'final_intrinsic_value': self._convert_numpy_types(score_data.get('final_intrinsic_value')),
                })
                
                # If no rows were updated, insert new record
                if result.rowcount == 0:
                    conn.execute(text("""
                        INSERT INTO undervaluation_scores 
                        (symbol, sector, undervaluation_score, valuation_score, quality_score, 
                         strength_score, risk_score, data_quality, price, mktcap, updated_at,
                         dcf_value, ddm_value, final_intrinsic_value)
                        VALUES (:symbol, :sector, :undervaluation_score, :valuation_score, :quality_score, 
                                :strength_score, :risk_score, :data_quality, :price, :mktcap, CURRENT_TIMESTAMP,
                                :dcf_value, :ddm_value, :final_intrinsic_value)
                    """), {
                        'symbol': score_data['symbol'],
                        'sector': score_data['sector'],
                        'undervaluation_score': score_data['undervaluation_score'],
                        'valuation_score': score_data['valuation_score'],
                        'quality_score': score_data['quality_score'],
                        'strength_score': score_data['strength_score'],
                        'risk_score': score_data['risk_score'],
                        'data_quality': score_data['data_quality'],
                        'price': score_data['price'],
                        'mktcap': score_data['market_cap'],
                        'dcf_value': self._convert_numpy_types(score_data.get('dcf_value')),
                        'ddm_value': self._convert_numpy_types(score_data.get('ddm_value')),
                        'final_intrinsic_value': self._convert_numpy_types(score_data.get('final_intrinsic_value')),
                    })
                conn.commit()
            
            logger.debug(f"Saved undervaluation score for {score_data['symbol']}")
            
        except Exception as e:
            logger.error(f"Error saving undervaluation score for {score_data['symbol']}: {e}")
            raise
    
    def calculate_all_scores_batch(self, limit: Optional[int] = None, batch_size: int = 50) -> Dict:
        """Calculate undervaluation scores for all companies using batch processing"""
        logger.info("Starting Yahoo Finance-based undervaluation analysis with batch processing")
        
        try:
            # Get config for valuation parameters
            config = get_config()

            # Get all symbols and their data in a single query
            with self.db.engine.connect() as conn:
                query = """
                    SELECT 
                        cp.symbol,
                        cp.price,
                        cp.mktcap,
                        cp.sector,
                        cp.beta,
                        -- Income statement data (latest)
                        i.total_revenue,
                        i.net_income,
                        i.basic_eps,
                        i.shares_outstanding,
                        i.interest_expense,
                        i.tax_provision,
                        -- Balance sheet data (latest)
                        b.total_assets,
                        b.total_equity,
                        b.total_debt,
                        b.cash_and_equivalents,
                        -- Cash flow data (latest)
                        cf.operating_cash_flow,
                        cf.free_cash_flow
                    FROM company_profiles cp
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, total_revenue, net_income, basic_eps, shares_outstanding, interest_expense, tax_provision
                        FROM income_statements
                        WHERE period_type = 'annual'
                        ORDER BY symbol, period_ending DESC
                    ) i ON cp.symbol = i.symbol
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, total_assets, total_equity, total_debt, cash_and_equivalents
                        FROM balance_sheets
                        WHERE period_type = 'annual'
                        ORDER BY symbol, period_ending DESC
                    ) b ON cp.symbol = b.symbol
                    LEFT JOIN (
                        SELECT DISTINCT ON (symbol) symbol, operating_cash_flow, free_cash_flow
                        FROM cash_flow_statements
                        WHERE period_type = 'annual'
                        ORDER BY symbol, period_ending DESC
                    ) cf ON cp.symbol = cf.symbol
                    WHERE cp.price IS NOT NULL AND cp.mktcap IS NOT NULL
                    ORDER BY cp.symbol
                """
                if limit:
                    query += f" LIMIT {limit}"
                    
                all_data = conn.execute(text(query)).fetchall()
            
            logger.info(f"Processing {len(all_data)} companies in batches of {batch_size}")
            
            successful = 0
            failed = 0
            
            # Process in batches
            for i in range(0, len(all_data), batch_size):
                batch = all_data[i:i+batch_size]
                batch_scores = []
                
                for row in batch:
                    try:
                        # Convert row to dict
                        data = dict(row._mapping)
                        
                        score_data = self.calculate_scorecard_from_data(data, config)
                        if score_data:
                            batch_scores.append(score_data)
                            successful += 1
                        else:
                            failed += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to process {row.symbol}: {e}")
                        failed += 1
                
                # Save batch results
                if batch_scores:
                    self.save_batch_undervaluation_scores(batch_scores)
                    
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(all_data) + batch_size - 1)//batch_size}")
            
            result = {
                'total_processed': len(all_data),
                'successful': successful,
                'failed': failed,
                'success_rate': successful / len(all_data) * 100 if all_data else 0
            }
            
            logger.info(f"Batch analysis complete: {successful}/{len(all_data)} successful ({result['success_rate']:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error in calculate_all_scores_batch: {e}")
            raise
    
    def calculate_scorecard_from_data(self, data: Dict, config) -> Optional[Dict]:
        """Calculate undervaluation scorecard from pre-fetched data"""
        try:
            symbol = data['symbol']
            
            # Relative Score Calculation (in-lined for batch processing)
            growth_rates = self.get_historical_growth_rates(symbol)
            data.update(growth_rates)
            ratios = self.calculate_financial_ratios(data)
            if not ratios:
                return None
            
            sector_avg = self.get_sector_averages(data.get('sector', 'Unknown'))
            
            scores = {}
            if 'pe_ratio' in ratios and ratios['pe_ratio'] > 0:
                pe_score = max(0, min(100, 100 * (sector_avg['avg_pe'] / ratios['pe_ratio'])))
                scores['pe_score'] = pe_score
            if 'pb_ratio' in ratios and ratios['pb_ratio'] > 0:
                pb_score = max(0, min(100, 100 * (sector_avg['avg_pb'] / ratios['pb_ratio'])))
                scores['pb_score'] = pb_score
            if 'ps_ratio' in ratios and ratios['ps_ratio'] > 0:
                ps_score = max(0, min(100, 100 * (sector_avg['avg_ps'] / ratios['ps_ratio'])))
                scores['ps_score'] = ps_score
            if 'peg_ratio' in ratios and ratios['peg_ratio'] > 0:
                peg = ratios['peg_ratio']
                if peg <= 1.0:
                    peg_score = 100
                else:
                    peg_score = max(0, 100 - (peg - 1.0) * 50)
                scores['peg_score'] = peg_score
            if 'roe' in ratios:
                roe_score = max(0, min(100, (ratios['roe'] / sector_avg['avg_roe']) * 100))
                scores['roe_score'] = roe_score
            if 'roa' in ratios:
                roa_score = max(0, min(100, (ratios['roa'] / sector_avg['avg_roa']) * 100))
                scores['roa_score'] = roa_score
            if 'current_ratio' in ratios:
                cr = ratios['current_ratio']
                if 1.5 <= cr <= 2.5:
                    cr_score = 100
                elif cr < 1.0:
                    cr_score = 0
                elif cr < 1.5:
                    cr_score = 50 + (cr - 1.0) * 100
                else:
                    cr_score = max(0, 100 - (cr - 2.5) * 20)
                scores['current_ratio_score'] = cr_score
            if 'debt_to_equity' in ratios:
                de_score = max(0, min(100, 100 * (1 - ratios['debt_to_equity'] / 2)))
                scores['debt_equity_score'] = de_score
            if 'fcf_yield' in ratios:
                fcf_score = max(0, min(100, ratios['fcf_yield'] * 1000))
                scores['fcf_score'] = fcf_score

            value_scores = [scores.get('pe_score'), scores.get('pb_score'), scores.get('ps_score'), scores.get('peg_score')]
            quality_scores = [scores.get('roe_score'), scores.get('roa_score')]
            strength_scores = [scores.get('current_ratio_score'), scores.get('debt_equity_score')]
            cash_scores = [scores.get('fcf_score')]

            value_avg = sum(s for s in value_scores if s is not None) / len([s for s in value_scores if s is not None]) if any(s is not None for s in value_scores) else 0
            quality_avg = sum(s for s in quality_scores if s is not None) / len([s for s in quality_scores if s is not None]) if any(s is not None for s in quality_scores) else 0
            strength_avg = sum(s for s in strength_scores if s is not None) / len([s for s in strength_scores if s is not None]) if any(s is not None for s in strength_scores) else 0
            cash_avg = sum(s for s in cash_scores if s is not None) / len([s for s in cash_scores if s is not None]) if any(s is not None for s in cash_scores) else 0

            final_score = (value_avg * 0.4 + quality_avg * 0.3 + strength_avg * 0.2 + cash_avg * 0.1)
            
            data_points = len([s for s in scores.values() if s is not None])
            if data_points >= 6:
                data_quality = 'high'
            elif data_points >= 3:
                data_quality = 'medium'
            else:
                data_quality = 'low'

            relative_score_data = {
                'symbol': symbol,
                'undervaluation_score': round(final_score, 1),
                'valuation_score': round(value_avg, 1),
                'quality_score': round(quality_avg, 1),
                'strength_score': round(strength_avg, 1),
                'risk_score': round(100 - strength_avg, 1),
                'data_quality': data_quality,
                'sector': data.get('sector'),
                'price': data.get('price'),
                'market_cap': data.get('market_cap'),
                'ratios': ratios,
                'individual_scores': scores
            }
            # End of in-lined relative score calculation

            # DDM and DCF
            risk_free_rate = config.VALUATION_CONFIG['risk_free_rate']
            equity_risk_premium = config.VALUATION_CONFIG['equity_risk_premium']
            beta = data.get('beta')

            ddm_value = None
            if beta:
                ddm_value = self.calculate_ddm_value(symbol, beta, risk_free_rate, equity_risk_premium)

            dcf_value = self.calculate_dcf_value(symbol, risk_free_rate, equity_risk_premium)

            # Synthesize Results
            final_intrinsic_value = None
            weights = {'dcf': 0.5, 'ddm': 0.2, 'relative': 0.3}
            values = []
            if dcf_value:
                values.append(dcf_value * weights['dcf'])
            if ddm_value:
                values.append(ddm_value * weights['ddm'])
            
            if relative_score_data.get('undervaluation_score'):
                relative_value = relative_score_data['price'] * (1 + (relative_score_data['undervaluation_score'] - 50) / 100)
                values.append(relative_value * weights['relative'])

            if values:
                final_intrinsic_value = sum(values) / sum(weights[k] for k, v in {'dcf': dcf_value, 'ddm': ddm_value, 'relative': relative_value}.items() if v is not None)

            # Combine all data
            scorecard = {
                **relative_score_data,
                'dcf_value': dcf_value,
                'ddm_value': ddm_value,
                'final_intrinsic_value': final_intrinsic_value,
            }
            
            return scorecard
            
        except Exception as e:
            logger.error(f"Error calculating scorecard for {data.get('symbol', 'unknown')}: {e}")
            return None
    
    def _convert_numpy_types(self, value):
        """Convert numpy types to Python native types for database compatibility"""
        if isinstance(value, np.floating):
            return float(value)
        elif isinstance(value, np.integer):
            return int(value)
        elif hasattr(value, 'item'):  # Other numpy scalars
            return value.item()
        return value

    def save_batch_undervaluation_scores(self, batch_scores: List[Dict]):
        """Save multiple undervaluation scores in a single transaction"""
        try:
            with self.db.engine.connect() as conn:
                # Use individual INSERT statements since there's no unique constraint
                for score in batch_scores:
                    # First, try to update existing record
                    result = conn.execute(text("""
                        UPDATE undervaluation_scores 
                        SET sector = :sector,
                            undervaluation_score = :undervaluation_score,
                            valuation_score = :valuation_score,
                            quality_score = :quality_score,
                            strength_score = :strength_score,
                            risk_score = :risk_score,
                            data_quality = :data_quality,
                            price = :price,
                            mktcap = :mktcap,
                            updated_at = CURRENT_TIMESTAMP,
                            dcf_value = :dcf_value,
                            ddm_value = :ddm_value,
                            final_intrinsic_value = :final_intrinsic_value
                        WHERE symbol = :symbol
                    """), {
                        'symbol': score['symbol'],
                        'sector': score['sector'],
                        'undervaluation_score': score['undervaluation_score'],
                        'valuation_score': score['valuation_score'],
                        'quality_score': score['quality_score'],
                        'strength_score': score['strength_score'],
                        'risk_score': score['risk_score'],
                        'data_quality': score['data_quality'],
                        'price': score['price'],
                        'mktcap': score['market_cap'],
                        'dcf_value': self._convert_numpy_types(score.get('dcf_value')),
                        'ddm_value': self._convert_numpy_types(score.get('ddm_value')),
                        'final_intrinsic_value': self._convert_numpy_types(score.get('final_intrinsic_value')),
                    })
                    
                    # If no rows were updated, insert new record
                    if result.rowcount == 0:
                        conn.execute(text("""
                            INSERT INTO undervaluation_scores 
                            (symbol, sector, undervaluation_score, valuation_score, quality_score, 
                             strength_score, risk_score, data_quality, price, mktcap, updated_at,
                             dcf_value, ddm_value, final_intrinsic_value)
                            VALUES (:symbol, :sector, :undervaluation_score, :valuation_score, :quality_score, 
                                    :strength_score, :risk_score, :data_quality, :price, :mktcap, CURRENT_TIMESTAMP,
                                    :dcf_value, :ddm_value, :final_intrinsic_value)
                        """), {
                            'symbol': score['symbol'],
                            'sector': score['sector'],
                            'undervaluation_score': score['undervaluation_score'],
                            'valuation_score': score['valuation_score'],
                            'quality_score': score['quality_score'],
                            'strength_score': score['strength_score'],
                            'risk_score': score['risk_score'],
                            'data_quality': score['data_quality'],
                            'price': score['price'],
                            'mktcap': score['market_cap'],
                            'dcf_value': self._convert_numpy_types(score.get('dcf_value')),
                            'ddm_value': self._convert_numpy_types(score.get('ddm_value')),
                            'final_intrinsic_value': self._convert_numpy_types(score.get('final_intrinsic_value')),
                        })
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving batch undervaluation scores: {e}")
            raise
    
    def score_pe_ratio(self, pe_ratio: Optional[float]) -> Optional[float]:
        """Score PE ratio (lower is better)"""
        if pe_ratio is None or pe_ratio <= 0:
            return None
        return max(0, min(100, 100 * (1 - (pe_ratio - 5) / 45)))  # 5-50 PE range
    
    def score_pb_ratio(self, pb_ratio: Optional[float]) -> Optional[float]:
        """Score PB ratio (lower is better)"""
        if pb_ratio is None or pb_ratio <= 0:
            return None
        return max(0, min(100, 100 * (1 - (pb_ratio - 0.5) / 9.5)))  # 0.5-10 PB range
    
    def score_ps_ratio(self, ps_ratio: Optional[float]) -> Optional[float]:
        """Score PS ratio (lower is better)"""
        if ps_ratio is None or ps_ratio <= 0:
            return None
        return max(0, min(100, 100 * (1 - (ps_ratio - 0.5) / 19.5)))  # 0.5-20 PS range
    
    def score_roe(self, roe: Optional[float]) -> Optional[float]:
        """Score ROE (higher is better)"""
        if roe is None:
            return None
        return max(0, min(100, roe * 500))  # 20% ROE = 100 score
    
    def score_roa(self, roa: Optional[float]) -> Optional[float]:
        """Score ROA (higher is better)"""
        if roa is None:
            return None
        return max(0, min(100, roa * 1000))  # 10% ROA = 100 score
    
    def score_debt_to_equity(self, debt_to_equity: Optional[float]) -> Optional[float]:
        """Score debt-to-equity ratio (lower is better)"""
        if debt_to_equity is None:
            return None
        return max(0, min(100, 100 * (1 - debt_to_equity / 2)))  # 0-200% range
    
    def score_cash_flow_yield(self, cf_yield: Optional[float]) -> Optional[float]:
        """Score cash flow yield (higher is better)"""
        if cf_yield is None:
            return None
        return max(0, min(100, cf_yield * 1000))  # 10% CF yield = 100 score
    
    def calculate_all_scores(self, limit: Optional[int] = None) -> Dict:
        """Calculate undervaluation scores for all companies with sufficient data (legacy method)"""
        logger.info("Starting Yahoo Finance-based undervaluation analysis (legacy method)")
        
        try:
            # Get all symbols with profile data
            with self.db.engine.connect() as conn:
                query = """
                    SELECT symbol FROM company_profiles 
                    WHERE price IS NOT NULL AND mktcap IS NOT NULL
                    ORDER BY symbol
                """
                if limit:
                    query += f" LIMIT {limit}"
                    
                symbols = [row[0] for row in conn.execute(text(query)).fetchall()]
            
            logger.info(f"Processing {len(symbols)} companies")
            
            successful = 0
            failed = 0
            
            for symbol in symbols:
                try:
                    score_data = self.get_valuation_scorecard(symbol)
                    if score_data:
                        self.save_undervaluation_score(score_data)
                        successful += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process {symbol}: {e}")
                    failed += 1
            
            result = {
                'total_processed': len(symbols),
                'successful': successful,
                'failed': failed,
                'success_rate': successful / len(symbols) * 100 if symbols else 0
            }
            
            logger.info(f"Analysis complete: {successful}/{len(symbols)} successful ({result['success_rate']:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error in calculate_all_scores: {e}")
            raise

def main():
    """Run the Yahoo Finance undervaluation calculator"""
    calculator = YFinanceUndervaluationCalculator()
    
    print("🚀 Starting Yahoo Finance-based undervaluation analysis...")
    result = calculator.calculate_all_scores_batch()
    
    print("✅ Analysis complete!")
    print(f"📊 Results: {result['successful']}/{result['total_processed']} companies processed ({result['success_rate']:.1f}% success rate)")
    
    # Show top results
    try:
        with calculator.db.engine.connect() as conn:
            top_stocks = conn.execute(text("""
                SELECT symbol, undervaluation_score, data_quality, sector
                FROM undervaluation_scores 
                WHERE undervaluation_score IS NOT NULL 
                ORDER BY undervaluation_score DESC 
                LIMIT 10
            """)).fetchall()
            
            print("\n🏆 Top 10 undervalued stocks:")
            for i, stock in enumerate(top_stocks, 1):
                print(f"   {i:2d}. {stock.symbol:4s}: Score={stock.undervaluation_score:5.1f}, Quality={stock.data_quality}, {stock.sector}")
                
    except Exception as e:
        print(f"Error showing results: {e}")

if __name__ == "__main__":
    main()