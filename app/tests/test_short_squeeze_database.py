import pytest
import os
from datetime import date
from unittest.mock import patch
from sqlalchemy import text
from database import DatabaseManager


@pytest.fixture
def db_manager():
    """Create a test database manager with proper test environment setup"""
    with patch.dict(os.environ, {
        'TESTING': 'true',
        'POSTGRES_HOST': 'test-postgres',
        'POSTGRES_DB': 'stockanalyst_test'
    }):
        manager = DatabaseManager()
        yield manager
        manager.cleanup_connections()


class TestShortSqueezeDatabase:
    """Test suite for short squeeze database functionality"""
    
    def test_short_interest_data_table_exists(self, db_manager):
        """Test that short_interest_data table exists with correct structure"""
        with db_manager.engine.connect() as conn:
            # Check table exists
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name='short_interest_data'"
            ))
            assert result.fetchone() is not None, "short_interest_data table not found"
            
            # Check columns exist
            expected_columns = [
                'id', 'symbol', 'report_date', 'short_interest', 'float_shares',
                'short_ratio', 'short_percent_of_float', 'average_daily_volume', 'created_at'
            ]
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='short_interest_data' ORDER BY ordinal_position"
            ))
            columns = [row[0] for row in result.fetchall()]
            for col in expected_columns:
                assert col in columns, f"Column {col} not found in short_interest_data table"
    
    def test_short_squeeze_scores_table_exists(self, db_manager):
        """Test that short_squeeze_scores table exists with correct structure"""
        with db_manager.engine.connect() as conn:
            # Check table exists
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name='short_squeeze_scores'"
            ))
            assert result.fetchone() is not None, "short_squeeze_scores table not found"
            
            # Check columns exist
            expected_columns = [
                'id', 'symbol', 'squeeze_score', 'si_score', 'dtc_score', 
                'float_score', 'momentum_score', 'data_quality', 'calculated_at'
            ]
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='short_squeeze_scores' ORDER BY ordinal_position"
            ))
            columns = [row[0] for row in result.fetchall()]
            for col in expected_columns:
                assert col in columns, f"Column {col} not found in short_squeeze_scores table"
    
    def test_insert_short_interest_data(self, db_manager):
        """Test inserting short interest data"""
        test_symbol = "AAPL"
        test_data = {
            'report_date': date.today(),
            'short_interest': 50000000,
            'float_shares': 300000000,
            'short_ratio': 2.5,
            'short_percent_of_float': 16.67,
            'average_daily_volume': 20000000
        }
        
        # Insert data
        db_manager.insert_short_interest_data(test_symbol, test_data)
        
        # Verify data was inserted
        retrieved_data = db_manager.get_short_interest_data(test_symbol)
        assert len(retrieved_data) == 1
        assert retrieved_data[0]['symbol'] == test_symbol
        assert retrieved_data[0]['short_interest'] == test_data['short_interest']
        assert float(retrieved_data[0]['short_percent_of_float']) == test_data['short_percent_of_float']
    
    def test_insert_short_squeeze_score(self, db_manager):
        """Test inserting short squeeze scores"""
        test_symbol = "MSFT"
        test_score = {
            'squeeze_score': 75.5,
            'si_score': 60.0,
            'dtc_score': 40.0,
            'float_score': 80.0,
            'momentum_score': 90.0,
            'data_quality': 'high'
        }
        
        # Insert score
        db_manager.insert_short_squeeze_score(test_symbol, test_score)
        
        # Verify score was inserted
        retrieved_score = db_manager.get_short_squeeze_score(test_symbol)
        assert retrieved_score['symbol'] == test_symbol
        assert float(retrieved_score['squeeze_score']) == test_score['squeeze_score']
        assert retrieved_score['data_quality'] == test_score['data_quality']
    
    def test_upsert_short_interest_data(self, db_manager):
        """Test that duplicate short interest data is updated, not duplicated"""
        test_symbol = "GOOGL"
        initial_data = {
            'report_date': date.today(),
            'short_interest': 30000000,
            'float_shares': 250000000,
            'short_ratio': 1.8,
            'short_percent_of_float': 12.0,
            'average_daily_volume': 15000000
        }
        
        updated_data = {
            'report_date': date.today(),  # Same date
            'short_interest': 35000000,   # Updated value
            'float_shares': 250000000,
            'short_ratio': 2.0,
            'short_percent_of_float': 14.0,
            'average_daily_volume': 15000000
        }
        
        # Insert initial data
        db_manager.insert_short_interest_data(test_symbol, initial_data)
        
        # Insert updated data (should update, not create new record)
        db_manager.insert_short_interest_data(test_symbol, updated_data)
        
        # Verify only one record exists with updated values
        retrieved_data = db_manager.get_short_interest_data(test_symbol)
        assert len(retrieved_data) == 1
        assert retrieved_data[0]['short_interest'] == updated_data['short_interest']
        assert float(retrieved_data[0]['short_percent_of_float']) == updated_data['short_percent_of_float']
    
    def test_upsert_short_squeeze_score(self, db_manager):
        """Test that duplicate squeeze scores are updated, not duplicated"""
        test_symbol = "TSLA"
        initial_score = {
            'squeeze_score': 65.0,
            'si_score': 50.0,
            'dtc_score': 30.0,
            'float_score': 70.0,
            'momentum_score': 85.0,
            'data_quality': 'medium'
        }
        
        updated_score = {
            'squeeze_score': 75.5,  # Updated
            'si_score': 60.0,       # Updated
            'dtc_score': 40.0,      # Updated
            'float_score': 80.0,    # Updated
            'momentum_score': 90.0, # Updated
            'data_quality': 'high'  # Updated
        }
        
        # Insert initial score
        db_manager.insert_short_squeeze_score(test_symbol, initial_score)
        
        # Insert updated score (should update, not create new record)
        db_manager.insert_short_squeeze_score(test_symbol, updated_score)
        
        # Verify only one record exists with updated values
        retrieved_score = db_manager.get_short_squeeze_score(test_symbol)
        assert float(retrieved_score['squeeze_score']) == updated_score['squeeze_score']
        assert retrieved_score['data_quality'] == updated_score['data_quality']
    
    def test_get_short_squeeze_rankings(self, db_manager):
        """Test retrieving short squeeze rankings"""
        # Clean up any existing data
        with db_manager.engine.connect() as conn:
            conn.execute(text("DELETE FROM short_squeeze_scores"))
            conn.commit()
        
        # Insert test scores for multiple symbols
        test_scores = [
            ('AAPL', {'squeeze_score': 85.0, 'si_score': 70.0, 'dtc_score': 60.0, 
                     'float_score': 90.0, 'momentum_score': 95.0, 'data_quality': 'high'}),
            ('MSFT', {'squeeze_score': 75.0, 'si_score': 60.0, 'dtc_score': 50.0, 
                     'float_score': 80.0, 'momentum_score': 85.0, 'data_quality': 'high'}),
            ('GOOGL', {'squeeze_score': 65.0, 'si_score': 50.0, 'dtc_score': 40.0, 
                      'float_score': 70.0, 'momentum_score': 75.0, 'data_quality': 'medium'})
        ]
        
        for symbol, score_data in test_scores:
            db_manager.insert_short_squeeze_score(symbol, score_data)
        
        # Get rankings
        rankings = db_manager.get_short_squeeze_rankings(limit=3)
        
        # Verify rankings are in descending order by squeeze_score
        assert len(rankings) == 3
        assert rankings[0]['symbol'] == 'AAPL'  # Highest score
        assert rankings[1]['symbol'] == 'MSFT'  # Second highest
        assert rankings[2]['symbol'] == 'GOOGL' # Lowest score
        
        # Verify scores are correct
        assert float(rankings[0]['squeeze_score']) == 85.0
        assert float(rankings[1]['squeeze_score']) == 75.0
        assert float(rankings[2]['squeeze_score']) == 65.0
    
    def test_get_nonexistent_short_squeeze_score(self, db_manager):
        """Test retrieving score for non-existent symbol"""
        result = db_manager.get_short_squeeze_score("NONEXISTENT")
        assert result == {}
    
    def test_get_short_interest_data_with_limit(self, db_manager):
        """Test retrieving short interest data with limit"""
        test_symbol = "META"
        
        # Insert multiple records with different dates
        from datetime import timedelta
        base_date = date.today()
        
        for i in range(5):
            test_data = {
                'report_date': base_date - timedelta(days=i*30),
                'short_interest': 10000000 + i * 1000000,
                'float_shares': 200000000,
                'short_ratio': 2.0 + i * 0.1,
                'short_percent_of_float': 10.0 + i,
                'average_daily_volume': 18000000
            }
            db_manager.insert_short_interest_data(test_symbol, test_data)
        
        # Get limited results
        data = db_manager.get_short_interest_data(test_symbol, limit=3)
        assert len(data) == 3
        
        # Verify they're in descending date order (most recent first)
        for i in range(len(data) - 1):
            assert data[i]['report_date'] >= data[i + 1]['report_date']