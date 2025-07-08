#!/usr/bin/env python3
"""
Check status of enhanced data collection
"""

from enhanced_data_collector import EnhancedDataCollector

def main():
    collector = EnhancedDataCollector()
    
    print("📊 Enhanced Data Collection Status")
    print("=" * 50)
    
    coverage = collector.check_data_coverage()
    for metric, value in coverage.items():
        if metric == 'total_companies':
            print(f"Total Companies: {value}")
        else:
            print(f"{metric.replace('_', ' ').title()}: {value}")
    
    # Check which companies have complete enhanced data
    from sqlalchemy import text
    with collector.db.engine.connect() as conn:
        complete_data = conn.execute(text("""
            SELECT COUNT(*) FROM company_profiles 
            WHERE beta IS NOT NULL 
            AND shares_outstanding IS NOT NULL 
            AND book_value IS NOT NULL
        """)).scalar()
        
        print(f"\nComplete Enhanced Data: {complete_data}/{coverage['total_companies']} ({complete_data/coverage['total_companies']*100:.1f}%)")

if __name__ == "__main__":
    main()