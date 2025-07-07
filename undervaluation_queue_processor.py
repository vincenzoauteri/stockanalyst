#!/usr/bin/env python3
"""
Undervaluation Queue Processor
Processes automatic recalculation requests triggered by database changes
"""

import time
import logging
from datetime import datetime
from typing import List, Dict
from database import DatabaseManager
from yfinance_undervaluation_calculator import YFinanceUndervaluationCalculator
from sqlalchemy import text
from logging_config import get_logger

logger = get_logger(__name__)

class UndervaluationQueueProcessor:
    """
    Background processor for automatic undervaluation score recalculation
    """
    
    def __init__(self, batch_size: int = 10, sleep_interval: int = 30):
        self.db = DatabaseManager()
        self.calculator = YFinanceUndervaluationCalculator()
        self.batch_size = batch_size
        self.sleep_interval = sleep_interval
        self.running = False
        
    def get_pending_recalculations(self) -> List[Dict]:
        """Get pending recalculation requests from the queue"""
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT symbol, trigger_table, triggered_at
                    FROM undervaluation_recalc_queue 
                    WHERE status = 'pending'
                    ORDER BY triggered_at
                    LIMIT :limit
                """), {'limit': self.batch_size})
                
                return [{'symbol': row.symbol, 'trigger_table': row.trigger_table, 
                        'triggered_at': row.triggered_at} for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting pending recalculations: {e}")
            return []
    
    def mark_processing(self, symbols: List[str]):
        """Mark symbols as being processed"""
        try:
            with self.db.engine.connect() as conn:
                for symbol in symbols:
                    conn.execute(text("""
                        UPDATE undervaluation_recalc_queue 
                        SET status = 'processing' 
                        WHERE symbol = :symbol
                    """), {'symbol': symbol})
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error marking symbols as processing: {e}")
    
    def mark_completed(self, symbol: str, success: bool = True):
        """Mark a symbol's recalculation as completed or failed"""
        try:
            status = 'completed' if success else 'failed'
            with self.db.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE undervaluation_recalc_queue 
                    SET status = :status, processed_at = CURRENT_TIMESTAMP
                    WHERE symbol = :symbol
                """), {'symbol': symbol, 'status': status})
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error marking {symbol} as {status}: {e}")
    
    def cleanup_old_entries(self, days: int = 7):
        """Clean up old completed/failed entries"""
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM undervaluation_recalc_queue 
                    WHERE status IN ('completed', 'failed') 
                    AND processed_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """ % days))
                deleted = result.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old queue entries")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old entries: {e}")
    
    def process_recalculation(self, symbol: str) -> bool:
        """Process a single recalculation request"""
        try:
            logger.info(f"Recalculating undervaluation score for {symbol}")
            
            # Calculate new score
            score_data = self.calculator.calculate_undervaluation_score(symbol)
            
            if score_data:
                # Save updated score
                self.calculator.save_undervaluation_score(score_data)
                logger.info(f"Updated undervaluation score for {symbol}: {score_data['undervaluation_score']:.1f}")
                return True
            else:
                logger.warning(f"Could not calculate score for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing recalculation for {symbol}: {e}")
            return False
    
    def process_batch(self):
        """Process a batch of pending recalculations"""
        pending = self.get_pending_recalculations()
        
        if not pending:
            return 0
            
        symbols = [item['symbol'] for item in pending]
        logger.info(f"Processing batch of {len(symbols)} recalculations: {', '.join(symbols)}")
        
        # Mark as processing
        self.mark_processing(symbols)
        
        processed = 0
        for item in pending:
            symbol = item['symbol']
            
            try:
                success = self.process_recalculation(symbol)
                self.mark_completed(symbol, success)
                
                if success:
                    processed += 1
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                self.mark_completed(symbol, False)
        
        logger.info(f"Batch complete: {processed}/{len(symbols)} successful")
        return processed
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT status, COUNT(*) as count
                    FROM undervaluation_recalc_queue 
                    GROUP BY status
                """)).fetchall()
                
                stats = {row.status: row.count for row in result}
                stats['total'] = sum(stats.values())
                return stats
                
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {}
    
    def run_once(self):
        """Run one processing cycle"""
        try:
            # Process pending recalculations
            processed = self.process_batch()
            
            # Clean up old entries periodically  
            if processed > 0:
                self.cleanup_old_entries()
            
            # Log stats if there's activity
            if processed > 0:
                stats = self.get_queue_stats()
                logger.info(f"Queue stats: {stats}")
                
            return processed
            
        except Exception as e:
            logger.error(f"Error in processing cycle: {e}")
            return 0
    
    def run_forever(self):
        """Run the processor continuously"""
        logger.info("Starting undervaluation queue processor")
        self.running = True
        
        try:
            while self.running:
                processed = self.run_once()
                
                # Sleep between cycles (longer if no work done)
                sleep_time = self.sleep_interval if processed > 0 else self.sleep_interval * 2
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
            logger.info("Queue processor stopped")
    
    def stop(self):
        """Stop the processor"""
        self.running = False

def main():
    """Run the queue processor"""
    processor = UndervaluationQueueProcessor()
    
    print("🔄 Starting undervaluation queue processor...")
    print("   This will automatically recalculate scores when financial data changes")
    print("   Press Ctrl+C to stop")
    
    try:
        processor.run_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Stopping processor...")
        processor.stop()

if __name__ == "__main__":
    main()