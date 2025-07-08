#!/usr/bin/env python3
"""
Yahoo Finance-based Undervaluation Calculator
Calculates undervaluation scores using data already collected from Yahoo Finance
"""

from typing import Dict, List, Optional
from database import DatabaseManager
from sqlalchemy import text
from logging_config import get_logger

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
                # Get company profile data
                profile_data = conn.execute(text("""
                    SELECT symbol, companyname, price, mktcap, sector, industry
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
                
                # Combine all data
                result = {
                    'symbol': profile_data.symbol,
                    'company_name': profile_data.companyname,
                    'price': profile_data.price,
                    'market_cap': profile_data.mktcap,
                    'sector': profile_data.sector,
                    'industry': profile_data.industry
                }
                
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
            
            # Price-to-Book ratio
            if data.get('market_cap') and data.get('total_equity') and data.get('total_equity') > 0:
                ratios['pb_ratio'] = data['market_cap'] / data['total_equity']
            
            # Price-to-Sales ratio
            if data.get('market_cap') and data.get('revenue') and data.get('revenue') > 0:
                ratios['ps_ratio'] = data['market_cap'] / data['revenue']
            
            # Return on Equity
            if data.get('net_income') and data.get('total_equity') and data.get('total_equity') > 0:
                ratios['roe'] = data['net_income'] / data['total_equity']
            
            # Return on Assets
            if data.get('net_income') and data.get('total_assets') and data.get('total_assets') > 0:
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
    
    def calculate_undervaluation_score(self, symbol: str) -> Optional[Dict]:
        """Calculate undervaluation score for a single symbol"""
        try:
            # Get financial data
            data = self.get_financial_data(symbol)
            if not data or not data.get('price') or not data.get('market_cap'):
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Calculate ratios
            ratios = self.calculate_financial_ratios(data)
            if not ratios:
                logger.warning(f"Could not calculate ratios for {symbol}")
                return None
            
            # Get sector averages (for future use)
            # sector_avg = self.get_sector_averages(data.get('sector', 'Unknown'))
            
            # Calculate individual scores (0-100 scale)
            scores = {}
            
            # Value Score (lower ratios = higher score)
            if 'pe_ratio' in ratios and ratios['pe_ratio'] > 0:
                pe_score = max(0, min(100, 100 * (1 - (ratios['pe_ratio'] - 5) / 45)))  # 5-50 PE range
                scores['pe_score'] = pe_score
            
            if 'pb_ratio' in ratios and ratios['pb_ratio'] > 0:
                pb_score = max(0, min(100, 100 * (1 - (ratios['pb_ratio'] - 0.5) / 9.5)))  # 0.5-10 PB range
                scores['pb_score'] = pb_score
            
            if 'ps_ratio' in ratios and ratios['ps_ratio'] > 0:
                ps_score = max(0, min(100, 100 * (1 - (ratios['ps_ratio'] - 0.5) / 19.5)))  # 0.5-20 PS range
                scores['ps_score'] = ps_score
            
            # Quality Score (higher profitability = higher score)
            if 'roe' in ratios:
                roe_score = max(0, min(100, ratios['roe'] * 500))  # 20% ROE = 100 score
                scores['roe_score'] = roe_score
            
            if 'roa' in ratios:
                roa_score = max(0, min(100, ratios['roa'] * 1000))  # 10% ROA = 100 score
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
            value_scores = [scores.get('pe_score'), scores.get('pb_score'), scores.get('ps_score')]
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
    
    def save_undervaluation_score(self, score_data: Dict):
        """Save undervaluation score to database"""
        try:
            with self.db.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO undervaluation_scores 
                    (symbol, sector, undervaluation_score, valuation_score, quality_score, 
                     strength_score, risk_score, data_quality, price, mktcap, updated_at)
                    VALUES (:symbol, :sector, :undervaluation_score, :valuation_score, :quality_score, 
                            :strength_score, :risk_score, :data_quality, :price, :mktcap, CURRENT_TIMESTAMP)
                    ON CONFLICT (symbol) DO UPDATE SET
                    sector = EXCLUDED.sector,
                    undervaluation_score = EXCLUDED.undervaluation_score,
                    valuation_score = EXCLUDED.valuation_score,
                    quality_score = EXCLUDED.quality_score,
                    strength_score = EXCLUDED.strength_score,
                    risk_score = EXCLUDED.risk_score,
                    data_quality = EXCLUDED.data_quality,
                    price = EXCLUDED.price,
                    mktcap = EXCLUDED.mktcap,
                    updated_at = CURRENT_TIMESTAMP
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
                    'mktcap': score_data['market_cap']
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
            # Get all symbols and their data in a single query
            with self.db.engine.connect() as conn:
                query = """
                    SELECT 
                        cp.symbol,
                        cp.price,
                        cp.mktcap,
                        cp.sector,
                        -- Income statement data (latest)
                        i.total_revenue,
                        i.net_income,
                        i.basic_eps,
                        i.shares_outstanding,
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
                        SELECT DISTINCT ON (symbol) symbol, total_revenue, net_income, basic_eps, shares_outstanding
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
                        data = {
                            'symbol': row.symbol,
                            'price': row.price,
                            'market_cap': row.mktcap,
                            'sector': row.sector,
                            'total_revenue': row.total_revenue,
                            'net_income': row.net_income,
                            'basic_eps': row.basic_eps,
                            'shares_outstanding': row.shares_outstanding,
                            'total_assets': row.total_assets,
                            'total_equity': row.total_equity,
                            'total_debt': row.total_debt,
                            'cash_and_equivalents': row.cash_and_equivalents,
                            'operating_cash_flow': row.operating_cash_flow,
                            'free_cash_flow': row.free_cash_flow
                        }
                        
                        score_data = self.calculate_score_from_data(data)
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
    
    def calculate_score_from_data(self, data: Dict) -> Optional[Dict]:
        """Calculate undervaluation score from pre-fetched data"""
        try:
            symbol = data['symbol']
            
            # Calculate ratios using vectorized operations where possible
            price = data.get('price', 0)
            market_cap = data.get('market_cap', 0)
            net_income = data.get('net_income', 0)
            total_revenue = data.get('total_revenue', 0)
            total_equity = data.get('total_equity', 0)
            total_assets = data.get('total_assets', 0)
            total_debt = data.get('total_debt', 0)
            operating_cash_flow = data.get('operating_cash_flow', 0)
            free_cash_flow = data.get('free_cash_flow', 0)
            
            # Calculate ratios
            ratios = {}
            ratios['pe_ratio'] = market_cap / net_income if net_income and net_income > 0 else None
            ratios['pb_ratio'] = market_cap / total_equity if total_equity and total_equity > 0 else None
            ratios['ps_ratio'] = market_cap / total_revenue if total_revenue and total_revenue > 0 else None
            ratios['roe'] = net_income / total_equity if total_equity and total_equity > 0 else None
            ratios['roa'] = net_income / total_assets if total_assets and total_assets > 0 else None
            ratios['debt_to_equity'] = total_debt / total_equity if total_equity and total_equity > 0 else None
            ratios['ocf_yield'] = operating_cash_flow / market_cap if market_cap and market_cap > 0 else None
            ratios['fcf_yield'] = free_cash_flow / market_cap if market_cap and market_cap > 0 else None
            
            # Calculate scores using existing scoring logic
            scores = {}
            
            # Valuation Scores (Lower is better)
            scores['pe_score'] = self.score_pe_ratio(ratios.get('pe_ratio'))
            scores['pb_score'] = self.score_pb_ratio(ratios.get('pb_ratio'))
            scores['ps_score'] = self.score_ps_ratio(ratios.get('ps_ratio'))
            
            # Quality Scores (Higher is better)
            scores['roe_score'] = self.score_roe(ratios.get('roe'))
            scores['roa_score'] = self.score_roa(ratios.get('roa'))
            
            # Strength Scores (Lower debt is better)
            scores['debt_score'] = self.score_debt_to_equity(ratios.get('debt_to_equity'))
            
            # Cash Flow Scores (Higher is better)
            scores['ocf_score'] = self.score_cash_flow_yield(ratios.get('ocf_yield'))
            scores['fcf_score'] = self.score_cash_flow_yield(ratios.get('fcf_yield'))
            
            # Calculate component averages
            valuation_scores = [s for s in [scores['pe_score'], scores['pb_score'], scores['ps_score']] if s is not None]
            quality_scores = [s for s in [scores['roe_score'], scores['roa_score']] if s is not None]
            strength_scores = [s for s in [scores['debt_score']] if s is not None]
            cash_flow_scores = [s for s in [scores['ocf_score'], scores['fcf_score']] if s is not None]
            
            # Determine data quality
            total_metrics = len([r for r in ratios.values() if r is not None])
            if total_metrics >= 6:
                data_quality = "high"
            elif total_metrics >= 4:
                data_quality = "medium"
            else:
                data_quality = "low"
            
            # Calculate weighted final score
            value_avg = sum(valuation_scores) / len(valuation_scores) if valuation_scores else 50
            quality_avg = sum(quality_scores) / len(quality_scores) if quality_scores else 50
            strength_avg = sum(strength_scores) / len(strength_scores) if strength_scores else 50
            cash_flow_avg = sum(cash_flow_scores) / len(cash_flow_scores) if cash_flow_scores else 50
            
            # Weighted average
            final_score = (value_avg * 0.4 + quality_avg * 0.3 + strength_avg * 0.2 + cash_flow_avg * 0.1)
            
            return {
                'symbol': symbol,
                'undervaluation_score': round(final_score, 1),
                'valuation_score': round(value_avg, 1),
                'quality_score': round(quality_avg, 1),
                'strength_score': round(strength_avg, 1),
                'risk_score': round(100 - strength_avg, 1),
                'data_quality': data_quality,
                'sector': data.get('sector'),
                'price': price,
                'market_cap': market_cap,
            }
            
        except Exception as e:
            logger.error(f"Error calculating score for {data.get('symbol', 'unknown')}: {e}")
            return None
    
    def save_batch_undervaluation_scores(self, batch_scores: List[Dict]):
        """Save multiple undervaluation scores in a single transaction"""
        try:
            with self.db.engine.connect() as conn:
                # Use bulk insert for better performance
                conn.execute(text("""
                    INSERT INTO undervaluation_scores 
                    (symbol, sector, undervaluation_score, valuation_score, quality_score, 
                     strength_score, risk_score, data_quality, price, mktcap, updated_at)
                    VALUES 
                    """ + ",".join([
                        "(:symbol_{i}, :sector_{i}, :undervaluation_score_{i}, :valuation_score_{i}, :quality_score_{i}, "
                        ":strength_score_{i}, :risk_score_{i}, :data_quality_{i}, :price_{i}, :mktcap_{i}, CURRENT_TIMESTAMP)".format(i=i)
                        for i in range(len(batch_scores))
                    ]) + """
                    ON CONFLICT (symbol) DO UPDATE SET
                    sector = EXCLUDED.sector,
                    undervaluation_score = EXCLUDED.undervaluation_score,
                    valuation_score = EXCLUDED.valuation_score,
                    quality_score = EXCLUDED.quality_score,
                    strength_score = EXCLUDED.strength_score,
                    risk_score = EXCLUDED.risk_score,
                    data_quality = EXCLUDED.data_quality,
                    price = EXCLUDED.price,
                    mktcap = EXCLUDED.mktcap,
                    updated_at = CURRENT_TIMESTAMP
                """), {
                    **{f'symbol_{i}': score['symbol'] for i, score in enumerate(batch_scores)},
                    **{f'sector_{i}': score['sector'] for i, score in enumerate(batch_scores)},
                    **{f'undervaluation_score_{i}': score['undervaluation_score'] for i, score in enumerate(batch_scores)},
                    **{f'valuation_score_{i}': score['valuation_score'] for i, score in enumerate(batch_scores)},
                    **{f'quality_score_{i}': score['quality_score'] for i, score in enumerate(batch_scores)},
                    **{f'strength_score_{i}': score['strength_score'] for i, score in enumerate(batch_scores)},
                    **{f'risk_score_{i}': score['risk_score'] for i, score in enumerate(batch_scores)},
                    **{f'data_quality_{i}': score['data_quality'] for i, score in enumerate(batch_scores)},
                    **{f'price_{i}': score['price'] for i, score in enumerate(batch_scores)},
                    **{f'mktcap_{i}': score['market_cap'] for i, score in enumerate(batch_scores)},
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
                    score_data = self.calculate_undervaluation_score(symbol)
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
    result = calculator.calculate_all_scores()
    
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