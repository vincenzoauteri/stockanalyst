import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from database import DatabaseManager
from fmp_client import FMPClient
from sqlalchemy import text
import warnings
import json
import os
from datetime import datetime
import logging

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UndervaluationAnalyzer:
    def __init__(self, cache_duration_hours: int = 24):
        self.db = DatabaseManager()
        self.client = FMPClient()
        self.cache_file = 'fundamentals_cache.json'
        self.cache_duration_hours = cache_duration_hours
        
        # Initialize cache if it doesn't exist
        self._init_cache()
        
    def calculate_sector_stats(self, df: pd.DataFrame, metric_cols: List[str]) -> Dict:
        """Calculate sector averages and standard deviations for key metrics"""
        sector_stats = {}
        
        for sector in df['sector'].unique():
            if pd.isna(sector):
                continue
                
            sector_data = df[df['sector'] == sector]
            sector_stats[sector] = {}
            
            for col in metric_cols:
                if col in sector_data.columns:
                    values = pd.to_numeric(sector_data[col], errors='coerce').dropna()
                    if len(values) > 0:
                        sector_stats[sector][col] = {
                            'mean': values.mean(),
                            'median': values.median(),
                            'std': values.std() if len(values) > 1 else 1.0
                        }
        
        return sector_stats
    
    def _init_cache(self):
        """Initialize cache file if it doesn't exist"""
        if not os.path.exists(self.cache_file):
            self._save_cache({})
    
    def _load_cache(self) -> Dict:
        """Load cached fundamentals data"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Cache file not found or corrupted, starting fresh")
            return {}
    
    def _save_cache(self, cache_data: Dict):
        """Save fundamentals data to cache"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _is_cache_valid(self, timestamp_str: str) -> bool:
        """Check if cached data is still valid based on timestamp"""
        try:
            cache_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            current_time = datetime.now()
            age_hours = (current_time - cache_time).total_seconds() / 3600
            return age_hours < self.cache_duration_hours
        except Exception:
            return False
    
    def _get_cached_fundamentals(self, symbol: str) -> Optional[Dict]:
        """Get cached fundamentals for a symbol if valid"""
        cache = self._load_cache()
        
        if symbol in cache:
            entry = cache[symbol]
            if 'timestamp' in entry and self._is_cache_valid(entry['timestamp']):
                logger.debug(f"Using cached fundamentals for {symbol}")
                return entry.get('data')
            else:
                logger.debug(f"Cache expired for {symbol}")
        
        return None
    
    def _cache_fundamentals(self, symbol: str, fundamentals_data: Dict):
        """Cache fundamentals data for a symbol"""
        cache = self._load_cache()
        
        cache[symbol] = {
            'data': fundamentals_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self._save_cache(cache)
        logger.debug(f"Cached fundamentals for {symbol}")
    
    def _cleanup_cache(self):
        """Remove expired entries from cache"""
        cache = self._load_cache()
        
        symbols_to_remove = []
        for symbol, entry in cache.items():
            if 'timestamp' not in entry or not self._is_cache_valid(entry['timestamp']):
                symbols_to_remove.append(symbol)
        
        for symbol in symbols_to_remove:
            del cache[symbol]
        
        if symbols_to_remove:
            self._save_cache(cache)
            logger.info(f"Cleaned up {len(symbols_to_remove)} expired cache entries")
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the fundamentals cache"""
        cache = self._load_cache()
        
        total_entries = len(cache)
        valid_entries = 0
        expired_entries = 0
        
        for entry in cache.values():
            if 'timestamp' in entry and self._is_cache_valid(entry['timestamp']):
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_file': self.cache_file,
            'cache_duration_hours': self.cache_duration_hours
        }
    
    def clear_cache(self):
        """Clear all cached fundamentals data"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("Fundamentals cache cleared")
            self._init_cache()
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def score_valuation_metrics(self, stock: pd.Series, sector_stats: Dict, sector: str) -> float:
        """Score valuation metrics relative to sector (40% of total score)"""
        if sector not in sector_stats:
            return 0.0
            
        valuation_metrics = ['pe_ratio', 'pb_ratio', 'price_to_sales']
        scores = []
        
        for metric in valuation_metrics:
            if metric in sector_stats[sector]:
                stock_value = pd.to_numeric(stock.get(metric), errors='coerce')
                
                if pd.notna(stock_value) and stock_value > 0:
                    sector_avg = sector_stats[sector][metric]['mean']
                    sector_std = sector_stats[sector][metric]['std']
                    
                    if sector_std > 0:
                        # Lower ratios are better (more undervalued)
                        z_score = (sector_avg - stock_value) / sector_std
                        # Convert to 0-100 scale, capped at reasonable bounds
                        normalized_score = max(0, min(100, 50 + (z_score * 10)))
                        scores.append(normalized_score)
        
        return np.mean(scores) if scores else 0.0
    
    def score_quality_metrics(self, stock: pd.Series, sector_stats: Dict, sector: str) -> float:
        """Score quality metrics relative to sector (30% of total score)"""
        if sector not in sector_stats:
            return 0.0
            
        quality_metrics = {
            'roe': 0.25,
            'net_profit_margin': 0.25,
            'current_ratio': 0.25,
            'free_cash_flow_yield': 0.25
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric, weight in quality_metrics.items():
            if metric in sector_stats[sector]:
                stock_value = pd.to_numeric(stock.get(metric), errors='coerce')
                
                if pd.notna(stock_value):
                    sector_avg = sector_stats[sector][metric]['mean']
                    sector_std = sector_stats[sector][metric]['std']
                    
                    if sector_std > 0:
                        # Higher values are better for quality metrics
                        z_score = (stock_value - sector_avg) / sector_std
                        normalized_score = max(0, min(100, 50 + (z_score * 10)))
                        weighted_score += normalized_score * weight
                        total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def score_financial_strength(self, stock: pd.Series, sector_stats: Dict, sector: str) -> float:
        """Score financial strength metrics (20% of total score)"""
        if sector not in sector_stats:
            return 0.0
            
        strength_metrics = {
            'debt_to_equity': 0.4,  # Lower is better
            'return_on_assets': 0.3,  # Higher is better
            'gross_profit_margin': 0.3  # Higher is better
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric, weight in strength_metrics.items():
            if metric in sector_stats[sector]:
                stock_value = pd.to_numeric(stock.get(metric), errors='coerce')
                
                if pd.notna(stock_value):
                    sector_avg = sector_stats[sector][metric]['mean']
                    sector_std = sector_stats[sector][metric]['std']
                    
                    if sector_std > 0:
                        if metric == 'debt_to_equity':
                            # Lower debt is better
                            z_score = (sector_avg - stock_value) / sector_std
                        else:
                            # Higher values are better
                            z_score = (stock_value - sector_avg) / sector_std
                            
                        normalized_score = max(0, min(100, 50 + (z_score * 10)))
                        weighted_score += normalized_score * weight
                        total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def score_risk_adjustment(self, stock: pd.Series) -> float:
        """Apply risk adjustments (10% of total score)"""
        beta = pd.to_numeric(stock.get('beta'), errors='coerce')
        mkt_cap = pd.to_numeric(stock.get('mktcap'), errors='coerce')
        
        risk_score = 50.0  # Neutral starting point
        
        # Beta adjustment
        if pd.notna(beta):
            if beta > 2.0:
                risk_score -= 20  # Penalize very high beta
            elif beta > 1.5:
                risk_score -= 10
            elif beta < 0.8:
                risk_score += 10  # Reward low beta
        
        # Market cap adjustment (slight preference for stability)
        if pd.notna(mkt_cap):
            if mkt_cap > 100_000_000_000:  # Large cap (>100B)
                risk_score += 5
            elif mkt_cap > 10_000_000_000:  # Mid cap (10B-100B)
                risk_score += 0
            else:  # Small cap
                risk_score -= 5
        
        return max(0, min(100, risk_score))
    
    def get_fundamentals_data(self, use_cache: bool = True, force_refresh: bool = False) -> pd.DataFrame:
        """Fetch all available fundamentals data from database and API with caching
        
        Args:
            use_cache: Whether to use cached data when available
            force_refresh: Whether to force refresh all data regardless of cache
        """
        logger.info("Fetching fundamentals data for undervaluation analysis...")
        
        # Clean up expired cache entries
        if use_cache:
            self._cleanup_cache()
        
        # Get all S&P 500 symbols
        with self.db.engine.connect() as conn:
            query = text("""
                SELECT s.symbol, s.sector, c.price, c.beta, c.mktcap, c.dcf
                FROM sp500_constituents s
                LEFT JOIN company_profiles c ON s.symbol = c.symbol
            """)
            base_df = pd.read_sql(query, conn)
        
        # Collect fundamentals for each symbol
        fundamentals_data = []
        cache_hits = 0
        api_calls = 0
        
        for _, row in base_df.iterrows():
            symbol = row['symbol']
            logger.debug(f"Processing {symbol}...")
            
            # Try to get from cache first
            cached_fundamentals = None
            if use_cache and not force_refresh:
                cached_fundamentals = self._get_cached_fundamentals(symbol)
            
            if cached_fundamentals:
                # Use cached data
                cache_hits += 1
                combined_data = {
                    'symbol': symbol,
                    'sector': row['sector'],
                    'price': row['price'],
                    'beta': row['beta'],
                    'mktcap': row['mktcap'],
                    'dcf': row['dcf']
                }
                combined_data.update(cached_fundamentals)
                fundamentals_data.append(combined_data)
            else:
                # Fetch from API
                api_calls += 1
                logger.debug(f"Fetching fresh fundamentals for {symbol}")
                
                fundamentals = self.client.get_fundamentals_summary(symbol)
                
                if fundamentals and 'error' not in fundamentals:
                    # Cache the successful result
                    if use_cache:
                        self._cache_fundamentals(symbol, fundamentals)
                    
                    # Combine base data with fundamentals
                    combined_data = {
                        'symbol': symbol,
                        'sector': row['sector'],
                        'price': row['price'],
                        'beta': row['beta'],
                        'mktcap': row['mktcap'],
                        'dcf': row['dcf']
                    }
                    
                    # Add fundamentals data
                    combined_data.update(fundamentals)
                    fundamentals_data.append(combined_data)
                else:
                    # Add base data only for stocks without fundamentals
                    fundamentals_data.append({
                        'symbol': symbol,
                        'sector': row['sector'],
                        'price': row['price'],
                        'beta': row['beta'],
                        'mktcap': row['mktcap'],
                        'dcf': row['dcf'],
                        'insufficient_data': True
                    })
        
        logger.info("Fundamentals data collection complete:")
        logger.info(f"  Cache hits: {cache_hits}")
        logger.info(f"  API calls: {api_calls}")
        logger.info(f"  Total symbols processed: {len(base_df)}")
        
        return pd.DataFrame(fundamentals_data)
    
    def calculate_undervaluation_scores(self, use_cache: bool = True, force_refresh: bool = False) -> pd.DataFrame:
        """Calculate undervaluation scores for all stocks with caching support
        
        Args:
            use_cache: Whether to use cached fundamentals data
            force_refresh: Whether to force refresh all fundamentals data
        """
        logger.info("Starting undervaluation analysis...")
        
        # Get fundamentals data with caching
        df = self.get_fundamentals_data(use_cache=use_cache, force_refresh=force_refresh)
        
        # Define metrics for sector comparison
        valuation_metrics = ['pe_ratio', 'pb_ratio', 'price_to_sales']
        quality_metrics = ['roe', 'net_profit_margin', 'current_ratio', 'free_cash_flow_yield']
        strength_metrics = ['debt_to_equity', 'return_on_assets', 'gross_profit_margin']
        
        all_metrics = valuation_metrics + quality_metrics + strength_metrics
        
        # Calculate sector statistics
        sector_stats = self.calculate_sector_stats(df, all_metrics)
        
        # Calculate scores for each stock
        scores = []
        
        for _, stock in df.iterrows():
            if stock.get('insufficient_data'):
                scores.append({
                    'symbol': stock['symbol'],
                    'sector': stock['sector'],
                    'undervaluation_score': None,
                    'valuation_score': None,
                    'quality_score': None,
                    'strength_score': None,
                    'risk_score': None,
                    'data_quality': 'insufficient',
                    'price': stock.get('price'),
                    'mktcap': stock.get('mktcap')
                })
                continue
            
            sector = stock['sector']
            
            # Calculate component scores
            valuation_score = self.score_valuation_metrics(stock, sector_stats, sector)
            quality_score = self.score_quality_metrics(stock, sector_stats, sector)
            strength_score = self.score_financial_strength(stock, sector_stats, sector)
            risk_score = self.score_risk_adjustment(stock)
            
            # Calculate weighted final score
            final_score = (
                valuation_score * 0.4 +
                quality_score * 0.3 +
                strength_score * 0.2 +
                risk_score * 0.1
            )
            
            # Determine data quality
            available_metrics = sum(1 for metric in all_metrics 
                                  if pd.notna(pd.to_numeric(stock.get(metric), errors='coerce')))
            
            if available_metrics >= len(all_metrics) * 0.7:
                data_quality = 'high'
            elif available_metrics >= len(all_metrics) * 0.4:
                data_quality = 'medium'
            else:
                data_quality = 'low'
            
            scores.append({
                'symbol': stock['symbol'],
                'sector': stock['sector'],
                'undervaluation_score': round(final_score, 2),
                'valuation_score': round(valuation_score, 2),
                'quality_score': round(quality_score, 2),
                'strength_score': round(strength_score, 2),
                'risk_score': round(risk_score, 2),
                'data_quality': data_quality,
                'price': stock.get('price'),
                'mktcap': stock.get('mktcap')
            })
        
        return pd.DataFrame(scores)
    
    def store_scores(self, scores_df: pd.DataFrame):
        """Store undervaluation scores in database using standardized interface"""
        try:
            # Convert DataFrame to list of dictionaries for the standardized interface
            scores_data = scores_df.to_dict('records')
            
            # Use the standardized database interface
            self.db.insert_undervaluation_scores(scores_data)
            logger.info(f"Stored undervaluation scores for {len(scores_df)} stocks")
        except Exception as e:
            logger.error(f"Error storing undervaluation scores: {e}")
            # Fallback to direct to_sql if standardized interface fails
            scores_df.to_sql('undervaluation_scores', self.db.engine, 
                            if_exists='replace', index=False)
            logger.info(f"Fallback: Stored undervaluation scores for {len(scores_df)} stocks")
    
    def get_undervaluation_ranking(self) -> pd.DataFrame:
        """Get stocks ranked by undervaluation score"""
        with self.db.engine.connect() as conn:
            query = text("""
                SELECT symbol, sector, undervaluation_score, data_quality, 
                       price, mktcap, valuation_score, quality_score, 
                       strength_score, risk_score
                FROM undervaluation_scores
                ORDER BY 
                    CASE WHEN undervaluation_score IS NULL THEN 1 ELSE 0 END,
                    undervaluation_score DESC
            """)
            return pd.read_sql(query, conn)
    
    def analyze_undervaluation(self, use_cache: bool = True, force_refresh: bool = False) -> Dict:
        """Run complete undervaluation analysis with caching support
        
        Args:
            use_cache: Whether to use cached fundamentals data
            force_refresh: Whether to force refresh all fundamentals data
        """
        # Log cache statistics before analysis
        cache_stats = self.get_cache_stats()
        logger.info(f"Cache stats before analysis: {cache_stats}")
        
        scores_df = self.calculate_undervaluation_scores(use_cache=use_cache, force_refresh=force_refresh)
        self.store_scores(scores_df)
        
        # Log cache statistics after analysis
        final_cache_stats = self.get_cache_stats()
        logger.info(f"Cache stats after analysis: {final_cache_stats}")
        
        # Generate summary statistics
        valid_scores = scores_df[scores_df['undervaluation_score'].notna()]
        
        summary = {
            'total_stocks': len(scores_df),
            'analyzed_stocks': len(valid_scores),
            'insufficient_data': len(scores_df) - len(valid_scores),
            'highly_undervalued': len(valid_scores[valid_scores['undervaluation_score'] >= 80]),
            'moderately_undervalued': len(valid_scores[
                (valid_scores['undervaluation_score'] >= 60) & 
                (valid_scores['undervaluation_score'] < 80)
            ]),
            'fairly_valued': len(valid_scores[
                (valid_scores['undervaluation_score'] >= 40) & 
                (valid_scores['undervaluation_score'] < 60)
            ]),
            'overvalued': len(valid_scores[valid_scores['undervaluation_score'] < 40]),
            'avg_score': valid_scores['undervaluation_score'].mean() if len(valid_scores) > 0 else 0
        }
        
        return summary

if __name__ == "__main__":
    analyzer = UndervaluationAnalyzer()
    summary = analyzer.analyze_undervaluation()
    
    print("\n=== Undervaluation Analysis Summary ===")
    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\n=== Top 10 Most Undervalued Stocks ===")
    ranking = analyzer.get_undervaluation_ranking()
    top_10 = ranking.head(10)
    
    for _, stock in top_10.iterrows():
        if pd.notna(stock['undervaluation_score']):
            print(f"{stock['symbol']}: {stock['undervaluation_score']:.1f} ({stock['sector']})")