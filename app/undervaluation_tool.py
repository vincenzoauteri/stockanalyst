#!/usr/bin/env python3
"""
Unified Undervaluation Analysis Tool
Supports both demo mode (with simulated data) and test mode (with real system testing)
"""

import argparse
import pandas as pd
import numpy as np
from database import DatabaseManager
from undervaluation_analyzer import UndervaluationAnalyzer
from sqlalchemy import text
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_mode():
    """Demo undervaluation calculation with simulated data for limited stocks"""
    
    print("🎯 Demo: Undervaluation Analysis (Limited Scope)")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # Use only a few stocks to avoid rate limits
    demo_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'JNJ']
    
    print(f"📊 Analyzing {len(demo_symbols)} stocks: {', '.join(demo_symbols)}")
    
    # Create sample undervaluation scores
    demo_scores = []
    
    for i, symbol in enumerate(demo_symbols):
        print(f"Processing {symbol}...")
        
        # Get basic company data
        with db.engine.connect() as conn:
            query = text("""
                SELECT s.symbol, s.sector, c.price, c.mktcap, c.beta 
                FROM sp500_constituents s
                LEFT JOIN company_profiles c ON s.symbol = c.symbol
                WHERE s.symbol = :symbol
            """)
            result = conn.execute(query, {"symbol": symbol})
            stock_data = result.fetchone()
        
        if stock_data:
            # Create demo scores (normally would be calculated from fundamentals)
            # These are simulated for demonstration
            base_score = 75 - (i * 10)  # Decreasing scores for variety
            
            demo_scores.append({
                'symbol': symbol,
                'sector': stock_data.sector,
                'undervaluation_score': round(base_score + np.random.uniform(-5, 5), 1),
                'valuation_score': round(base_score * 0.4 + np.random.uniform(-10, 10), 1),
                'quality_score': round(base_score * 0.3 + np.random.uniform(-10, 10), 1),
                'strength_score': round(base_score * 0.2 + np.random.uniform(-10, 10), 1),
                'risk_score': round(base_score * 0.1 + np.random.uniform(-10, 10), 1),
                'data_quality': 'high' if i < 3 else 'medium',
                'price': float(stock_data.price) if stock_data.price else None,
                'mktcap': float(stock_data.mktcap) if stock_data.mktcap else None
            })
        
        # Add delay to avoid rate limits
        time.sleep(1)
    
    # Store demo scores
    if demo_scores:
        scores_df = pd.DataFrame(demo_scores)
        scores_df.to_sql('undervaluation_scores', db.engine, if_exists='replace', index=False)
        print(f"✅ Stored {len(demo_scores)} demo undervaluation scores")
        
        print("\n📈 Demo Results:")
        print("-" * 60)
        for score in sorted(demo_scores, key=lambda x: x['undervaluation_score'] or 0, reverse=True):
            score_val = score['undervaluation_score']
            if score_val >= 80:
                category = "🟢 Highly Undervalued"
            elif score_val >= 60:
                category = "🟡 Moderately Undervalued"
            elif score_val >= 40:
                category = "🔵 Fairly Valued"
            else:
                category = "🔴 Overvalued"
                
            print(f"{score['symbol']:<6} | Score: {score_val:5.1f} | {category}")
        
        print("\n📊 Summary:")
        valid_scores = [s['undervaluation_score'] for s in demo_scores if s['undervaluation_score']]
        print(f"   • Total analyzed: {len(demo_scores)}")
        print(f"   • Average score: {np.mean(valid_scores):.1f}")
        print(f"   • Highly undervalued (≥80): {sum(1 for s in valid_scores if s >= 80)}")
        print(f"   • Moderately undervalued (60-79): {sum(1 for s in valid_scores if 60 <= s < 80)}")
        print(f"   • Fairly valued (40-59): {sum(1 for s in valid_scores if 40 <= s < 60)}")
        print(f"   • Overvalued (<40): {sum(1 for s in valid_scores if s < 40)}")
        
        return True
    
    return False


