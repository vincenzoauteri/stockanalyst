import pytest
from unittest.mock import patch, MagicMock
from scheduler import Scheduler


class TestSchedulerShortInterest:
    """Test suite for scheduler short interest functionality"""
    
    @pytest.fixture
    def scheduler(self):
        """Create a Scheduler instance with mocked dependencies"""
        with patch('daily_updater.DailyUpdater'), \
             patch('gap_detector.GapDetector'), \
             patch('data_fetcher.DataFetcher'), \
             patch('data_access_layer.StockDataService'), \
             patch('database.DatabaseManager') as mock_db, \
             patch('data_fetcher.DatabaseManager') as mock_data_fetcher_db, \
             patch('fmp_client.FMPClient'), \
             patch('yahoo_finance_client.YahooFinanceClient'):
            
            # Configure the mocked DatabaseManager instances
            mock_db.return_value = MagicMock()
            mock_data_fetcher_db.return_value = MagicMock()
            
            scheduler = Scheduler()
            
            # Mock the data fetcher and database manager
            scheduler.data_fetcher = MagicMock()
            scheduler.db_manager = MagicMock()
            
            return scheduler
    
    def test_run_weekly_short_interest_update_success(self, scheduler):
        """Test successful weekly short interest update"""
        # Mock database to return test symbols
        scheduler.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT', 'GOOGL']
        
        # Mock data fetcher to return successful result
        scheduler.data_fetcher.fetch_short_interest_data.return_value = 3
        
        # Run the update
        scheduler.run_weekly_short_interest_update()
        
        # Verify symbols were retrieved
        scheduler.db_manager.get_sp500_symbols.assert_called_once()
        
        # Verify data fetcher was called with correct parameters
        scheduler.data_fetcher.fetch_short_interest_data.assert_called_once_with(['AAPL', 'MSFT', 'GOOGL'], max_requests=250)
        
        # Verify status was updated
        assert "last_short_interest_update" in scheduler.status
        assert scheduler.status["short_interest_symbols_updated"] == 3
    
    def test_run_weekly_short_interest_update_no_data(self, scheduler):
        """Test weekly short interest update when no data is collected"""
        # Mock database to return test symbols
        scheduler.db_manager.get_sp500_symbols.return_value = ['AAPL', 'MSFT']
        
        # Mock data fetcher to return no results
        scheduler.data_fetcher.fetch_short_interest_data.return_value = 0
        
        # Run the update
        scheduler.run_weekly_short_interest_update()
        
        # Verify data fetcher was called
        scheduler.data_fetcher.fetch_short_interest_data.assert_called_once_with(['AAPL', 'MSFT'], max_requests=250)
        
        # Verify status reflects no data collected
        assert "last_short_interest_update" not in scheduler.status
        assert "short_interest_symbols_updated" not in scheduler.status
    
    def test_run_weekly_short_interest_update_exception(self, scheduler):
        """Test weekly short interest update when an exception occurs"""
        # Mock database to raise exception
        scheduler.db_manager.get_sp500_symbols.side_effect = Exception("Database error")
        
        # Run the update (should not raise exception)
        scheduler.run_weekly_short_interest_update()
        
        # Verify data fetcher was not called due to early exception
        scheduler.data_fetcher.fetch_short_interest_data.assert_not_called()
        
        # Verify status was saved (finally block)
        # Note: _save_status is called in finally block
    
    def test_run_weekly_short_interest_update_with_large_symbol_list(self, scheduler):
        """Test weekly short interest update with large symbol list"""
        # Mock database to return large symbol list
        large_symbol_list = [f'SYMBOL{i}' for i in range(500)]
        scheduler.db_manager.get_sp500_symbols.return_value = large_symbol_list
        
        # Mock data fetcher to return partial results (due to rate limiting)
        scheduler.data_fetcher.fetch_short_interest_data.return_value = 250
        
        # Run the update
        scheduler.run_weekly_short_interest_update()
        
        # Verify data fetcher was called with correct parameters and rate limiting
        scheduler.data_fetcher.fetch_short_interest_data.assert_called_once_with(large_symbol_list, max_requests=250)
        
        # Verify status reflects partial completion
        assert scheduler.status["short_interest_symbols_updated"] == 250
    
    @patch('scheduler.schedule')
    def test_scheduler_schedules_weekly_update(self, mock_schedule, scheduler):
        """Test that the scheduler properly schedules the weekly short interest update"""
        # Mock schedule object
        mock_schedule.every.return_value.sunday.at.return_value.do = MagicMock()
        
        # Create new scheduler to trigger schedule setup
        with patch('daily_updater.DailyUpdater'), \
             patch('gap_detector.GapDetector'), \
             patch('data_fetcher.DataFetcher'), \
             patch('data_access_layer.StockDataService'), \
             patch('database.DatabaseManager'), \
             patch('fmp_client.FMPClient'), \
             patch('yahoo_finance_client.YahooFinanceClient'):
            
            test_scheduler = Scheduler()
            test_scheduler.run_forever_once = True  # Prevent infinite loop
            
            # Mock gap detector to return no gaps
            test_scheduler.gap_detector = MagicMock()
            test_scheduler.gap_detector.detect_all_gaps.return_value = {}
            
            # Start the scheduler (this should set up schedules)
            try:
                test_scheduler.run_forever()
            except SystemExit:
                pass  # Expected when run_forever_once is True
            
            # Verify weekly schedule was set up
            mock_schedule.every.assert_called()
            mock_schedule.every.return_value.sunday.at.assert_called_with("02:00")
    
    def test_data_fetcher_initialization(self, scheduler):
        """Test that the scheduler properly initializes the DataFetcher"""
        # Verify DataFetcher was initialized
        assert hasattr(scheduler, 'data_fetcher')
        assert scheduler.data_fetcher is not None
    
    def test_weekly_update_method_exists(self, scheduler):
        """Test that the weekly update method exists and is callable"""
        assert hasattr(scheduler, 'run_weekly_short_interest_update')
        assert callable(getattr(scheduler, 'run_weekly_short_interest_update'))
    
    def test_status_tracking(self, scheduler):
        """Test that the scheduler properly tracks status"""
        # Initialize with empty status
        scheduler.status = {}
        
        # Mock successful update
        scheduler.db_manager.get_sp500_symbols.return_value = ['AAPL']
        scheduler.data_fetcher.fetch_short_interest_data.return_value = 1
        
        # Run update
        scheduler.run_weekly_short_interest_update()
        
        # Verify status tracking
        assert "last_short_interest_update" in scheduler.status
        assert "short_interest_symbols_updated" in scheduler.status
        assert scheduler.status["short_interest_symbols_updated"] == 1
        
        # Verify timestamp format
        import datetime
        timestamp_str = scheduler.status["last_short_interest_update"]
        # Should be able to parse the ISO format timestamp
        datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))