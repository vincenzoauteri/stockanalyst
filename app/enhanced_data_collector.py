#!/usr/bin/env python3
"""
Enhanced Data Collector for Critical Valuation Metrics
Collects missing data from Yahoo Finance to improve valuation quality
"""

import yfinance as yf
from database import DatabaseManager
from sqlalchemy import text
from logging_config import get_logger
import time
from typing import Dict, List, Optional

logger = get_logger(__name__)

class EnhancedDataCollector:
    """Collect critical missing data from Yahoo Finance for better valuations"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.delay_between_requests = 0.5  # 0.5 second delay to improve efficiency
    
    def get_enhanced_metrics(self, symbol: str) -> Optional[Dict]:
        """Get enhanced financial metrics from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract critical missing data
            enhanced_data = {
                'symbol': symbol,
                'beta': info.get('beta'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'book_value': info.get('bookValue'),
                'peg_ratio': info.get('pegRatio'),
                'forward_pe': info.get('forwardPE'),
                'enterprise_value': info.get('enterpriseValue'),
                'debt_to_equity_ratio': info.get('debtToEquity'),
                'return_on_equity': info.get('returnOnEquity'),
                'return_on_assets': info.get('returnOnAssets'),
                'operating_cashflow': info.get('operatingCashflow'),
                'free_cashflow': info.get('freeCashflow'),
            }
            
            # Convert percentage values to decimals where needed
            if enhanced_data['return_on_equity']:
                enhanced_data['return_on_equity'] = float(enhanced_data['return_on_equity'])
            if enhanced_data['return_on_assets']:
                enhanced_data['return_on_assets'] = float(enhanced_data['return_on_assets'])
            if enhanced_data['debt_to_equity_ratio']:
                enhanced_data['debt_to_equity_ratio'] = float(enhanced_data['debt_to_equity_ratio']) / 100.0
            
            logger.debug(f"Retrieved enhanced metrics for {symbol}")
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error getting enhanced metrics for {symbol}: {e}")
            return None
    
    def update_company_profile_enhanced(self, enhanced_data: Dict) -> bool:
        """Update company profile with enhanced metrics"""
        try:
            with self.db.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE company_profiles 
                    SET beta = :beta,
                        shares_outstanding = :shares_outstanding,
                        book_value = :book_value,
                        peg_ratio = :peg_ratio,
                        forward_pe = :forward_pe,
                        enterprise_value = :enterprise_value,
                        debt_to_equity_ratio = :debt_to_equity_ratio,
                        return_on_equity = :return_on_equity,
                        return_on_assets = :return_on_assets,
                        operating_cashflow = :operating_cashflow,
                        free_cashflow = :free_cashflow,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE symbol = :symbol
                """), enhanced_data)
                conn.commit()
                
            logger.debug(f"Updated enhanced metrics for {enhanced_data['symbol']}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating enhanced metrics for {enhanced_data['symbol']}: {e}")
            return False
    
    def update_income_statement_shares(self, symbol: str, shares_outstanding: int) -> bool:
        """Update income statements with shares outstanding data"""
        try:
            with self.db.engine.connect() as conn:
                # Update the most recent income statement record
                conn.execute(text("""
                    UPDATE income_statements 
                    SET shares_outstanding = :shares_outstanding
                    WHERE symbol = :symbol
                    AND id = (
                        SELECT id FROM income_statements 
                        WHERE symbol = :symbol 
                        ORDER BY period_ending DESC 
                        LIMIT 1
                    )
                """), {
                    'symbol': symbol,
                    'shares_outstanding': shares_outstanding
                })
                conn.commit()
                
            logger.debug(f"Updated shares outstanding for {symbol}: {shares_outstanding}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating shares outstanding for {symbol}: {e}")
            return False
    
    def collect_enhanced_data_for_symbol(self, symbol: str) -> bool:
        """Collect and store enhanced data for a single symbol"""
        logger.info(f"Collecting enhanced data for {symbol}")
        
        enhanced_data = self.get_enhanced_metrics(symbol)
        if not enhanced_data:
            return False
        
        # Update company profile
        profile_success = self.update_company_profile_enhanced(enhanced_data)
        
        # Update income statements if shares outstanding available
        shares_success = True
        if enhanced_data.get('shares_outstanding'):
            shares_success = self.update_income_statement_shares(
                symbol, enhanced_data['shares_outstanding']
            )
        
        return profile_success and shares_success
    
    def collect_enhanced_data_batch(self, symbols: List[str] = None, limit: int = None) -> Dict:
        """Collect enhanced data for multiple symbols"""
        if not symbols:
            # Get all symbols from company_profiles
            with self.db.engine.connect() as conn:
                result = conn.execute(text("SELECT symbol FROM company_profiles ORDER BY symbol"))
                symbols = [row[0] for row in result.fetchall()]
        
        if limit:
            symbols = symbols[:limit]
        
        logger.info(f"Starting enhanced data collection for {len(symbols)} symbols")
        
        successful = 0
        failed = 0
        
        for i, symbol in enumerate(symbols, 1):
            try:
                success = self.collect_enhanced_data_for_symbol(symbol)
                if success:
                    successful += 1
                    logger.info(f"✅ {symbol} ({i}/{len(symbols)}) - Enhanced data collected")
                else:
                    failed += 1
                    logger.warning(f"❌ {symbol} ({i}/{len(symbols)}) - Failed to collect data")
                
                # Rate limiting
                if i < len(symbols):
                    time.sleep(self.delay_between_requests)
                    
            except Exception as e:
                failed += 1
                logger.error(f"❌ {symbol} ({i}/{len(symbols)}) - Error: {e}")
        
        result = {
            'total_processed': len(symbols),
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / len(symbols)) * 100 if symbols else 0
        }
        
        logger.info(f"Enhanced data collection complete: {successful}/{len(symbols)} successful ({result['success_rate']:.1f}%)")
        return result
    
    def check_data_coverage(self) -> Dict:
        """Check current coverage of enhanced data"""
        with self.db.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_companies,
                    COUNT(CASE WHEN beta IS NOT NULL THEN 1 END) as has_beta,
                    COUNT(CASE WHEN shares_outstanding IS NOT NULL THEN 1 END) as has_shares,
                    COUNT(CASE WHEN book_value IS NOT NULL THEN 1 END) as has_book_value,
                    COUNT(CASE WHEN peg_ratio IS NOT NULL THEN 1 END) as has_peg,
                    COUNT(CASE WHEN forward_pe IS NOT NULL THEN 1 END) as has_forward_pe,
                    COUNT(CASE WHEN return_on_equity IS NOT NULL THEN 1 END) as has_roe,
                    COUNT(CASE WHEN return_on_assets IS NOT NULL THEN 1 END) as has_roa
                FROM company_profiles
            """)).fetchone()
        
        coverage = {
            'total_companies': result.total_companies,
            'beta_coverage': f"{result.has_beta}/{result.total_companies} ({result.has_beta/result.total_companies*100:.1f}%)",
            'shares_coverage': f"{result.has_shares}/{result.total_companies} ({result.has_shares/result.total_companies*100:.1f}%)",
            'book_value_coverage': f"{result.has_book_value}/{result.total_companies} ({result.has_book_value/result.total_companies*100:.1f}%)",
            'peg_coverage': f"{result.has_peg}/{result.total_companies} ({result.has_peg/result.total_companies*100:.1f}%)",
            'forward_pe_coverage': f"{result.has_forward_pe}/{result.total_companies} ({result.has_forward_pe/result.total_companies*100:.1f}%)",
            'roe_coverage': f"{result.has_roe}/{result.total_companies} ({result.has_roe/result.total_companies*100:.1f}%)",
            'roa_coverage': f"{result.has_roa}/{result.total_companies} ({result.has_roa/result.total_companies*100:.1f}%)",
        }
        
        return coverage

def main():
    """Run enhanced data collection"""
    collector = EnhancedDataCollector()
    
    print("🔍 Checking current data coverage...")
    coverage_before = collector.check_data_coverage()
    print("📊 Current Coverage:")
    for metric, value in coverage_before.items():
        if metric != 'total_companies':
            print(f"   {metric}: {value}")
    
    print(f"\n🚀 Starting enhanced data collection for {coverage_before['total_companies']} companies...")
    
    # Collect data for all companies
    result = collector.collect_enhanced_data_batch()
    
    print(f"\n✅ Collection complete!")
    print(f"📈 Results: {result['successful']}/{result['total_processed']} companies updated ({result['success_rate']:.1f}% success rate)")
    
    print(f"\n🔍 Checking updated data coverage...")
    coverage_after = collector.check_data_coverage()
    print("📊 Updated Coverage:")
    for metric, value in coverage_after.items():
        if metric != 'total_companies':
            print(f"   {metric}: {value}")

if __name__ == "__main__":
    main()