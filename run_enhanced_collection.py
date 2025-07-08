#!/usr/bin/env python3
"""
Run enhanced data collection in manageable batches
"""

from enhanced_data_collector import EnhancedDataCollector
from sqlalchemy import text
import time

def run_batch_collection():
    """Run enhanced data collection in batches"""
    collector = EnhancedDataCollector()
    
    # Get symbols that don't have enhanced data yet
    with collector.db.engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol FROM company_profiles 
            WHERE beta IS NULL OR shares_outstanding IS NULL 
            ORDER BY symbol
        """)).fetchall()
        
        missing_symbols = [row[0] for row in result]
    
    print(f"🔍 Found {len(missing_symbols)} companies missing enhanced data")
    
    if not missing_symbols:
        print("✅ All companies already have enhanced data!")
        return
    
    batch_size = 100
    total_batches = (len(missing_symbols) + batch_size - 1) // batch_size
    
    overall_successful = 0
    overall_failed = 0
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(missing_symbols))
        batch_symbols = missing_symbols[start_idx:end_idx]
        
        print(f"\n🚀 Processing batch {batch_num + 1}/{total_batches} ({len(batch_symbols)} symbols)")
        
        result = collector.collect_enhanced_data_batch(symbols=batch_symbols)
        overall_successful += result['successful']
        overall_failed += result['failed']
        
        print(f"   Batch {batch_num + 1} result: {result['successful']}/{result['total_processed']} successful")
        
        # Show progress every few batches
        if (batch_num + 1) % 2 == 0 or batch_num == total_batches - 1:
            coverage = collector.check_data_coverage()
            print(f"   Current beta coverage: {coverage['beta_coverage']}")
            print(f"   Current shares coverage: {coverage['shares_coverage']}")
    
    print(f"\n✅ Enhanced data collection complete!")
    print(f"📈 Overall results: {overall_successful}/{overall_successful + overall_failed} companies updated")
    
    # Final coverage check
    print(f"\n🔍 Final data coverage:")
    final_coverage = collector.check_data_coverage()
    for metric, value in final_coverage.items():
        if metric != 'total_companies':
            print(f"   {metric}: {value}")

if __name__ == "__main__":
    run_batch_collection()