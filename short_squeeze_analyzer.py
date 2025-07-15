#!/usr/bin/env python3
"""
Short Squeeze Analysis Engine
Implements the quantitative model for assessing short squeeze susceptibility
Based on the methodology outlined in SQUEEZE.md
"""

from typing import Dict, List, Optional, Tuple
from database import DatabaseManager
from sqlalchemy import text
from logging_config import get_logger
import pandas as pd
import numpy as np
from datetime import datetime, date
from unified_config import get_config

logger = get_logger(__name__)

class ShortSqueezeAnalyzer:
    """
    Calculate short squeeze susceptibility scores using Yahoo Finance data.
    Implements the scoring algorithm from SQUEEZE.md with database integration.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def get_short_interest_data(self, symbol: str) -> Dict:
        """Get the latest short interest data for a symbol from our database"""
        try:
            with self.db.engine.connect() as conn:
                short_data = conn.execute(text("""
                    SELECT symbol, report_date, short_interest, float_shares, 
                           short_ratio, short_percent_of_float, average_daily_volume
                    FROM short_interest_data 
                    WHERE symbol = :symbol 
                    ORDER BY report_date DESC 
                    LIMIT 1
                """), {'symbol': symbol}).fetchone()
                
                if not short_data:
                    return {}
                
                # Convert to dictionary
                return {
                    'symbol': short_data.symbol,
                    'report_date': short_data.report_date,
                    'short_interest': short_data.short_interest,
                    'float_shares': short_data.float_shares,
                    'short_ratio': float(short_data.short_ratio) if short_data.short_ratio else None,
                    'short_percent_of_float': float(short_data.short_percent_of_float) if short_data.short_percent_of_float else None,
                    'average_daily_volume': short_data.average_daily_volume
                }
        except Exception as e:
            logger.error(f"Error retrieving short interest data for {symbol}: {e}")
            return {}
    
    def get_historical_prices(self, symbol: str, days: int = 70) -> pd.DataFrame:
        """Get historical price data for RSI calculation"""
        try:
            with self.db.engine.connect() as conn:
                price_data = conn.execute(text("""
                    SELECT date, open, high, low, close, volume
                    FROM historical_prices 
                    WHERE symbol = :symbol 
                    ORDER BY date DESC 
                    LIMIT :days
                """), {'symbol': symbol, 'days': days}).fetchall()
                
                if not price_data:
                    return pd.DataFrame()
                
                # Convert to DataFrame and sort by date ascending for calculations
                df = pd.DataFrame(price_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                
                return df
        except Exception as e:
            logger.error(f"Error retrieving historical prices for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """
        Calculate RSI (Relative Strength Index) using standard 14-day period
        
        Args:
            prices: Series of closing prices
            period: Period for RSI calculation (default 14)
            
        Returns:
            Current RSI value or 50 if calculation fails
        """
        try:
            if len(prices) < period + 1:
                logger.warning(f"Insufficient price data for RSI calculation: {len(prices)} days")
                return 50.0  # Neutral RSI
            
            # Calculate price changes
            delta = prices.diff()
            
            # Separate gains and losses
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Return the most recent RSI value
            current_rsi = rsi.iloc[-1]
            
            if pd.isna(current_rsi):
                return 50.0
                
            return float(current_rsi)
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0
    
    def calculate_relative_volume(self, symbol: str) -> float:
        """
        Calculate relative volume (current volume vs average daily volume)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Relative volume ratio or 1.0 if calculation fails
        """
        try:
            with self.db.engine.connect() as conn:
                # Get most recent trading day volume and average volume
                volume_data = conn.execute(text("""
                    SELECT hp.volume as current_volume, si.average_daily_volume
                    FROM historical_prices hp
                    LEFT JOIN short_interest_data si ON hp.symbol = si.symbol
                    WHERE hp.symbol = :symbol 
                    ORDER BY hp.date DESC, si.report_date DESC
                    LIMIT 1
                """), {'symbol': symbol}).fetchone()
                
                if not volume_data or not volume_data.current_volume or not volume_data.average_daily_volume:
                    return 1.0
                
                current_vol = float(volume_data.current_volume)
                avg_vol = float(volume_data.average_daily_volume)
                
                if avg_vol <= 0:
                    return 1.0
                
                return current_vol / avg_vol
                
        except Exception as e:
            logger.error(f"Error calculating relative volume for {symbol}: {e}")
            return 1.0
    
    def normalize_si_score(self, si_percent: float) -> float:
        """
        Normalize Short Interest % of Float to 0-100 score
        Thresholds: 10% = 0, 40%+ = 100
        """
        if si_percent <= 10:
            return 0.0
        elif si_percent >= 40:
            return 100.0
        else:
            return (si_percent - 10) * (100 / (40 - 10))
    
    def normalize_dtc_score(self, days_to_cover: float) -> float:
        """
        Normalize Days to Cover to 0-100 score
        Thresholds: 2 days = 0, 10+ days = 100
        """
        if days_to_cover <= 2:
            return 0.0
        elif days_to_cover >= 10:
            return 100.0
        else:
            return (days_to_cover - 2) * (100 / (10 - 2))
    
    def normalize_float_score(self, float_shares: int) -> float:
        """
        Normalize Float Shares to 0-100 score (inverse scale)
        Thresholds: <10M = 100, >200M = 0
        """
        if float_shares <= 10_000_000:
            return 100.0
        elif float_shares >= 200_000_000:
            return 0.0
        else:
            # Linear interpolation between the thresholds
            return 100 - ((float_shares - 10_000_000) / (200_000_000 - 10_000_000) * 100)
    
    def normalize_rvol_score(self, relative_volume: float) -> float:
        """
        Normalize Relative Volume to 0-100 score
        Thresholds: 1.5 = 0, 5+ = 100
        """
        if relative_volume <= 1.5:
            return 0.0
        elif relative_volume >= 5.0:
            return 100.0
        else:
            return (relative_volume - 1.5) * (100 / (5.0 - 1.5))
    
    def normalize_rsi_score(self, rsi: float) -> float:
        """
        Normalize RSI to 0-100 score (inverse scale for oversold)
        Thresholds: <30 = 100 (oversold, good for squeeze), >70 = 0 (overbought)
        """
        if rsi <= 30:
            return 100.0
        elif rsi >= 70:
            return 0.0
        else:
            # Linear interpolation: higher RSI = lower squeeze potential
            return 100 - ((rsi - 30) / (70 - 30) * 100)
    
    def assess_data_quality(self, symbol: str, short_data: Dict, price_data: pd.DataFrame) -> str:
        """
        Assess the quality of data available for scoring
        
        Returns:
            'high', 'medium', 'low', or 'insufficient'
        """
        quality_score = 0
        max_score = 5
        
        # Check short interest data completeness
        if short_data.get('short_percent_of_float') is not None:
            quality_score += 1
        if short_data.get('short_ratio') is not None:
            quality_score += 1
        if short_data.get('float_shares') is not None:
            quality_score += 1
        if short_data.get('average_daily_volume') is not None:
            quality_score += 1
            
        # Check historical price data
        if len(price_data) >= 14:  # Minimum for RSI
            quality_score += 1
        
        if quality_score == max_score:
            return 'high'
        elif quality_score >= 3:
            return 'medium'
        elif quality_score >= 1:
            return 'low'
        else:
            return 'insufficient'
    
    def calculate_squeeze_score(self, symbol: str) -> Dict:
        """
        Calculate comprehensive short squeeze susceptibility score for a symbol
        
        Args:
            symbol: Stock symbol to analyze
            
        Returns:
            Dictionary containing squeeze score and component analysis
        """
        logger.info(f"Calculating short squeeze score for {symbol}")
        
        try:
            # Get short interest data
            short_data = self.get_short_interest_data(symbol)
            if not short_data:
                return {
                    'symbol': symbol,
                    'squeeze_score': None,
                    'data_quality': 'insufficient',
                    'error': 'No short interest data available'
                }
            
            # Get historical price data for RSI calculation
            price_data = self.get_historical_prices(symbol)
            
            # Assess data quality
            data_quality = self.assess_data_quality(symbol, short_data, price_data)
            
            if data_quality == 'insufficient':
                return {
                    'symbol': symbol,
                    'squeeze_score': None,
                    'data_quality': data_quality,
                    'error': 'Insufficient data for reliable scoring'
                }
            
            # Extract raw metrics with defaults
            si_percent = short_data.get('short_percent_of_float', 0) or 0
            days_to_cover = short_data.get('short_ratio', 0) or 0
            float_shares = short_data.get('float_shares', 200_000_000) or 200_000_000  # Default to large float
            
            # Calculate RSI
            if len(price_data) >= 14:
                rsi = self.calculate_rsi(price_data['close'])
            else:
                rsi = 50.0  # Neutral RSI if insufficient data
            
            # Calculate relative volume
            rvol = self.calculate_relative_volume(symbol)
            
            # Normalize all components to 0-100 scores
            si_score = self.normalize_si_score(si_percent)
            dtc_score = self.normalize_dtc_score(days_to_cover)
            float_score = self.normalize_float_score(float_shares)
            rvol_score = self.normalize_rvol_score(rvol)
            rsi_score = self.normalize_rsi_score(rsi)
            
            # Calculate momentum score (average of RVOL and RSI scores)
            momentum_score = (rvol_score + rsi_score) / 2
            
            # Calculate weighted final score according to SQUEEZE.md methodology
            # SI% (40%) + DTC (30%) + Float (15%) + Momentum (15%)
            squeeze_score = (
                si_score * 0.40 +
                dtc_score * 0.30 +
                float_score * 0.15 +
                momentum_score * 0.15
            )
            
            result = {
                'symbol': symbol,
                'squeeze_score': round(squeeze_score, 2),
                'si_score': round(si_score, 2),
                'dtc_score': round(dtc_score, 2),
                'float_score': round(float_score, 2),
                'momentum_score': round(momentum_score, 2),
                'data_quality': data_quality,
                'raw_metrics': {
                    'short_percent_of_float': si_percent,
                    'days_to_cover': days_to_cover,
                    'float_shares': float_shares,
                    'rsi': round(rsi, 2),
                    'relative_volume': round(rvol, 2),
                    'report_date': short_data.get('report_date')
                },
                'calculated_at': datetime.now().isoformat()
            }
            
            logger.info(f"Calculated squeeze score for {symbol}: {squeeze_score:.2f} (quality: {data_quality})")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating squeeze score for {symbol}: {e}")
            return {
                'symbol': symbol,
                'squeeze_score': None,
                'data_quality': 'error',
                'error': str(e)
            }
    
    def calculate_batch_scores(self, symbols: List[str]) -> List[Dict]:
        """
        Calculate squeeze scores for multiple symbols efficiently
        
        Args:
            symbols: List of stock symbols to analyze
            
        Returns:
            List of dictionaries containing results for each symbol
        """
        logger.info(f"Calculating squeeze scores for {len(symbols)} symbols")
        
        results = []
        processed = 0
        
        for symbol in symbols:
            try:
                result = self.calculate_squeeze_score(symbol)
                results.append(result)
                processed += 1
                
                if processed % 50 == 0:
                    logger.info(f"Processed {processed}/{len(symbols)} symbols")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                results.append({
                    'symbol': symbol,
                    'squeeze_score': None,
                    'data_quality': 'error',
                    'error': str(e)
                })
        
        # Filter out error results and sort by squeeze score
        valid_results = [r for r in results if r.get('squeeze_score') is not None]
        valid_results.sort(key=lambda x: x['squeeze_score'], reverse=True)
        
        logger.info(f"Completed squeeze score calculation for {len(symbols)} symbols. "
                   f"{len(valid_results)} valid scores calculated.")
        
        return results
    
    def store_squeeze_scores(self, results: List[Dict]) -> int:
        """
        Store calculated squeeze scores in the database
        
        Args:
            results: List of squeeze score results
            
        Returns:
            Number of scores successfully stored
        """
        stored_count = 0
        
        for result in results:
            if result.get('squeeze_score') is not None:
                try:
                    score_data = {
                        'squeeze_score': result['squeeze_score'],
                        'si_score': result['si_score'],
                        'dtc_score': result['dtc_score'],
                        'float_score': result['float_score'],
                        'momentum_score': result['momentum_score'],
                        'data_quality': result['data_quality']
                    }
                    
                    self.db.insert_short_squeeze_score(result['symbol'], score_data)
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Error storing squeeze score for {result['symbol']}: {e}")
        
        logger.info(f"Stored {stored_count} squeeze scores to database")
        return stored_count