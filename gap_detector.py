#!/usr/bin/env python3
"""
Data Gap Detection Module for Stock Analyst
Identifies missing data periods and prioritizes backfilling
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from database import DatabaseManager
from sqlalchemy import text
from unified_config import get_config

logger = logging.getLogger(__name__)

@dataclass
class DataGap:
    """Represents a gap in data for a specific symbol"""
    symbol: str
    gap_type: str  # 'historical_prices', 'company_profile', etc.
    start_date: date
    end_date: date
    gap_days: int
    priority: str  # 'critical', 'high', 'medium', 'low'
    last_update: Optional[date] = None

class GapDetector:
    """
    Detects gaps in stock data and prioritizes backfilling
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config = get_config()
        
        # Market calendar - get holidays from unified config
        current_year = datetime.now().year
        self.market_holidays = self.config.get_market_holidays_as_dates(current_year)
        
        # Gap priority thresholds
        self.gap_thresholds = {
            'critical': 7,  # More than 7 business days
            'high': 3,      # 3-7 business days
            'medium': 1,    # 1-3 business days
            'low': 0        # Same day or next business day
        }
    
    def is_market_day(self, check_date: date) -> bool:
        """Check if a given date is a market trading day"""
        # Skip weekends
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Skip holidays
        if check_date in self.market_holidays:
            return False
        
        return True
    
    def get_business_days_gap(self, start_date: date, end_date: date) -> int:
        """Calculate number of business days between two dates"""
        business_days = 0
        current_date = start_date + timedelta(days=1)
        
        while current_date <= end_date:
            if self.is_market_day(current_date):
                business_days += 1
            current_date += timedelta(days=1)
        
        return business_days
    
    def classify_gap_priority(self, business_days_gap: int) -> str:
        """Classify gap priority based on business days"""
        if business_days_gap >= self.gap_thresholds['critical']:
            return 'critical'
        elif business_days_gap >= self.gap_thresholds['high']:
            return 'high'
        elif business_days_gap >= self.gap_thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def detect_price_data_gaps(self, limit_symbols: int = 100) -> List[DataGap]:
        """
        Detect gaps in historical price data
        """
        gaps = []
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Get S&P 500 symbols with their latest price data
                query = text("""
                    SELECT 
                        s.symbol,
                        MAX(hp.date) as last_price_date,
                        COUNT(hp.date) as price_records
                    FROM sp500_constituents s
                    LEFT JOIN historical_prices hp ON s.symbol = hp.symbol
                    GROUP BY s.symbol
                    ORDER BY 
                        CASE WHEN MAX(hp.date) IS NULL THEN 1 ELSE 0 END,
                        MAX(hp.date) ASC
                    LIMIT :limit
                """)
                
                result = conn.execute(query, {"limit": limit_symbols})
                
                for row in result.fetchall():
                    symbol = row.symbol
                    last_price_date = row.last_price_date
                    
                    # If no price data exists at all
                    if not last_price_date:
                        # Gap from 1 year ago to today
                        start_date = date.today() - timedelta(days=365)
                        end_date = date.today() - timedelta(days=1)  # Yesterday
                        
                        business_days = self.get_business_days_gap(start_date, end_date)
                        priority = 'critical'  # No data is always critical
                        
                        gaps.append(DataGap(
                            symbol=symbol,
                            gap_type='historical_prices',
                            start_date=start_date,
                            end_date=end_date,
                            gap_days=business_days,
                            priority=priority
                        ))
                    else:
                        # Check for gaps from last data to present
                        # Handle both date objects and string dates
                        if isinstance(last_price_date, date):
                            last_date = last_price_date
                        elif isinstance(last_price_date, str):
                            # Parse date string, handling potential time components
                            if ' ' in last_price_date:
                                last_date = datetime.strptime(last_price_date.split(' ')[0], '%Y-%m-%d').date()
                            else:
                                last_date = datetime.strptime(last_price_date, '%Y-%m-%d').date()
                        else:
                            # If it's a datetime object, convert to date
                            last_date = last_price_date.date() if hasattr(last_price_date, 'date') else date.today()
                        today = date.today()
                        
                        # Only consider it a gap if it's more than 1 business day old
                        if last_date < today - timedelta(days=1):
                            business_days = self.get_business_days_gap(last_date, today - timedelta(days=1))
                            
                            if business_days > 0:  # Only add if there are actual business days missing
                                priority = self.classify_gap_priority(business_days)
                                
                                gaps.append(DataGap(
                                    symbol=symbol,
                                    gap_type='historical_prices',
                                    start_date=last_date + timedelta(days=1),
                                    end_date=today - timedelta(days=1),
                                    gap_days=business_days,
                                    priority=priority,
                                    last_update=last_date
                                ))
                
                logger.info(f"Detected {len(gaps)} price data gaps")
                
        except Exception as e:
            logger.error(f"Error detecting price data gaps: {e}")
        
        return gaps
    
    def detect_profile_data_gaps(self, limit_symbols: int = None) -> List[DataGap]:
        """
        Detect missing company profile data
        """
        gaps = []
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Find symbols without company profiles
                if limit_symbols:
                    query = text("""
                        SELECT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN company_profiles cp ON s.symbol = cp.symbol
                        WHERE cp.symbol IS NULL
                        ORDER BY s.symbol
                        LIMIT :limit
                    """)
                    result = conn.execute(query, {"limit": limit_symbols})
                else:
                    query = text("""
                        SELECT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN company_profiles cp ON s.symbol = cp.symbol
                        WHERE cp.symbol IS NULL
                        ORDER BY s.symbol
                    """)
                    result = conn.execute(query)
                
                for row in result.fetchall():
                    gaps.append(DataGap(
                        symbol=row.symbol,
                        gap_type='company_profile',
                        start_date=date.today(),
                        end_date=date.today(),
                        gap_days=1,
                        priority='high'  # Missing profiles are high priority
                    ))
                
                logger.info(f"Detected {len(gaps)} missing company profiles")
                
        except Exception as e:
            logger.error(f"Error detecting profile gaps: {e}")
        
        return gaps
    
    def detect_corporate_actions_gaps(self, limit_symbols: int = None) -> List[DataGap]:
        """
        Detect missing corporate actions data
        """
        gaps = []
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Find symbols without corporate actions data
                if limit_symbols:
                    query = text("""
                        SELECT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN corporate_actions ca ON s.symbol = ca.symbol
                        WHERE ca.symbol IS NULL
                        ORDER BY s.symbol
                        LIMIT :limit
                    """)
                    result = conn.execute(query, {"limit": limit_symbols})
                else:
                    query = text("""
                        SELECT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN corporate_actions ca ON s.symbol = ca.symbol
                        WHERE ca.symbol IS NULL
                        ORDER BY s.symbol
                    """)
                    result = conn.execute(query)
                
                for row in result.fetchall():
                    gaps.append(DataGap(
                        symbol=row.symbol,
                        gap_type='corporate_actions',
                        start_date=date.today(),
                        end_date=date.today(),
                        gap_days=1,
                        priority='medium'  # Corporate actions are medium priority
                    ))
                
                logger.info(f"Detected {len(gaps)} missing corporate actions")
                
        except Exception as e:
            logger.error(f"Error detecting corporate actions gaps: {e}")
        
        return gaps
    
    def detect_financial_statements_gaps(self, limit_symbols: int = None) -> List[DataGap]:
        """
        Detect missing financial statements data
        """
        gaps = []
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Find symbols without any financial statements data (income, balance sheet, or cash flow)
                if limit_symbols:
                    query = text("""
                        SELECT DISTINCT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN income_statements ins ON s.symbol = ins.symbol
                        LEFT JOIN balance_sheets bs ON s.symbol = bs.symbol
                        LEFT JOIN cash_flow_statements cs ON s.symbol = cs.symbol
                        WHERE ins.symbol IS NULL AND bs.symbol IS NULL AND cs.symbol IS NULL
                        ORDER BY s.symbol
                        LIMIT :limit
                    """)
                    result = conn.execute(query, {"limit": limit_symbols})
                else:
                    query = text("""
                        SELECT DISTINCT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN income_statements ins ON s.symbol = ins.symbol
                        LEFT JOIN balance_sheets bs ON s.symbol = bs.symbol
                        LEFT JOIN cash_flow_statements cs ON s.symbol = cs.symbol
                        WHERE ins.symbol IS NULL AND bs.symbol IS NULL AND cs.symbol IS NULL
                        ORDER BY s.symbol
                    """)
                    result = conn.execute(query)
                
                for row in result.fetchall():
                    gaps.append(DataGap(
                        symbol=row.symbol,
                        gap_type='financial_statements',
                        start_date=date.today(),
                        end_date=date.today(),
                        gap_days=1,
                        priority='high'  # Financial statements are high priority
                    ))
                
                logger.info(f"Detected {len(gaps)} missing financial statements")
                
        except Exception as e:
            logger.error(f"Error detecting financial statements gaps: {e}")
        
        return gaps
    
    def detect_analyst_recommendations_gaps(self, limit_symbols: int = None) -> List[DataGap]:
        """
        Detect missing analyst recommendations data
        """
        gaps = []
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Find symbols without analyst recommendations data
                if limit_symbols:
                    query = text("""
                        SELECT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN analyst_recommendations ar ON s.symbol = ar.symbol
                        WHERE ar.symbol IS NULL
                        ORDER BY s.symbol
                        LIMIT :limit
                    """)
                    result = conn.execute(query, {"limit": limit_symbols})
                else:
                    query = text("""
                        SELECT s.symbol
                        FROM sp500_constituents s
                        LEFT JOIN analyst_recommendations ar ON s.symbol = ar.symbol
                        WHERE ar.symbol IS NULL
                        ORDER BY s.symbol
                    """)
                    result = conn.execute(query)
                
                for row in result.fetchall():
                    gaps.append(DataGap(
                        symbol=row.symbol,
                        gap_type='analyst_recommendations',
                        start_date=date.today(),
                        end_date=date.today(),
                        gap_days=1,
                        priority='medium'  # Analyst recommendations are medium priority
                    ))
                
                logger.info(f"Detected {len(gaps)} missing analyst recommendations")
                
        except Exception as e:
            logger.error(f"Error detecting analyst recommendations gaps: {e}")
        
        return gaps
    
    def detect_all_gaps(self) -> Dict[str, List[DataGap]]:
        """
        Detect all types of data gaps
        """
        logger.info("Starting comprehensive gap detection...")
        
        all_gaps = {
            'price_data': self.detect_price_data_gaps(),
            'profile_data': self.detect_profile_data_gaps(),
            'corporate_actions': self.detect_corporate_actions_gaps(),
            'financial_statements': self.detect_financial_statements_gaps(),
            'analyst_recommendations': self.detect_analyst_recommendations_gaps()
        }
        
        # Log summary
        total_gaps = sum(len(gaps) for gaps in all_gaps.values())
        logger.info(f"Gap detection complete. Found {total_gaps} total gaps:")
        
        for gap_type, gaps in all_gaps.items():
            if gaps:
                priority_counts = {}
                for gap in gaps:
                    priority_counts[gap.priority] = priority_counts.get(gap.priority, 0) + 1
                
                logger.info(f"  {gap_type}: {len(gaps)} gaps - {priority_counts}")
        
        return all_gaps
    
    def get_prioritized_backfill_list(self, max_items: int = 100) -> List[DataGap]:
        """
        Get prioritized list of gaps for backfilling
        Returns gaps sorted by priority and business impact
        """
        all_gaps = self.detect_all_gaps()
        
        # Flatten all gaps into single list
        flattened_gaps = []
        for gap_type, gaps in all_gaps.items():
            flattened_gaps.extend(gaps)
        
        # Sort by priority (critical first) and then by gap size
        priority_order = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
        
        sorted_gaps = sorted(
            flattened_gaps,
            key=lambda x: (
                priority_order.get(x.priority, 5),  # Priority first
                -x.gap_days,  # Larger gaps first within same priority
                x.symbol  # Alphabetical for consistency
            )
        )
        
        return sorted_gaps[:max_items]
    
    def get_gap_statistics(self) -> Dict:
        """
        Get comprehensive statistics about data gaps
        """
        all_gaps = self.detect_all_gaps()
        
        stats = {
            'total_gaps': 0,
            'by_type': {},
            'by_priority': {},
            'oldest_gap_days': 0,
            'symbols_affected': set()
        }
        
        for gap_type, gaps in all_gaps.items():
            stats['by_type'][gap_type] = len(gaps)
            stats['total_gaps'] += len(gaps)
            
            for gap in gaps:
                stats['by_priority'][gap.priority] = stats['by_priority'].get(gap.priority, 0) + 1
                stats['oldest_gap_days'] = max(stats['oldest_gap_days'], gap.gap_days)
                stats['symbols_affected'].add(gap.symbol)
        
        stats['symbols_affected'] = len(stats['symbols_affected'])
        
        return stats

def main():
    """Test the gap detection functionality"""
    from logging_config import setup_logging
    setup_logging()
    
    detector = GapDetector()
    
    print("Running comprehensive gap detection...")
    gaps = detector.detect_all_gaps()
    
    print(f"\nGap Detection Results:")
    print(f"{'='*50}")
    
    total_gaps = sum(len(gap_list) for gap_list in gaps.values())
    print(f"Total gaps found: {total_gaps}")
    
    for gap_type, gap_list in gaps.items():
        print(f"\n{gap_type.upper().replace('_', ' ')}: {len(gap_list)} gaps")
        if gap_list:
            priority_counts = {}
            for gap in gap_list:
                priority_counts[gap.priority] = priority_counts.get(gap.priority, 0) + 1
            
            for priority in ['critical', 'high', 'medium', 'low']:
                if priority in priority_counts:
                    print(f"  {priority.title()}: {priority_counts[priority]}")
    
    print(f"\n{'='*50}")
    stats = detector.get_gap_statistics()
    print(f"Statistics: {stats}")

if __name__ == '__main__':
    main()