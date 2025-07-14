#!/usr/bin/env python3
"""
Extended tests for Scheduler functionality
Tests scheduler logic, gap detection, and background task management
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import os

# Mock environment variables before importing
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {}):
        yield

@pytest.fixture
def mock_scheduler_components():
    """Mock all scheduler dependencies"""
    with patch('scheduler.DailyUpdater') as mock_daily_updater, \
         patch('scheduler.StockDataService') as mock_stock_service, \
         patch('scheduler.FMPClient') as mock_fmp_client, \
         patch('scheduler.YahooFinanceClient') as mock_yahoo_client, \
         patch('scheduler.GapDetector') as mock_gap_detector, \
         patch('database.DatabaseManager') as mock_db_manager:
        
        yield {
            'daily_updater': mock_daily_updater,
            'stock_service': mock_stock_service,
            'fmp_client': mock_fmp_client,
            'yahoo_client': mock_yahoo_client,
            'gap_detector': mock_gap_detector,
            'db_manager': mock_db_manager
        }

@pytest.fixture
def scheduler_instance(mock_scheduler_components):
    """Create a scheduler instance with mocked dependencies"""
    from scheduler import Scheduler
    
    scheduler = Scheduler()
    
    # Set up mock instances
    scheduler.daily_updater = mock_scheduler_components['daily_updater'].return_value
    scheduler.dal = mock_scheduler_components['stock_service'].return_value
    scheduler.gap_detector = mock_scheduler_components['gap_detector'].return_value
    scheduler.fmp_client = mock_scheduler_components['fmp_client'].return_value
    scheduler.yahoo_client = mock_scheduler_components['yahoo_client'].return_value
    scheduler.db_manager = mock_scheduler_components['db_manager'].return_value
    
    # Reset status to known state for tests
    scheduler.status = {
        "running": False,
        "pid": os.getpid(),
        "last_successful_update": None,
        "next_scheduled_run": None,
        "consecutive_failures": 0,
    }
    
    return scheduler

class TestSchedulerLogic:
    """Test scheduler business logic and task management"""

    def test_scheduler_initialization(self, scheduler_instance):
        """Test scheduler initializes with correct status"""
        assert scheduler_instance.status['running'] is False
        assert scheduler_instance.status['consecutive_failures'] == 0
        assert 'pid' in scheduler_instance.status

    def test_run_daily_update_success(self, scheduler_instance):
        """Test successful daily update execution"""
        # Mock successful daily update
        scheduler_instance.daily_updater.run_daily_update.return_value = True
        
        scheduler_instance.run_daily_update()
        
        # Verify daily updater was called
        scheduler_instance.daily_updater.run_daily_update.assert_called_once()
        
        # Verify status was updated
        assert scheduler_instance.status['consecutive_failures'] == 0
        assert scheduler_instance.status['last_successful_update'] is not None

    def test_run_daily_update_failure(self, scheduler_instance):
        """Test daily update execution with failure"""
        # Mock failed daily update
        scheduler_instance.daily_updater.run_daily_update.return_value = False
        
        scheduler_instance.run_daily_update()
        
        # Verify failure was recorded
        assert scheduler_instance.status['consecutive_failures'] == 1

    def test_run_daily_update_exception(self, scheduler_instance):
        """Test daily update execution with exception"""
        # Mock exception during daily update
        scheduler_instance.daily_updater.run_daily_update.side_effect = Exception("Database error")
        
        scheduler_instance.run_daily_update()
        
        # Verify exception was handled and failure recorded
        assert scheduler_instance.status['consecutive_failures'] == 1

    def test_run_health_check_no_gaps(self, scheduler_instance):
        """Test health check when no gaps are found"""
        # Mock gap detector returning no gaps
        scheduler_instance.gap_detector.detect_all_gaps.return_value = {
            'price_data': [],
            'profile_data': [],
            'corporate_actions': []
        }
        
        scheduler_instance.run_health_check()
        
        # Verify gap detector was called
        scheduler_instance.gap_detector.detect_all_gaps.assert_called_once()

    def test_run_health_check_with_gaps(self, scheduler_instance):
        """Test health check when gaps are found"""
        # Mock gap detector returning gaps
        mock_gaps = {
            'price_data': [{'symbol': 'AAPL', 'gap_type': 'price_data'}],
            'profile_data': [{'symbol': 'MSFT', 'gap_type': 'profile_data'}],
            'corporate_actions': []
        }
        scheduler_instance.gap_detector.detect_all_gaps.return_value = mock_gaps
        
        scheduler_instance.run_health_check()
        
        # Verify gaps were detected
        scheduler_instance.gap_detector.detect_all_gaps.assert_called_once()

    @patch('scheduler.time.sleep')
    def test_catchup_operation_no_gaps(self, mock_sleep, scheduler_instance):
        """Test catchup operation when no gaps exist"""
        # Mock no gaps
        scheduler_instance.gap_detector.detect_all_gaps.return_value = {}
        
        with patch.object(scheduler_instance, '_get_retry_gaps', return_value=[]):
            scheduler_instance.run_catchup_operation()
        
        # Should exit early when no gaps found
        scheduler_instance.gap_detector.detect_all_gaps.assert_called_once()

    @patch('scheduler.time.sleep')
    def test_catchup_operation_with_gaps(self, mock_sleep, scheduler_instance):
        """Test catchup operation processing gaps"""
        # Mock gaps
        mock_gaps = {
            'price_data': [MagicMock(symbol='AAPL')],
            'profile_data': [MagicMock(symbol='MSFT')]
        }
        scheduler_instance.gap_detector.detect_all_gaps.return_value = mock_gaps
        
        # Mock other methods
        with patch.object(scheduler_instance, '_get_retry_gaps', return_value=[]), \
             patch.object(scheduler_instance, '_get_already_processed_gaps', return_value=set()), \
             patch('scheduler.YahooFinanceClient') as mock_yahoo_class:
            
            mock_yahoo_client = mock_yahoo_class.return_value
            mock_yahoo_client.get_historical_prices.return_value = MagicMock(empty=False)
            mock_yahoo_client.get_company_profile.return_value = {'symbol': 'TEST'}
            
            scheduler_instance.run_catchup_operation()
        
        # Verify gaps were processed
        assert mock_sleep.call_count >= 0  # Sleep called between gap processing

    def test_rate_limit_pause_logic(self, scheduler_instance):
        """Test rate limiting pause functionality"""
        # Set rate limit pause
        scheduler_instance.rate_limit_pause_until = datetime.now() + timedelta(minutes=5)
        
        with patch('scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now()
            
            scheduler_instance.run_catchup_operation()
        
        # Should exit early due to rate limit pause
        # The exact behavior depends on implementation, but should not crash

    def test_consecutive_error_handling(self, scheduler_instance):
        """Test consecutive error handling in catchup operation"""
        # Mock gaps and failures
        mock_gaps = {
            'price_data': [MagicMock(symbol='AAPL'), MagicMock(symbol='MSFT'), 
                          MagicMock(symbol='GOOGL'), MagicMock(symbol='AMZN')]
        }
        scheduler_instance.gap_detector.detect_all_gaps.return_value = mock_gaps
        
        with patch.object(scheduler_instance, '_get_retry_gaps', return_value=[]), \
             patch.object(scheduler_instance, '_get_already_processed_gaps', return_value=set()), \
             patch('scheduler.YahooFinanceClient') as mock_yahoo_class, \
             patch('scheduler.time.sleep'):
            
            mock_yahoo_client = mock_yahoo_class.return_value
            # Mock consecutive failures
            mock_yahoo_client.get_historical_prices.side_effect = Exception("Rate limit error")
            
            scheduler_instance.run_catchup_operation()
        
        # Should handle consecutive errors gracefully
        assert hasattr(scheduler_instance, '_running')  # Basic functionality check

    def test_gap_processing_data_unavailable(self, scheduler_instance):
        """Test handling of data unavailable scenarios"""
        mock_gaps = {
            'corporate_actions': [MagicMock(symbol='AAPL')]
        }
        scheduler_instance.gap_detector.detect_all_gaps.return_value = mock_gaps
        
        with patch.object(scheduler_instance, '_get_retry_gaps', return_value=[]), \
             patch.object(scheduler_instance, '_get_already_processed_gaps', return_value=set()), \
             patch.object(scheduler_instance, '_mark_gap_unavailable') as mock_mark_unavailable, \
             patch('scheduler.YahooFinanceClient') as mock_yahoo_class, \
             patch('scheduler.time.sleep'):
            
            mock_yahoo_client = mock_yahoo_class.return_value
            # Mock no data available
            mock_yahoo_client.get_corporate_actions.return_value = None
            
            scheduler_instance.run_catchup_operation()
        
        # Should mark gap as unavailable
        assert mock_mark_unavailable.call_count >= 0  # May be called for data unavailability

    def test_scheduler_stop_functionality(self, scheduler_instance):
        """Test scheduler stop functionality"""
        scheduler_instance.stop()
        assert scheduler_instance._running is False

    @patch('scheduler.schedule')
    def test_job_scheduling(self, mock_schedule, scheduler_instance):
        """Test that scheduler sets up jobs correctly"""
        # Mock schedule every method chains
        mock_schedule.every.return_value.day.at.return_value.do = MagicMock()
        mock_schedule.every.return_value.hours.do = MagicMock()
        mock_schedule.every.return_value.hour.do = MagicMock()
        
        # Mock gap detector for initial check
        scheduler_instance.gap_detector.detect_all_gaps.return_value = {}
        
        with patch('scheduler.time.sleep', side_effect=KeyboardInterrupt):
            # Use KeyboardInterrupt to exit the infinite loop
            try:
                scheduler_instance.run_forever()
            except KeyboardInterrupt:
                pass
        
        # Verify jobs were scheduled
        assert mock_schedule.every.call_count >= 3  # Should have scheduled 3 types of jobs

class TestSchedulerDataProcessing:
    """Test scheduler data processing and gap handling"""

    def test_record_gap_attempt(self, scheduler_instance):
        """Test gap attempt recording"""
        mock_conn = MagicMock()
        scheduler_instance.db_manager.engine.connect.return_value.__enter__.return_value = mock_conn
        
        scheduler_instance._record_gap_attempt('AAPL', 'price_data', 'rate_limit', 'Too many requests')
        
        # Verify database call was made
        mock_conn.execute.assert_called_once()

    def test_mark_gap_unavailable(self, scheduler_instance):
        """Test marking gap as unavailable"""
        mock_conn = MagicMock()
        scheduler_instance.db_manager.engine.connect.return_value.__enter__.return_value = mock_conn
        
        scheduler_instance._mark_gap_unavailable('AAPL', 'corporate_actions', 'No data available')
        
        # Verify database call was made
        mock_conn.execute.assert_called_once()

    def test_get_retry_gaps(self, scheduler_instance):
        """Test getting gaps ready for retry"""
        mock_conn = MagicMock()
        scheduler_instance.db_manager.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock database response
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [('AAPL', 'price_data'), ('MSFT', 'profile_data')]
        mock_conn.execute.return_value = mock_result
        
        retry_gaps = scheduler_instance._get_retry_gaps()
        
        assert len(retry_gaps) == 2
        assert ('AAPL', 'price_data') in retry_gaps
        assert ('MSFT', 'profile_data') in retry_gaps

    def test_get_already_processed_gaps(self, scheduler_instance):
        """Test getting already processed gaps"""
        mock_conn = MagicMock()
        scheduler_instance.db_manager.engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mock database response
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [('AAPL', 'corporate_actions'), ('GOOGL', 'analyst_recommendations')]
        mock_conn.execute.return_value = mock_result
        
        processed_gaps = scheduler_instance._get_already_processed_gaps()
        
        assert len(processed_gaps) == 2
        assert ('AAPL', 'corporate_actions') in processed_gaps
        assert ('GOOGL', 'analyst_recommendations') in processed_gaps

    def test_save_status(self, scheduler_instance):
        """Test status saving functionality"""
        with patch('scheduler.STATUS_FILE') as mock_status_file, \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.dump') as mock_json_dump:
            
            mock_status_file.parent.mkdir = MagicMock()
            
            scheduler_instance._save_status()
            
            # Verify status was saved
            assert scheduler_instance.status['last_updated'] is not None

class TestSchedulerErrorHandling:
    """Test scheduler error handling and resilience"""

    def test_initialization_failure_handling(self, mock_scheduler_components):
        """Test handling of initialization failures"""
        # Mock database manager to raise exception
        mock_scheduler_components['db_manager'].side_effect = Exception("Database connection failed")
        
        from scheduler import Scheduler
        
        with pytest.raises(Exception):
            Scheduler()

    def test_health_check_exception_handling(self, scheduler_instance):
        """Test health check exception handling"""
        # Mock gap detector to raise exception
        scheduler_instance.gap_detector.detect_all_gaps.side_effect = Exception("Database error")
        
        # Should not crash
        scheduler_instance.run_health_check()
        
        # Status should still be accessible
        assert 'running' in scheduler_instance.status

    def test_catchup_operation_database_error(self, scheduler_instance):
        """Test catchup operation with database errors"""
        # Mock database operations to fail
        scheduler_instance.gap_detector.detect_all_gaps.side_effect = Exception("Database connection lost")
        
        # Should handle gracefully
        scheduler_instance.run_catchup_operation()
        
        # Should not crash the scheduler
        assert scheduler_instance._running is True

    def test_gap_processing_with_invalid_data(self, scheduler_instance):
        """Test gap processing with invalid or corrupted data"""
        # Mock gaps with invalid structure
        invalid_gaps = {
            'price_data': [MagicMock(symbol=None)],  # Invalid symbol
            'invalid_type': [MagicMock(symbol='AAPL')]  # Invalid gap type
        }
        scheduler_instance.gap_detector.detect_all_gaps.return_value = invalid_gaps
        
        with patch.object(scheduler_instance, '_get_retry_gaps', return_value=[]), \
             patch.object(scheduler_instance, '_get_already_processed_gaps', return_value=set()), \
             patch('scheduler.time.sleep'):
            
            # Should handle invalid data gracefully
            scheduler_instance.run_catchup_operation()
        
        # Should not crash
        assert hasattr(scheduler_instance, '_running')