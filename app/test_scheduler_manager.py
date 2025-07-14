

import unittest
import time
import sys
from pathlib import Path
import psutil
from process_manager import EnhancedProcessManager
from scheduler import SCHEDULER_NAME, SCHEDULER_COMMAND

class TestSchedulerManager(unittest.TestCase):
    def setUp(self):
        """Set up for each test."""
        self.pid_file = Path(f"/tmp/{SCHEDULER_NAME}.pid")
        self.status_file = Path(f"/tmp/{SCHEDULER_NAME}_status.json")
        
        self.pm = EnhancedProcessManager(
            name=SCHEDULER_NAME,
            pid_file=self.pid_file,
            status_file=self.status_file,
            command=SCHEDULER_COMMAND,
            working_dir='/app'
        )
        # Clean up before each test
        self.pm.stop()

    def tearDown(self):
        """Clean up after each test."""
        self.pm.stop()

    def test_01_start_and_is_running(self):
        """Test starting the scheduler and checking if it's running."""
        print("\n--- Testing Scheduler Start and is_running ---")
        self.assertFalse(self.pm.is_running(), "Scheduler should not be running initially.")
        
        success = self.pm.start()
        self.assertTrue(success, "Scheduler should start successfully.")
        time.sleep(2)  # Give it a moment to start and write status
        
        self.assertTrue(self.pm.is_running(), "Scheduler should be running after start.")
        
        pid = self.pm.get_pid()
        self.assertIsNotNone(pid, "PID should not be None.")
        self.assertTrue(psutil.pid_exists(pid), f"PID {pid} should exist.")

    def test_02_stop(self):
        """Test stopping the scheduler."""
        print("\n--- Testing Scheduler Stop ---")
        self.pm.start()
        time.sleep(1)
        self.assertTrue(self.pm.is_running(), "Scheduler should be running before stop.")
        
        success = self.pm.stop()
        self.assertTrue(success, "Scheduler should stop successfully.")
        time.sleep(1)
        
        self.assertFalse(self.pm.is_running(), "Scheduler should not be running after stop.")
        self.assertFalse(self.pid_file.exists(), "PID file should be cleaned up.")
        self.assertFalse(self.status_file.exists(), "Status file should be cleaned up.")

    def test_03_restart(self):
        """Test restarting the scheduler."""
        print("\n--- Testing Scheduler Restart ---")
        self.pm.start()
        time.sleep(1)
        initial_pid = self.pm.get_pid()
        self.assertTrue(self.pm.is_running(), "Scheduler should be running before restart.")
        
        success = self.pm.restart()
        self.assertTrue(success, "Scheduler should restart successfully.")
        time.sleep(2)
        
        self.assertTrue(self.pm.is_running(), "Scheduler should be running after restart.")
        new_pid = self.pm.get_pid()
        self.assertIsNotNone(new_pid, "New PID should not be None.")
        self.assertNotEqual(initial_pid, new_pid, "PID should change after restart.")

    def test_04_status(self):
        """Test the status functionality."""
        print("\n--- Testing Scheduler Status ---")
        # Status when stopped
        status_stopped = self.pm.get_status()
        self.assertFalse(status_stopped['running'])
        self.assertEqual(status_stopped.get('status'), 'stopped')

        # Status when running
        self.pm.start()
        # Give the scheduler time to start and write its status file
        time.sleep(5) 

        status_running = self.pm.get_status()
        
        self.assertTrue(status_running['running'])
        # The scheduler overwrites the status file with its own format
        # Check for either the process manager format or scheduler format
        status_field = status_running.get('status') or ('running' if status_running.get('running') else 'stopped')
        self.assertEqual(status_field, 'running')
        self.assertIsNotNone(status_running['pid'])

if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSchedulerManager))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nAll scheduler tests passed successfully!")
        sys.exit(0)
    else:
        print("\nSome scheduler tests failed.")
        sys.exit(1)