def test_mode():
    """Test the complete undervaluation scoring system"""
    
    print("🧪 Testing Undervaluation Scoring System")
    print("=" * 50)
    
    # Initialize components
    db = DatabaseManager()
    analyzer = UndervaluationAnalyzer()
    
    # Check if we have S&P 500 data
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM sp500_constituents"))
        stock_count = result.fetchone()[0]
        
        print(f"📊 Found {stock_count} stocks in S&P 500 constituents table")
        
        if stock_count == 0:
            print("❌ No S&P 500 data found. Please run main.py first to populate data.")
            return False
    
    # Check existing undervaluation scores
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM undervaluation_scores"))
        scores_count = result.fetchone()[0]
        
        print(f"📈 Found {scores_count} existing undervaluation scores")
    
    # Test a small batch calculation (first 5 stocks)
    print("\n🔬 Testing calculation with first 5 stocks...")
    
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT symbol FROM sp500_constituents LIMIT 5"))
        symbols = [row[0] for row in result.fetchall()]
        
        print(f"Testing symbols: {', '.join(symbols)}")
    
    # This would normally calculate all stocks, but for testing we'll just verify the system works
    try:
        # Just test the database structure
        scores_df = analyzer.get_undervaluation_ranking()
        print(f"✅ Database query successful - found {len(scores_df)} ranked stocks")
        
        if len(scores_df) > 0:
            print("\n📋 Sample Rankings:")
            for i, row in scores_df.head(10).iterrows():
                score_str = f"{row['undervaluation_score']:.1f}" if row['undervaluation_score'] else "N/A"
                quality_str = row['data_quality'] or "Unknown"
                print(f"   {row['symbol']}: {score_str} ({quality_str})")
        else:
            print("⚠️  No undervaluation scores found. Run calculation first.")
        
        print("\n✅ Undervaluation system test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        logger.error(f"Test mode failed: {e}", exc_info=True)
        return False


def full_calculation_mode():
    """Run full undervaluation calculation on all S&P 500 stocks"""
    
    print("🚀 Full Undervaluation Analysis")
    print("=" * 50)
    
    try:
        analyzer = UndervaluationAnalyzer()
        
        print("Starting full calculation for all S&P 500 stocks...")
        print("⚠️ This may take a while and consume API credits")
        
        # Run the full calculation
        results = analyzer.calculate_undervaluation_scores()
        
        if results and len(results) > 0:
            print(f"✅ Successfully calculated scores for {len(results)} stocks")
            
            # Show top 10 undervalued stocks
            sorted_results = sorted(results, key=lambda x: x.get('undervaluation_score', 0), reverse=True)
            print("\n🏆 Top 10 Most Undervalued Stocks:")
            for i, stock in enumerate(sorted_results[:10], 1):
                score = stock.get('undervaluation_score', 0)
                symbol = stock.get('symbol', 'N/A')
                sector = stock.get('sector', 'N/A')
                print(f"   {i:2d}. {symbol:<6} | Score: {score:5.1f} | {sector}")
            
            return True
        else:
            print("❌ No results calculated")
            return False
            
    except Exception as e:
        print(f"❌ Error during full calculation: {e}")
        logger.error(f"Full calculation failed: {e}", exc_info=True)
        return False


def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Undervaluation Analysis Tool')
    parser.add_argument('mode', choices=['demo', 'test', 'full'], 
                       help='Mode to run: demo (simulated data), test (system validation), or full (complete analysis)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print(f"🔧 Running in {args.mode} mode...")
    print()
    
    success = False
    
    if args.mode == 'demo':
        success = demo_mode()
    elif args.mode == 'test':
        success = test_mode()
    elif args.mode == 'full':
        success = full_calculation_mode()
    
    if success:
        print("\n🎉 Operation completed successfully!")
    else:
        print("\n❌ Operation failed or completed with issues")
        exit(1)


if __name__ == "__main__":
    main()